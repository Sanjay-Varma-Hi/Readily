from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from typing import List, Optional
from datetime import datetime
import os
import aiofiles
from pydantic import BaseModel
from bson import ObjectId
from core.database import get_database
from core.schema import Document, DocumentStatus, PolicyType, PolicyFolder, generate_checksum
from core.ingestion import get_processor
# PDF chunker removed - using single chunk mechanism instead
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class CreatePolicyFolderRequest(BaseModel):
    name: str
    policy_type: PolicyType = PolicyType.CUSTOM

@router.post("/policies", response_model=dict)
async def upload_policy(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    jurisdiction: str = Form(...),
    policy_type: PolicyType = Form(...),
    version: str = Form("1.0"),
    effective_date: str = Form(...),
    db = Depends(get_database)
):
    """Upload a new policy document"""
    try:
        # Validate file type
        allowed_extensions = os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt").split(",")
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {allowed_extensions}"
            )

        # Check file size
        max_size = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024  # Convert to bytes
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {os.getenv('MAX_FILE_SIZE_MB', '50')}MB"
            )

        # Generate checksum
        checksum = generate_checksum(content)

        # Check if document already exists
        existing_doc = await db.documents.find_one({"checksum": checksum})
        if existing_doc:
            return {
                "message": "Document already exists",
                "doc_id": str(existing_doc["_id"]),
                "status": existing_doc["status"]
            }

        # Save file to disk
        upload_dir = "uploads/policies"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Use original filename exactly as uploaded
        file_extension = file.filename.split('.')[-1]
        file_path = os.path.join(upload_dir, file.filename)
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Parse effective date
        try:
            effective_date_obj = datetime.fromisoformat(effective_date.replace("Z", "+00:00"))
        except ValueError:
            effective_date_obj = datetime.utcnow()

        # Create document record
        document = Document(
            title=title,
            path=file_path,
            jurisdiction=jurisdiction,
            policy_type=policy_type,
            version=version,
            effective_date=effective_date_obj,
            checksum=checksum,
            status=DocumentStatus.PENDING,
            file_size=len(content),
            file_type=file_extension
        )

        # Save to database
        result = await db.documents.insert_one(document.dict(by_alias=True, exclude={"id"}))
        doc_id = str(result.inserted_id)

        # Add to policy folder
        await add_to_policy_folder(db, policy_type, doc_id)

        # Auto-create single chunk for all supported files
        if file_extension.lower() in ['pdf', 'docx', 'txt']:
            try:
                logger.info(f"🔄 Auto-creating single chunk for: {title}")
                
                # Import single chunk function
                from core.single_chunk import create_single_chunk
                
                # Create single chunk
                single_chunk = await create_single_chunk(file_path, doc_id, title, file_extension)
                
                if single_chunk:
                    # Delete existing chunks for this document first
                    await db.chunks.delete_many({"doc_id": doc_id})
                    
                    # Insert single chunk
                    await db.chunks.insert_one(single_chunk)
                    logger.info(f"✅ Auto-created single chunk for {file_extension.upper()}")
                    
                    # Update document status to completed
                    await db.documents.update_one(
                        {"_id": ObjectId(doc_id)},
                        {
                            "$set": {
                                "status": "completed", 
                                "chunks_count": 1,
                                "total_chunks": 1,
                                "processed_chunks": 1,
                                "progress": 100
                            }
                        }
                    )
                    
                    return {
                        "message": f"{file_extension.upper()} uploaded and chunked successfully",
                        "doc_id": doc_id,
                        "status": "completed",
                        "chunks_created": 1
                    }
                else:
                    logger.warning(f"⚠️ No chunk created for {file_extension.upper()}: {title}")
                    
            except Exception as chunk_error:
                logger.error(f"❌ Error auto-chunking {file_extension.upper()}: {chunk_error}")
                # Continue with normal flow even if chunking fails
                pass

        # Document will be processed immediately
        logger.info(f"📄 Document {doc_id} ready for processing")

        return {
            "message": "Document uploaded successfully",
            "doc_id": doc_id,
            "status": "pending"
        }

    except Exception as e:
        logger.error(f"Error uploading policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/policies", response_model=List[dict])
