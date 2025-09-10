#!/usr/bin/env python3
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def reset_document():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb+srv://sankarsanjayvarmathotakura:Sanju123@cluster0.6qj8h.mongodb.net/")
    db = client.policiesdb
    
    # Document ID from the image
    doc_id = "68c05bf860c12c1fabcb3ccd"
    
    # Update document status to pending
    result = await db.documents.update_one(
        {"_id": ObjectId(doc_id)},
        {
            "$set": {
                "status": "pending",
                "progress": 0,
                "processed_chunks": 0,
                "total_chunks": 0,
                "attempts": 0,
                "next_action_at": None,
                "lease": None,
                "error": None
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Document {doc_id} reset to pending status")
    else:
        print(f"❌ Failed to reset document {doc_id}")
    
    # Check document status
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    print(f"📄 Document status: {doc.get('status')}")
    print(f"📄 Document path: {doc.get('path')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(reset_document())
