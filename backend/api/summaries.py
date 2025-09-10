from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from core.database import get_database
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/summaries/documents/{doc_id}", response_model=dict)
async def get_document_summary(
    doc_id: str,
    db = Depends(get_database)
):
    """Get document overview and chunk summaries"""
    try:
        # Get document with overview
        doc = await db.documents.find_one({"_id": doc_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get chunk summaries
        chunks = []
        async for chunk in db.chunks.find({"doc_id": doc_id}):
            chunk_info = {
                "chunk_id": str(chunk["_id"]),
                "page_from": chunk["page_from"],
                "page_to": chunk["page_to"],
                "section": chunk.get("section"),
                "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "summary": chunk.get("summary"),
                "key_topics": chunk.get("key_topics", []),
                "important_details": chunk.get("important_details", [])
            }
            chunks.append(chunk_info)
        
        return {
            "document": {
                "id": str(doc["_id"]),
                "title": doc["title"],
                "status": doc["status"],
                "overview": doc.get("overview")
            },
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summaries/documents", response_model=List[dict])
async def list_document_summaries(
    db = Depends(get_database)
):
    """List all documents with their overviews"""
    try:
        documents = []
        async for doc in db.documents.find({}, {"title": 1, "status": 1, "overview": 1, "uploaded_at": 1}):
            doc_info = {
                "id": str(doc["_id"]),
                "title": doc["title"],
                "status": doc["status"],
                "uploaded_at": doc["uploaded_at"],
                "overview": doc.get("overview")
            }
            documents.append(doc_info)
        
        return documents
        
    except Exception as e:
        logger.error(f"Error listing document summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summaries/reprocess/{doc_id}", response_model=dict)
async def reprocess_document_summaries(
    doc_id: str,
    db = Depends(get_database)
):
    """Reprocess document to generate new summaries"""
    try:
        from core.ingestion import get_processor
        from core.schema import DocumentStatus
        
        # Check if document exists
        doc = await db.documents.find_one({"_id": doc_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update status to processing
        await db.documents.update_one(
            {"_id": doc_id},
            {"$set": {"status": DocumentStatus.PENDING}}
        )
        
        # Get processor and reprocess
        processor = get_processor(db)
        result = await processor.process_document(doc_id, doc["path"], doc["policy_type"])
        
        return {
            "message": "Document reprocessing started",
            "doc_id": doc_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

