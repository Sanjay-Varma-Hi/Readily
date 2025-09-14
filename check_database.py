#!/usr/bin/env python3
"""
Check MongoDB database structure and content
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/example.env")

async def check_database():
    """Check database structure and content"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("DB_NAME", "policiesdb")
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # List all collections
        collections = await db.list_collection_names()
        print(f"\n📋 Collections in database '{db_name}':")
        for collection in collections:
            count = await db[collection].count_documents({})
            print(f"  - {collection}: {count} documents")
        
        # Check chunks collection structure
        if 'chunks' in collections:
            print(f"\n🔍 Chunks collection sample:")
            sample_chunk = await db.chunks.find_one()
            if sample_chunk:
                print(f"Sample chunk fields: {list(sample_chunk.keys())}")
                print(f"Sample chunk content preview: {str(sample_chunk)[:200]}...")
        
        # Check audit_questions collection
        if 'audit_questions' in collections:
            print(f"\n📝 Audit questions collection sample:")
            sample_question = await db.audit_questions.find_one()
            if sample_question:
                print(f"Sample question fields: {list(sample_question.keys())}")
                print(f"Sample question: {sample_question.get('requirement', 'N/A')[:100]}...")
        
        # Check answers collection
        if 'answers' in collections:
            print(f"\n💾 Answers collection sample:")
            sample_answer = await db.answers.find_one()
            if sample_answer:
                print(f"Sample answer fields: {list(sample_answer.keys())}")
                print(f"Sample answer: {sample_answer.get('answer', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    asyncio.run(check_database())