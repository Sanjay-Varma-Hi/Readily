#!/usr/bin/env python3
"""
Check chunk content and structure
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/example.env")

async def check_chunk_content():
    """Check chunk content and structure"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("DB_NAME", "policiesdb")
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get total chunk count
        total_chunks = await db.chunks.count_documents({})
        print(f"📊 Total chunks in database: {total_chunks}")
        
        # Get chunks with text field
        chunks_with_text = await db.chunks.count_documents({"text": {"$exists": True, "$ne": ""}})
        print(f"📄 Chunks with text content: {chunks_with_text}")
        
        # Get chunks with summary field
        chunks_with_summary = await db.chunks.count_documents({"summary": {"$exists": True, "$ne": ""}})
        print(f"📝 Chunks with summary: {chunks_with_summary}")
        
        # Sample a few chunks
        print(f"\n🔍 Sample chunks:")
        async for i, chunk in enumerate(db.chunks.find().limit(3)):
            print(f"\n--- Chunk {i+1} ---")
            print(f"Fields: {list(chunk.keys())}")
            if 'text' in chunk:
                print(f"Text preview: {chunk['text'][:200]}...")
            if 'summary' in chunk:
                print(f"Summary: {chunk['summary']}")
            if 'page_from' in chunk:
                print(f"Page: {chunk.get('page_from', 'N/A')}-{chunk.get('page_to', 'N/A')}")
            if 'doc_id' in chunk:
                print(f"Document ID: {chunk['doc_id']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    asyncio.run(check_chunk_content())