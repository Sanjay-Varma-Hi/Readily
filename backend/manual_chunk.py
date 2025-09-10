#!/usr/bin/env python3
"""
Manual chunking script to process uploaded PDFs
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from core.database import get_database, init_db
from core.pdf_chunker import get_pdf_chunker
from bson import ObjectId

async def chunk_document(doc_id: str):
    """Manually chunk a specific document"""
    try:
        # Initialize database
        await init_db()
        db = await get_database()
        
        print(f"🔄 Processing document: {doc_id}")
        
        # Get document info
        try:
            doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
        except:
            # Try as string if ObjectId fails
            doc = await db.documents.find_one({"_id": doc_id})
        
        if not doc:
            print(f"❌ Document {doc_id} not found")
            return
        
        print(f"📄 Document: {doc['title']}")
        print(f"📁 File path: {doc['path']}")
        print(f"📊 Current status: {doc['status']}")
        
        # Check if file exists
        if not os.path.exists(doc['path']):
            print(f"❌ File not found: {doc['path']}")
            return
        
        # Get PDF chunker
        chunker = get_pdf_chunker()
        
        # Chunk the PDF
        print("🔄 Starting PDF chunking...")
        chunks = chunker.chunk_pdf_to_json(doc['path'], doc_id, doc['title'])
        
        if not chunks:
            print("❌ No chunks created")
            return
        
        print(f"✅ Created {len(chunks)} chunks")
        
        # Store chunks in database
        chunk_documents = []
        for chunk in chunks:
            chunk_doc = {
                **chunk,
                "doc_id": doc_id,
                "created_at": chunk.get("created_at"),
                "file_type": "pdf",
                "chunk_type": "structured"
            }
            chunk_documents.append(chunk_doc)
        
        # Insert chunks
        result = await db.chunks.insert_many(chunk_documents)
        print(f"✅ Stored {len(result.inserted_ids)} chunks in database")
        
        # Update document status
        await db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "status": "completed", 
                "chunks_count": len(chunks),
                "total_chunks": len(chunks),
                "processed_chunks": len(chunks)
            }}
        )
        
        print(f"✅ Document status updated to completed")
        
        # Show chunk summary
        print("\n📋 Chunk Summary:")
        for i, chunk in enumerate(chunks):
            print(f"  {i+1}. {chunk['chunk_id']} - {chunk.get('section', 'No section')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python manual_chunk.py <document_id>")
        print("Example: python manual_chunk.py 68c0847319bffdfa2beb9477")
        return
    
    doc_id = sys.argv[1]
    success = await chunk_document(doc_id)
    
    if success:
        print("\n🎉 Chunking completed successfully!")
    else:
        print("\n💥 Chunking failed!")

if __name__ == "__main__":
    asyncio.run(main())
