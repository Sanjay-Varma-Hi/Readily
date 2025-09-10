#!/usr/bin/env python3
"""
Debug the audit answering system step by step
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/example.env")

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.database import get_database

async def debug_audit_system():
    """Debug the audit system step by step"""
    
    print("🔍 Debugging audit system...")
    
    try:
        # Step 1: Test database connection
        print("\n1. Testing database connection...")
        db = await get_database()
        print("✅ Database connected")
        
        # Step 2: Test question processing (embedding generation removed)
        print("\n2. Testing question processing...")
        question = "Does the P&P state the MCP must respond to retrospective requests no longer than 14 calendar days from receipt?"
        print(f"✅ Question processed: {question[:50]}...")
        
        # Step 3: Test chunk search
        print("\n3. Testing chunk search...")
        query = {
            "text": {
                "$regex": "retrospective|request|calendar|days|MCP|respond",
                "$options": "i"
            }
        }
        
        cursor = db.chunks.find(query).limit(5)
        chunks = []
        async for chunk in cursor:
            formatted_chunk = {
                "policy_id": chunk.get("doc_id", "unknown"),
                "filename": chunk.get("filename", "unknown"),
                "page": chunk.get("page", 1),
                "text": chunk.get("text", ""),
                "score": 0.8
            }
            chunks.append(formatted_chunk)
        
        print(f"✅ Found {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i+1}: {chunk['filename']} - {chunk['text'][:100]}...")
        
        # Step 4: Test simple answer generation (DeepSeek removed)
        print("\n4. Testing simple answer generation...")
        if chunks:
            print(f"✅ Found {len(chunks)} chunks for answer generation")
            print("⚠️ DeepSeek LLM integration removed - using simple text matching")
        else:
            print("⚠️ No chunks found, skipping answer generation test")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            await db.client.close()

if __name__ == "__main__":
    asyncio.run(debug_audit_system())
