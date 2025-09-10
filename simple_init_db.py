#!/usr/bin/env python3
"""
Simple database initialization script for READILY
This script will create the database schema and indexes in MongoDB Atlas
"""

import os
import sys
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING
from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/example.env")

def init_database():
    """Initialize the database with collections and indexes"""
    try:
        # Connect to MongoDB Atlas
        mongodb_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("DB_NAME", "policiesdb")
        
        print(f"🔗 Connecting to MongoDB Atlas...")
        print(f"Database: {db_name}")
        
        client = MongoClient(mongodb_uri)
        db = client[db_name]
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas successfully!")
        
        # Create collections and indexes
        print("\n📊 Creating collections and indexes...")
        
        # 1. Documents collection
        print("Creating 'documents' collection...")
        db.documents.create_indexes([
            IndexModel([("checksum", ASCENDING)], unique=True),
            IndexModel([("version", DESCENDING), ("effective_date", DESCENDING)]),
            IndexModel([("jurisdiction", ASCENDING), ("policy_type", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("uploaded_at", DESCENDING)])
        ])
        print("✅ Documents collection ready")
        
        # 2. Chunks collection
        print("Creating 'chunks' collection...")
        db.chunks.create_indexes([
            IndexModel([("doc_id", ASCENDING), ("page_from", ASCENDING)]),
            IndexModel([("text_hash", ASCENDING)], unique=True),
            IndexModel([("created_at", DESCENDING)])
        ])
        print("✅ Chunks collection ready")
        
        # 3. Embeddings collection
        print("Creating 'embeddings' collection...")
        db.embeddings.create_indexes([
            IndexModel([("chunk_id", ASCENDING)], unique=True),
            IndexModel([("model", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)])
        ])
        print("✅ Embeddings collection ready")
        
        # 4. Questionnaires collection
        print("Creating 'questionnaires' collection...")
        db.questionnaires.create_indexes([
            IndexModel([("uploaded_at", DESCENDING)]),
            IndexModel([("status", ASCENDING)])
        ])
        print("✅ Questionnaires collection ready")
        
        # 5. Answers collection
        print("Creating 'answers' collection...")
        db.answers.create_indexes([
            IndexModel([("questionnaire_id", ASCENDING), ("qid", ASCENDING)], unique=True),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("confidence", DESCENDING)])
        ])
        print("✅ Answers collection ready")
        
        # 6. Snapshots collection
        print("Creating 'snapshots' collection...")
        db.snapshots.create_indexes([
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("embedding_model", ASCENDING)])
        ])
        print("✅ Snapshots collection ready")
        
        # 7. Policy folders collection (cache collection removed)
        print("Creating 'policy_folders' collection...")
        db.policy_folders.create_indexes([
            IndexModel([("policy_type", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)])
        ])
        print("✅ Policy folders collection ready")
        
        # 8. Uploaded documents collection
        print("Creating 'uploaded_documents' collection...")
        db.uploaded_documents.create_indexes([
            IndexModel([("uploaded_at", DESCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("questionnaire_id", ASCENDING)])
        ])
        print("✅ Uploaded documents collection ready")
        
        # Create initial policy folders
        print("\n📁 Creating initial policy folders...")
        policy_types = [
            "healthcare", "education", "environment", 
            "economic", "social", "technology", "governance"
        ]
        
        for policy_type in policy_types:
            db.policy_folders.update_one(
                {"policy_type": policy_type},
                {
                    "$setOnInsert": {
                        "name": policy_type.title(),
                        "policy_type": policy_type,
                        "documents": [],
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                },
                upsert=True
            )
        print("✅ Policy folders created")
        
        # Create initial snapshot
        print("\n📸 Creating initial snapshot...")
        db.snapshots.insert_one({
            "created_at": "2024-01-01T00:00:00Z",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "notes": "Initial snapshot for READILY database"
        })
        print("✅ Initial snapshot created")
        
        print(f"\n🎉 Database '{db_name}' initialized successfully!")
        print("\nCollections created:")
        print("  • documents - Policy document metadata")
        print("  • chunks - Text chunks from documents")
        print("  • embeddings - Vector embeddings for chunks")
        print("  • questionnaires - Questionnaire metadata and questions")
        print("  • answers - Generated answers with citations")
        print("  • snapshots - Index snapshots")
        print("  • cache - Cached results")
        print("  • policy_folders - Policy organization folders")
        print("  • uploaded_documents - Uploaded document tracking")
        
        print(f"\n🚀 You can now start the READILY application!")
        print("Run: python start_backend.py")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    init_database()

