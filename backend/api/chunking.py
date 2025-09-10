from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Dict, Any
import logging
import os
from datetime import datetime
from core.database import get_database
from core.pdf_chunker import get_pdf_chunker
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chunk-pdf", response_model=dict)
async def chunk_pdf(
    file: UploadFile = File(...),
    doc_id: str = Form(...),
    title: str = Form(...),
    db = Depends(get_database)
):
    """Convert uploaded PDF to structured JSON chunks"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save uploaded file temporarily
        upload_dir = "uploads/policies"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get PDF chunker
        chunker = get_pdf_chunker()
        
        # Convert PDF to chunks
        chunks = chunker.chunk_pdf_to_json(file_path, doc_id, title)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to extract chunks from PDF")
        
        # Store chunks in database
        chunk_documents = []
        for chunk in chunks:
            chunk_doc = {
                **chunk,
                "doc_id": doc_id,
                "created_at": datetime.utcnow(),
                "file_type": "pdf",
                "chunk_type": "structured"
            }
            chunk_documents.append(chunk_doc)
        
        # Insert chunks into database
        result = await db.chunks.insert_many(chunk_documents)
        
        # Clean up temporary file
        try:
            os.remove(file_path)
        except:
            pass
        
        logger.info(f"✅ Created {len(chunks)} chunks for document {doc_id}")
        
        return {
            "message": "PDF chunked successfully",
            "doc_id": doc_id,
            "chunks_created": len(chunks),
            "chunk_ids": [chunk["chunk_id"] for chunk in chunks]
        }
        
    except Exception as e:
        logger.error(f"Error chunking PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chunks/{doc_id}", response_model=List[Dict[str, Any]])
async def get_document_chunks(
    doc_id: str,
    db = Depends(get_database)
):
    """Get all chunks for a specific document"""
    try:
        chunks_cursor = db.chunks.find({"doc_id": doc_id}).sort("chunk_id", 1)
        chunks = await chunks_cursor.to_list(length=None)
        
        # Convert ObjectId to string for JSON serialization
        for chunk in chunks:
            chunk["_id"] = str(chunk["_id"])
            if "created_at" in chunk:
                chunk["created_at"] = chunk["created_at"].isoformat()
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error getting chunks for document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chunks/{doc_id}/{chunk_id}", response_model=Dict[str, Any])
async def get_specific_chunk(
    doc_id: str,
    chunk_id: str,
    db = Depends(get_database)
):
    """Get a specific chunk by document ID and chunk ID"""
    try:
        chunk = await db.chunks.find_one({
            "doc_id": doc_id,
            "chunk_id": chunk_id
        })
        
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Convert ObjectId to string
        chunk["_id"] = str(chunk["_id"])
        if "created_at" in chunk:
            chunk["created_at"] = chunk["created_at"].isoformat()
        
        return chunk
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk {chunk_id} for document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/chunks/{doc_id}", response_model=dict)
async def delete_document_chunks(
    doc_id: str,
    db = Depends(get_database)
):
    """Delete all chunks for a specific document"""
    try:
        result = await db.chunks.delete_many({"doc_id": doc_id})
        
        return {
            "message": "Chunks deleted successfully",
            "doc_id": doc_id,
            "chunks_deleted": result.deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting chunks for document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chunk-by-doc-id/{doc_id}", response_model=dict)
async def chunk_by_doc_id(doc_id: str, db = Depends(get_database)):
    """Manually trigger chunking for an existing document by doc_id"""
    try:
        # Find the document
        document = await db.documents.find_one({"_id": ObjectId(doc_id)})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if it's a PDF
        if document.get("file_type", "").lower() != "pdf":
            raise HTTPException(status_code=400, detail="Document is not a PDF")
        
        # Get file path
        file_path = document.get("path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
        # Get PDF chunker
        chunker = get_pdf_chunker()
        
        # Convert PDF to chunks
        chunks = chunker.chunk_pdf_to_json(file_path, doc_id, document.get("title", "Unknown"))
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to extract chunks from PDF")
        
        # Delete existing chunks for this document first
        await db.chunks.delete_many({"doc_id": doc_id})
        
        # Store chunks in database
        chunk_documents = []
        for chunk in chunks:
            chunk_doc = {
                **chunk,
                "doc_id": doc_id,
                "created_at": datetime.utcnow(),
                "file_type": "pdf",
                "chunk_type": "structured"
            }
            chunk_documents.append(chunk_doc)
        
        # Insert new chunks
        await db.chunks.insert_many(chunk_documents)
        
        # Update document status
        await db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"status": "completed", "chunks_count": len(chunks)}}
        )
        
        return {
            "message": f"Successfully chunked document {doc_id}",
            "doc_id": doc_id,
            "chunks_created": len(chunks),
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error chunking document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to chunk document: {str(e)}")

@router.get("/chunks/stats", response_model=Dict[str, Any])
async def get_chunking_stats(
    db = Depends(get_database)
):
    """Get chunking statistics"""
    try:
        # Total chunks
        total_chunks = await db.chunks.count_documents({})
        
        # Chunks by document
        chunks_by_doc = await db.chunks.aggregate([
            {"$group": {"_id": "$doc_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]).to_list(length=None)
        
        # Chunks by type
        chunks_by_type = await db.chunks.aggregate([
            {"$group": {"_id": "$chunk_type", "count": {"$sum": 1}}}
        ]).to_list(length=None)
        
        return {
            "total_chunks": total_chunks,
            "chunks_by_document": chunks_by_doc,
            "chunks_by_type": chunks_by_type
        }
        
    except Exception as e:
        logger.error(f"Error getting chunking stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
