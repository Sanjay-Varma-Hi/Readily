#!/usr/bin/env python3
"""
Test script to check what's in the answers collection
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from core.database import get_database

async def check_answers():
    """Check what's in the answers collection"""
    try:
        db = await get_database()
        
        print("🔍 Checking answers collection...")
        
        # Check if answers collection exists
        collections = await db.list_collection_names()
        print(f"📁 Collections: {collections}")
        
        if "answers" in collections:
            answers_count = await db.answers.count_documents({})
            print(f"📊 Answers collection has {answers_count} documents")
            
            if answers_count > 0:
                # Get one sample answer
                sample_answer = await db.answers.find_one()
                print(f"📄 Sample answer: {sample_answer}")
            else:
                print("❌ No answers found in the collection")
        else:
            print("❌ No 'answers' collection found")
        
        # Check questionnaires to see if they have answered questions
        if "questionnaires" in collections:
            questionnaire = await db.questionnaires.find_one()
            if questionnaire and "questions" in questionnaire:
                answered_questions = [q for q in questionnaire["questions"] if q.get("answered", False)]
                print(f"📊 Questionnaire has {len(answered_questions)} answered questions")
                if answered_questions:
                    print(f"📄 Sample answered question: {answered_questions[0]}")
        
    except Exception as e:
        print(f"❌ Error checking answers: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_answers())
