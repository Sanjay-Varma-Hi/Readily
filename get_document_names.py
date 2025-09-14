#!/usr/bin/env python3
"""
Get document names from the database
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/example.env")

async def get_document_names():
    """Get document names from the database"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("DB_NAME", "policiesdb")
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get all documents
        documents = []
        async for doc in db.documents.find({}, {"_id": 1, "title": 1}):
            documents.append({
                "id": str(doc["_id"]),
                "title": doc.get("title", f"Document {doc['_id']}")
            })
        
        print(f"📚 Found {len(documents)} documents:")
        for doc in documents:
            print(f"  - {doc['title']} (ID: {doc['id']})")
        
        return documents
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    asyncio.run(get_document_names())