import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database
from core.schema import extract_tags_from_question
import hashlib

logger = logging.getLogger(__name__)

def generate_requirement_hash(requirement: str) -> str:
    """Generate a hash for the requirement text"""
    return hashlib.sha256(requirement.encode()).hexdigest()

async def create_audit_question(question_id: str, questionnaire_id: str, requirement: str, reference: str = "") -> Dict[str, Any]:
    """Create an audit question in the audit_questions collection"""
    try:
        db = await get_database()
        
        # Generate requirement hash for caching
        requirement_hash = generate_requirement_hash(requirement)
        
        # Extract tags from requirement
        tags = extract_tags_from_question(requirement)
        
        audit_question = {
            "question_id": question_id,
            "questionnaire_id": questionnaire_id,
            "requirement": requirement,
            "reference": reference,
            "requirement_hash": requirement_hash,
            "tags": tags,
            "answered": False
        }
        
        # Insert into audit_questions collection
        result = await db.audit_questions.insert_one(audit_question)
        
        logger.info(f"✅ Created audit question: {question_id}")
        return audit_question
        
    except Exception as e:
        logger.error(f"❌ Error creating audit question: {e}")
        raise

async def get_audit_question(question_id: str) -> Optional[Dict[str, Any]]:
    """Get an audit question by question_id"""
    try:
        db = await get_database()
        
        audit_question = await db.audit_questions.find_one({"question_id": question_id})
        
        if audit_question:
            audit_question["_id"] = str(audit_question["_id"])
            return audit_question
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting audit question: {e}")
        return None

async def get_audit_questions_by_questionnaire(questionnaire_id: str) -> List[Dict[str, Any]]:
    """Get all audit questions for a questionnaire"""
    try:
        db = await get_database()
        
        cursor = db.audit_questions.find({"questionnaire_id": questionnaire_id})
        questions = []
        async for question in cursor:
            question["_id"] = str(question["_id"])
            questions.append(question)
        
        return questions
        
    except Exception as e:
        logger.error(f"❌ Error getting audit questions for questionnaire: {e}")
        return []

async def mark_question_answered(question_id: str) -> bool:
    """Mark an audit question as answered"""
    try:
        db = await get_database()
        
        result = await db.audit_questions.update_one(
            {"question_id": question_id},
            {"$set": {"answered": True}}
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Marked question {question_id} as answered")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error marking question as answered: {e}")
        return False

async def migrate_questions_to_audit_collection(questionnaire_id: str) -> int:
    """Migrate questions from questionnaires collection to audit_questions collection"""
    try:
        db = await get_database()
        
        # Get questionnaire with questions
        questionnaire = await db.questionnaires.find_one({"_id": ObjectId(questionnaire_id)})
        if not questionnaire:
            logger.warning(f"⚠️ Questionnaire {questionnaire_id} not found")
            return 0
        
        questions = questionnaire.get("questions", [])
        migrated_count = 0
        
        for question in questions:
            question_id = question.get("question_id")
            if not question_id:
                continue
            
            # Check if already exists in audit_questions
            existing = await db.audit_questions.find_one({"question_id": question_id})
            if existing:
                continue
            
            # Create audit question
            await create_audit_question(
                question_id=question_id,
                questionnaire_id=questionnaire_id,
                requirement=question.get("text", ""),
                reference=question.get("reference", "")
            )
            migrated_count += 1
        
        logger.info(f"✅ Migrated {migrated_count} questions to audit_questions collection")
        return migrated_count
        
    except Exception as e:
        logger.error(f"❌ Error migrating questions: {e}")
        return 0
