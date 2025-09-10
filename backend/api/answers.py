from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from core.database import get_database
from core.answering import generate_answers_batch
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class BatchAnswerRequest(BaseModel):
    questionnaire_id: str
    qids: Optional[List[str]] = None

@router.post("/answers/batch", response_model=dict)
async def generate_batch_answers(
    background_tasks: BackgroundTasks,
    request: BatchAnswerRequest,
    db = Depends(get_database)
):
    """Generate answers for questions in a questionnaire"""
    try:
        # Get questionnaire
        questionnaire = await db.questionnaires.find_one({"_id": request.questionnaire_id})
        if not questionnaire:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        if questionnaire["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail="Questionnaire is not ready. Please wait for processing to complete."
            )

        # Filter questions if specific qids provided
        questions = questionnaire.get("questions", [])
        if request.qids:
            questions = [q for q in questions if q["qid"] in request.qids]

        if not questions:
            raise HTTPException(status_code=400, detail="No questions found")

        # Queue for background processing
        background_tasks.add_task(process_answers, request.questionnaire_id, questions, db)

        return {
            "message": "Answer generation started",
            "questionnaire_id": request.questionnaire_id,
            "questions_count": len(questions),
            "status": "processing"
        }

    except Exception as e:
        logger.error(f"Error starting batch answer generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/answers", response_model=List[dict])
async def get_answers(
    questionnaire_id: Optional[str] = None,
    qid: Optional[str] = None,
    db = Depends(get_database)
):
    """Get answers with optional filters"""
    try:
        query = {}
        if questionnaire_id:
            query["questionnaire_id"] = questionnaire_id
        if qid:
            query["qid"] = qid

        cursor = db.answers.find(query).sort("created_at", -1)
        answers = []
        async for answer in cursor:
            answer["_id"] = str(answer["_id"])
            answers.append(answer)

        return answers

    except Exception as e:
        logger.error(f"Error getting answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/answers/{questionnaire_id}/summary", response_model=dict)
async def get_answer_summary(
    questionnaire_id: str,
    db = Depends(get_database)
):
    """Get summary statistics for answers in a questionnaire"""
    try:
        # Get all answers for the questionnaire
        cursor = db.answers.find({"questionnaire_id": questionnaire_id})
        answers = []
        async for answer in cursor:
            answers.append(answer)

        if not answers:
            return {
                "questionnaire_id": questionnaire_id,
                "total_questions": 0,
                "answered_questions": 0,
                "average_confidence": 0.0,
                "answers_with_citations": 0,
                "not_found_count": 0
            }

        # Calculate statistics
        total_questions = len(answers)
        answered_questions = len([a for a in answers if a["answer"] != "Not found in provided docs."])
        not_found_count = total_questions - answered_questions
        
        confidences = [a["confidence"] for a in answers if a["confidence"] is not None]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        answers_with_citations = len([a for a in answers if a.get("citations")])

        return {
            "questionnaire_id": questionnaire_id,
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "average_confidence": round(average_confidence, 3),
            "answers_with_citations": answers_with_citations,
            "not_found_count": not_found_count
        }

    except Exception as e:
        logger.error(f"Error getting answer summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/answers/{questionnaire_id}")
async def delete_answers(
    questionnaire_id: str,
    db = Depends(get_database)
):
    """Delete all answers for a questionnaire"""
    try:
        result = await db.answers.delete_many({"questionnaire_id": questionnaire_id})
        return {
            "message": f"Deleted {result.deleted_count} answers",
            "deleted_count": result.deleted_count
        }

    except Exception as e:
        logger.error(f"Error deleting answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_answers(questionnaire_id: str, questions: List[dict], db):
    """Process answers in background"""
    try:
        # Generate answers using the answering module
        answers = await generate_answers_batch(questionnaire_id, questions)
        
        # Save answers to database
        if answers:
            await db.answers.insert_many(answers)
            logger.info(f"Generated {len(answers)} answers for questionnaire {questionnaire_id}")
        else:
            logger.warning(f"No answers generated for questionnaire {questionnaire_id}")

    except Exception as e:
        logger.error(f"Error processing answers for questionnaire {questionnaire_id}: {e}")
