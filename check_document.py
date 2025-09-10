#!/usr/bin/env python3
import asyncio
import sys
import os

# Add backend to path
sys.path.append('backend')

from core.database import init_db, get_database
from bson import ObjectId

async def check_document():
    # Initialize database
    await init_db()
    db = await get_database()
    
    # Document ID from the image
    doc_id = "68c05bf860c12c1fabcb3ccd"
    
    # Check document details
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if doc:
        print(f"📄 Document ID: {doc_id}")
        print(f"📄 Title: {doc.get('title')}")
        print(f"📄 Status: {doc.get('status')}")
        print(f"📄 Path: {doc.get('path')}")
        print(f"📄 Progress: {doc.get('progress')}")
        print(f"📄 Total chunks: {doc.get('total_chunks')}")
        print(f"📄 Processed chunks: {doc.get('processed_chunks')}")
        print(f"📄 Attempts: {doc.get('attempts')}")
        print(f"📄 Lease: {doc.get('lease')}")
        print(f"📄 Next action: {doc.get('next_action_at')}")
        print(f"📄 Error: {doc.get('error')}")
    else:
        print(f"❌ Document {doc_id} not found")
    
    # Check for any pending documents
    pending_docs = await db.documents.find({"status": "pending"}).to_list(length=10)
    print(f"\n📋 Pending documents: {len(pending_docs)}")
    for doc in pending_docs:
        print(f"  - {doc['_id']}: {doc.get('title')} ({doc.get('status')})")

if __name__ == "__main__":
    asyncio.run(check_document())
