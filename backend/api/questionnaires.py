from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from typing import List
import os
import aiofiles
from bson import ObjectId
from core.database import get_database
from core.schema import Questionnaire, Question, DocumentStatus, generate_checksum, normalize_question, extract_tags_from_question, generate_text_hash
from core.extraction import extract_questions_from_pdf
from core.audit_extraction import extract_audit_questions_from_pdf
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/questionnaires", response_model=dict)
async def upload_questionnaire(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db = Depends(get_database)
):
    """Upload a questionnaire PDF and extract questions"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed for questionnaires"
            )

        # Check file size
        max_size = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {os.getenv('MAX_FILE_SIZE_MB', '50')}MB"
            )

        # Generate checksum
        checksum = generate_checksum(content)

        # Save file to disk
        upload_dir = "uploads/questionnaires"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{checksum}_{file.filename}")
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Create questionnaire record
        questionnaire = Questionnaire(
            filename=file.filename,
            status=DocumentStatus.PENDING
        )

        # Save to database
        result = await db.questionnaires.insert_one(questionnaire.dict(by_alias=True, exclude={"id"}))
        questionnaire_id = str(result.inserted_id)

        # Queue for background processing
        background_tasks.add_task(process_questionnaire, questionnaire_id, file_path, db)

        return {
            "message": "Questionnaire uploaded successfully",
            "questionnaire_id": questionnaire_id,
            "status": "pending"
        }

    except Exception as e:
        logger.error(f"Error uploading questionnaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questionnaires", response_model=List[dict])
async def list_questionnaires(
    db = Depends(get_database)
):
    """List all uploaded questionnaires"""
    try:
        cursor = db.questionnaires.find().sort("uploaded_at", -1)
        questionnaires = []
        async for q in cursor:
            q["_id"] = str(q["_id"])
            questionnaires.append(q)

        return questionnaires

    except Exception as e:
        logger.error(f"Error listing questionnaires: {e}")
        # Return empty list instead of throwing error
        print(f"❌ MongoDB Error: {e}")
        return []

@router.get("/questionnaires/{questionnaire_id}", response_model=dict)
async def get_questionnaire(
    questionnaire_id: str,
    db = Depends(get_database)
):
    """Get a specific questionnaire with its questions"""
    try:
        questionnaire = await db.questionnaires.find_one({"_id": ObjectId(questionnaire_id)})
        if not questionnaire:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        questionnaire["_id"] = str(questionnaire["_id"])
        return questionnaire

    except Exception as e:
        logger.error(f"Error getting questionnaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questionnaires/{questionnaire_id}/questions", response_model=List[dict])
async def get_questionnaire_questions(
    questionnaire_id: str,
    db = Depends(get_database)
):
    """Get questions from a specific questionnaire"""
    try:
        questionnaire = await db.questionnaires.find_one({"_id": ObjectId(questionnaire_id)})
        if not questionnaire:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        return questionnaire.get("questions", [])

    except Exception as e:
        logger.error(f"Error getting questionnaire questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questionnaires/{questionnaire_id}/questions-formatted")
async def get_questionnaire_questions_formatted(
    questionnaire_id: str,
    db = Depends(get_database)
):
    """Get questions for a specific questionnaire with references in audit format"""
    try:
        questionnaire = await db.questionnaires.find_one({"_id": ObjectId(questionnaire_id)})
        if not questionnaire:
            raise HTTPException(status_code=404, detail="Questionnaire not found")
        
        questions = questionnaire.get("questions", [])
        
        # Format questions with references for frontend
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                "question_id": q.get("question_id", q.get("qid", "")),
                "qid": q.get("qid", ""),
                "requirement": q.get("text", ""),
                "reference": q.get("reference", ""),
                "tags": q.get("tags", []),
                "answered": q.get("answered", False)
            })
        
        return {
            "questionnaire_id": questionnaire_id,
            "filename": questionnaire.get("filename", ""),
            "status": questionnaire.get("status", "unknown"),
            "questions": formatted_questions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting formatted questionnaire questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/questionnaires/{questionnaire_id}")
async def delete_questionnaire(
    questionnaire_id: str,
    db = Depends(get_database)
):
    """Delete a questionnaire and all associated data"""
    try:
        # Get questionnaire details
        questionnaire = await db.questionnaires.find_one({"_id": ObjectId(questionnaire_id)})
        if not questionnaire:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        # Delete file from disk
        file_path = f"uploads/questionnaires/{questionnaire['filename']}"
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete associated answers
        await db.answers.delete_many({"questionnaire_id": questionnaire_id})

        # Delete questionnaire
        await db.questionnaires.delete_one({"_id": ObjectId(questionnaire_id)})

        return {"message": "Questionnaire deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting questionnaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_questionnaire(questionnaire_id: str, file_path: str, db):
    """Process questionnaire in background to extract questions"""
    try:
        # Try enhanced audit extraction first
        audit_questions = await extract_audit_questions_from_pdf(file_path)
        
        questions = []
        if audit_questions:
            # Process audit questions with references
            logger.info(f"Using enhanced audit extraction for {len(audit_questions)} questions")
            for audit_q in audit_questions:
                qid = f"Q{audit_q['question_id']}"
                # Generate unique question ID combining questionnaire ID and question number
                unique_question_id = f"{questionnaire_id}_{audit_q['question_id']}"
                normalized = normalize_question(audit_q['requirement'])
                tags = extract_tags_from_question(audit_q['requirement'])
                text_hash = generate_text_hash(audit_q['requirement'])
                
                question = Question(
                    qid=qid,
                    text=audit_q['requirement'],
                    normalized=normalized,
                    tags=tags,
                    hash=text_hash,
                    reference=audit_q['reference']
                )
                question_dict = question.dict()
                # Add unique question ID and answered status
                question_dict['question_id'] = unique_question_id
                question_dict['answered'] = False
                questions.append(question_dict)
        else:
            # Fallback to original extraction
            logger.info("Using fallback extraction method")
            questions_text = await extract_questions_from_pdf(file_path)
            
            for i, question_text in enumerate(questions_text, 1):
                qid = f"Q{i}"
                # Generate unique question ID combining questionnaire ID and question number
                unique_question_id = f"{questionnaire_id}_{i}"
                normalized = normalize_question(question_text)
                tags = extract_tags_from_question(question_text)
                text_hash = generate_text_hash(question_text)
                
                question = Question(
                    qid=qid,
                    text=question_text,
                    normalized=normalized,
                    tags=tags,
                    hash=text_hash,
                    reference=""
                )
                question_dict = question.dict()
                # Add unique question ID and answered status
                question_dict['question_id'] = unique_question_id
                question_dict['answered'] = False
                questions.append(question_dict)
        
        # Update questionnaire with extracted questions
        await db.questionnaires.update_one(
            {"_id": ObjectId(questionnaire_id)},
            {
                "$set": {
                    "questions": questions,
                    "status": DocumentStatus.READY
                }
            }
        )
        
        logger.info(f"Processed questionnaire {questionnaire_id} with {len(questions)} questions")

    except Exception as e:
        logger.error(f"Error processing questionnaire {questionnaire_id}: {e}")
        # Update status to error
        await db.questionnaires.update_one(
            {"_id": ObjectId(questionnaire_id)},
            {"$set": {"status": DocumentStatus.ERROR}}
        )