async def list_policies(
    status: Optional[DocumentStatus] = None,
    policy_type: Optional[PolicyType] = None,
    jurisdiction: Optional[str] = None,
    db = Depends(get_database)
):
    """List policy documents with optional filters"""
    try:
        query = {}
        if status:
            query["status"] = status
        if policy_type:
            query["policy_type"] = policy_type
        if jurisdiction:
            query["jurisdiction"] = jurisdiction

        cursor = db.documents.find(query).sort("uploaded_at", -1)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)

        return documents

    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/policies/folders", response_model=List[dict])
async def list_policy_folders(db = Depends(get_database)):
    """List all policy folders with document counts"""
    try:
        folders = []
        # Only get folders that actually exist in the database
        cursor = db.policy_folders.find()
        async for folder in cursor:
            # Count documents in this folder using the actual documents array
            doc_count = len(folder.get("documents", []))
            folder["document_count"] = doc_count
            folder["_id"] = str(folder["_id"])
            folders.append(folder)

        return folders

    except Exception as e:
        logger.error(f"Error listing policy folders: {e}")
        # Return empty list instead of throwing error
        print(f"❌ MongoDB Error: {e}")
        return []

@router.post("/policies/folders", response_model=dict)
async def create_policy_folder(
    request: CreatePolicyFolderRequest,
    db = Depends(get_database)
):
    """Create a new policy folder"""
    try:
        # Check if folder with same name already exists
        existing_folder = await db.policy_folders.find_one({"name": request.name})
        if existing_folder:
            raise HTTPException(
                status_code=400,
                detail="A policy folder with this name already exists"
            )

        # Create new policy folder
        folder_doc = PolicyFolder(
            name=request.name,
            policy_type=request.policy_type,
            documents=[]
        )
        
        result = await db.policy_folders.insert_one(folder_doc.dict(by_alias=True, exclude={"id"}))
        folder_id = str(result.inserted_id)
        
        print(f"✅ Created new policy folder: {request.name} (ID: {folder_id})")
        
        return {
            "message": "Policy folder created successfully",
            "folder_id": folder_id,
            "name": request.name,
            "policy_type": request.policy_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating policy folder: {e}")
        print(f"❌ Error creating policy folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies/folders/{folder_id}/documents", response_model=dict)
async def upload_document_to_folder(
    folder_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    jurisdiction: str = Form("Unknown"),
    version: str = Form("1.0"),
    effective_date: str = Form(...),
    db = Depends(get_database)
):
    """Upload a document to a specific policy folder"""
    try:
        # Convert string ID to ObjectId
        try:
            folder_object_id = ObjectId(folder_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid folder ID format")
        
        # Check if folder exists
        folder = await db.policy_folders.find_one({"_id": folder_object_id})
        if not folder:
            raise HTTPException(status_code=404, detail="Policy folder not found")
        
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
        
        # Create upload directory if it doesn't exist
        upload_dir = f"uploads/policies/{folder_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Use original filename exactly as uploaded
        file_extension = file.filename.split('.')[-1]
        file_path = os.path.join(upload_dir, file.filename)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Parse effective date
        try:
            effective_date_obj = datetime.fromisoformat(effective_date.replace('Z', '+00:00'))
        except ValueError:
            effective_date_obj = datetime.utcnow()
        
        # Calculate checksum
        checksum = generate_checksum(content)
        
        # Create document record
        document = Document(
            title=title,
            path=file_path,
            jurisdiction=jurisdiction,
            policy_type=folder["policy_type"],
            version=version,
            effective_date=effective_date_obj,
            checksum=checksum,
            status=DocumentStatus.PENDING,
            file_size=len(content),
            file_type=file_extension
        )
        
        # Save to database
        result = await db.documents.insert_one(document.dict(by_alias=True, exclude={"id"}))
        doc_id = str(result.inserted_id)
        
        # Add document to folder
        await db.policy_folders.update_one(
            {"_id": folder_object_id},
            {"$addToSet": {"documents": doc_id}}
        )
        
        # Auto-create single chunk for all supported files
        if file_extension.lower() in ['pdf', 'docx', 'txt']:
            try:
                logger.info(f"🔄 Auto-creating single chunk for: {title}")
                
                # Import single chunk function
                from core.single_chunk import create_single_chunk
                
                # Create single chunk
                single_chunk = await create_single_chunk(file_path, doc_id, title, file_extension)
                
                if single_chunk:
                    # Delete existing chunks for this document first
                    await db.chunks.delete_many({"doc_id": doc_id})
                    
                    # Insert single chunk
                    await db.chunks.insert_one(single_chunk)
                    logger.info(f"✅ Auto-created single chunk for {file_extension.upper()}")
                    
                    # Update document status to completed
                    await db.documents.update_one(
                        {"_id": ObjectId(doc_id)},
                        {
                            "$set": {
                                "status": "completed", 
                                "chunks_count": 1,
                                "total_chunks": 1,
                                "processed_chunks": 1,
                                "progress": 100
                            }
                        }
                    )
                    
                    return {
                        "message": f"{file_extension.upper()} uploaded and chunked successfully",
                        "doc_id": doc_id,
                        "folder_id": folder_id,
                        "status": "completed",
                        "chunks_created": 1
                    }
                else:
                    logger.warning(f"⚠️ No chunk created for {file_extension.upper()}: {title}")
                    
            except Exception as chunk_error:
                logger.error(f"❌ Error auto-chunking {file_extension.upper()}: {chunk_error}")
                # Continue with normal flow even if chunking fails
                pass
        
        logger.info(f"✅ Document uploaded to folder {folder_id}: {title}")
        
        return {
            "message": "Document uploaded successfully",
            "doc_id": doc_id,
            "folder_id": folder_id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document to folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/policies/folders/{folder_id}/documents", response_model=List[dict])
async def list_folder_documents(
    folder_id: str,
    db = Depends(get_database)
):
    """List documents in a specific policy folder"""
    try:
        # Convert string ID to ObjectId
        try:
            folder_object_id = ObjectId(folder_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid folder ID format")
        
        # Check if folder exists
        folder = await db.policy_folders.find_one({"_id": folder_object_id})
        if not folder:
            raise HTTPException(status_code=404, detail="Policy folder not found")
        
        # Get documents for this folder
        document_ids = folder.get("documents", [])
        if not document_ids:
            return []
        
        # Convert document IDs to ObjectIds
        document_object_ids = [ObjectId(doc_id) for doc_id in document_ids]
        cursor = db.documents.find({"_id": {"$in": document_object_ids}}).sort("uploaded_at", -1)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
        
        return documents
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing folder documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/policies/folders/by-type/{policy_type}/documents", response_model=List[dict])
async def list_documents_by_policy_type(
    policy_type: PolicyType,
    db = Depends(get_database)
):
    """List documents by policy type"""
    try:
        cursor = db.documents.find({"policy_type": policy_type}).sort("uploaded_at", -1)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)

        return documents

    except Exception as e:
        logger.error(f"Error listing folder documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/policies/{doc_id}")
async def delete_policy(
    doc_id: str,
    db = Depends(get_database)
):
    """Delete a policy document and all associated data"""
    try:
        # Try to find document by string ID first, then by ObjectId
        doc = await db.documents.find_one({"_id": doc_id})
        if not doc:
            # Try with ObjectId conversion
            try:
                doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
            except Exception:
                pass
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get the actual document ID (could be string or ObjectId)
        actual_doc_id = str(doc["_id"])

        # Delete file from disk
        if os.path.exists(doc["path"]):
            os.remove(doc["path"])

        # Delete associated chunks and embeddings
        chunk_ids = []
        async for chunk in db.chunks.find({"doc_id": actual_doc_id}):
            chunk_ids.append(chunk["_id"])

        if chunk_ids:
            await db.embeddings.delete_many({"chunk_id": {"$in": chunk_ids}})
            await db.chunks.delete_many({"doc_id": actual_doc_id})

        # Remove document from folder's documents array (try both string and ObjectId formats)
        await db.policy_folders.update_many(
            {"documents": actual_doc_id},
            {"$pull": {"documents": actual_doc_id}}
        )
        
        # Also try with the original doc_id parameter in case it's different
        if actual_doc_id != doc_id:
            await db.policy_folders.update_many(
                {"documents": doc_id},
                {"$pull": {"documents": doc_id}}
            )

        # Delete document using the actual document ID
        await db.documents.delete_one({"_id": doc["_id"]})

        return {"message": "Document deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def add_to_policy_folder(db, policy_type: PolicyType, doc_id: str):
    """Add document to policy folder, creating folder if it doesn't exist"""
    try:
        # Check if folder exists
        folder = await db.policy_folders.find_one({"policy_type": policy_type})
        
        if not folder:
            # Create new policy folder
            folder_doc = PolicyFolder(
                name=policy_type.value.title(),
                policy_type=policy_type,
                documents=[doc_id]
            )
            await db.policy_folders.insert_one(folder_doc.dict(by_alias=True, exclude={"id"}))
            print(f"✅ Created new policy folder: {policy_type.value}")
        else:
            # Add document to existing folder
            await db.policy_folders.update_one(
                {"policy_type": policy_type},
                {"$addToSet": {"documents": doc_id}}
            )
            print(f"✅ Added document to existing folder: {policy_type.value}")
            
    except Exception as e:
        logger.error(f"Error adding document to folder: {e}")
        print(f"❌ Error adding document to folder: {e}")

@router.post("/policies/reprocess/{doc_id}")
async def reprocess_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db = Depends(get_database)
):
    """Manually trigger reprocessing of a document"""
    try:
        # Get document details
        document = await db.documents.find_one({"_id": ObjectId(doc_id)})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document["status"] != "pending":
            raise HTTPException(status_code=400, detail="Document is not in pending status")
        
        # Get file path
        file_path = document["path"]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Create a new processor instance with the database connection
        from core.ingestion import DocumentProcessor
        processor = DocumentProcessor(db)
        
        # Process document directly (not in background for testing)
        try:
            result = await processor.process_document(doc_id, file_path, document.get("policy_type", "custom"))
            return {"message": "Document processed successfully", "doc_id": doc_id, "result": result}
        except Exception as e:
            logger.error(f"Error during document processing: {e}")
            return {"message": "Document processing failed", "doc_id": doc_id, "error": str(e)}
        
    except Exception as e:
        logger.error(f"Error reprocessing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/policies/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    db = Depends(get_database)
):
    """Get document processing status"""
    try:
        document = await db.documents.find_one(
            {"_id": ObjectId(doc_id)},
            {
                "status": 1,
                "progress": 1,
                "processed_chunks": 1,
                "total_chunks": 1,
                "error": 1,
                "attempts": 1,
                "next_action_at": 1,
                "lease": 1
            }
        )
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "doc_id": doc_id,
            "status": document.get("status", "unknown"),
            "progress": document.get("progress", 0),
            "processed_chunks": document.get("processed_chunks", 0),
            "total_chunks": document.get("total_chunks", 0),
            "error": document.get("error"),
            "attempts": document.get("attempts", 0),
            "next_action_at": document.get("next_action_at"),
            "lease": document.get("lease")
        }
        
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
