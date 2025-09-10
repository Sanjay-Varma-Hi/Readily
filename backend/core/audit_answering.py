"""
Audit Question Management Module
Handles audit question operations without answering functionality
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.database import get_database

logger = logging.getLogger(__name__)

async def get_audit_questions(questionnaire_id: str = None) -> List[Dict[str, Any]]:
    """
    Get audit questions from the database
    
    Args:
        questionnaire_id: Optional questionnaire ID to filter by
    
    Returns:
        List of audit questions
    """
    try:
        db = await get_database()
        
        query = {}
        if questionnaire_id:
            query["questionnaire_id"] = questionnaire_id
        
        questions = await db.audit_questions.find(query).to_list(None)
        
        # Convert ObjectId to string
        for question in questions:
            question["_id"] = str(question["_id"])
        
        logger.info(f"✅ Retrieved {len(questions)} audit questions")
        return questions
        
    except Exception as e:
        logger.error(f"❌ Error retrieving audit questions: {e}")
        return []

async def get_audit_question(question_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific audit question by ID
    
    Args:
        question_id: The question ID
    
    Returns:
        The audit question if found, None otherwise
    """
    try:
        db = await get_database()
        question = await db.audit_questions.find_one({"question_id": question_id})
        
        if question:
            question["_id"] = str(question["_id"])
            return question
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error retrieving audit question {question_id}: {e}")
        return None

async def create_audit_question(question_data: Dict[str, Any]) -> str:
    """
    Create a new audit question
    
    Args:
        question_data: The question data
    
    Returns:
        The created question ID
    """
    try:
        db = await get_database()
        
        # Add timestamps
        question_data["created_at"] = datetime.utcnow()
        question_data["updated_at"] = datetime.utcnow()
        
        result = await db.audit_questions.insert_one(question_data)
        question_id = str(result.inserted_id)
        
        logger.info(f"✅ Created audit question with ID: {question_id}")
        return question_id
        
    except Exception as e:
        logger.error(f"❌ Error creating audit question: {e}")
        raise e

async def update_audit_question(question_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update an existing audit question
    
    Args:
        question_id: The question ID
        update_data: The update data
    
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        db = await get_database()
        
        # Add update timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await db.audit_questions.update_one(
            {"question_id": question_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated audit question {question_id}")
            return True
        else:
            logger.warning(f"⚠️ No changes made to audit question {question_id}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error updating audit question {question_id}: {e}")
        return False

async def delete_audit_question(question_id: str) -> bool:
    """
    Delete an audit question
    
    Args:
        question_id: The question ID
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        db = await get_database()
        
        result = await db.audit_questions.delete_one({"question_id": question_id})
        
        if result.deleted_count > 0:
            logger.info(f"✅ Deleted audit question {question_id}")
            return True
        else:
            logger.warning(f"⚠️ Audit question {question_id} not found")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error deleting audit question {question_id}: {e}")
        return False

async def get_questionnaire_questions(questionnaire_id: str) -> List[Dict[str, Any]]:
    """
    Get all questions for a specific questionnaire
    
    Args:
        questionnaire_id: The questionnaire ID
    
    Returns:
        List of questions for the questionnaire
    """
    try:
        db = await get_database()
        
        questions = await db.audit_questions.find(
            {"questionnaire_id": questionnaire_id}
        ).to_list(None)
        
        # Convert ObjectId to string
        for question in questions:
            question["_id"] = str(question["_id"])
        
        logger.info(f"✅ Retrieved {len(questions)} questions for questionnaire {questionnaire_id}")
        return questions
        
    except Exception as e:
        logger.error(f"❌ Error retrieving questions for questionnaire {questionnaire_id}: {e}")
        return []

async def search_questions(search_term: str) -> List[Dict[str, Any]]:
    """
    Search audit questions by text
    
    Args:
        search_term: The search term
    
    Returns:
        List of matching questions
    """
    try:
        db = await get_database()
        
        query = {
            "$or": [
                {"requirement": {"$regex": search_term, "$options": "i"}},
                {"reference": {"$regex": search_term, "$options": "i"}},
                {"question_id": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        questions = await db.audit_questions.find(query).to_list(None)
        
        # Convert ObjectId to string
        for question in questions:
            question["_id"] = str(question["_id"])
        
        logger.info(f"✅ Found {len(questions)} questions matching '{search_term}'")
        return questions
        
    except Exception as e:
        logger.error(f"❌ Error searching questions: {e}")
        return []