import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from core.schema import Document, Embedding, Questionnaire, Answer, Snapshot, PolicyFolder, UploadedDocument
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../env/example.env")

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB - NO CACHING, FRESH CONNECTION EVERY TIME"""
        try:
            # Use EXACT same URI as API (hardcoded to ensure consistency)
            mongodb_uri = "mongodb+srv://sanjayvarmacol2:Sanjay1234@cluster01.inf1rib.mongodb.net/?retryWrites=true&w=majority&appName=Cluster01"
            db_name = "policiesdb"
            
            logger.info(f"🔗 Connecting to MongoDB: {mongodb_uri}")
            logger.info(f"📊 Database: {db_name}")
            
            # Create fresh client every time with exact same parameters
            self.client = AsyncIOMotorClient(mongodb_uri)
            self.db = self.client[db_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {db_name}")
            
            # Create indexes (skip if they already exist)
            try:
                await self.create_indexes()
            except Exception as e:
                logger.warning(f"⚠️ Index creation warning: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    async def create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Documents collection indexes
            documents_collection = self.db.documents
            await documents_collection.create_indexes([
                IndexModel([("checksum", ASCENDING)], unique=True),
                IndexModel([("version", DESCENDING), ("effective_date", DESCENDING)]),
                IndexModel([("jurisdiction", ASCENDING), ("policy_type", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("uploaded_at", DESCENDING)]),
                # State machine indexes
                IndexModel([("status", ASCENDING), ("next_action_at", ASCENDING)]),
                IndexModel([("status", ASCENDING), ("attempts", ASCENDING)]),
                IndexModel([("lease", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])

            # Policy folders collection indexes
            policy_folders_collection = self.db.policy_folders
            await policy_folders_collection.create_indexes([
                IndexModel([("name", ASCENDING)]),
                IndexModel([("policy_type", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])

            # Embeddings collection indexes
            embeddings_collection = self.db.embeddings
            await embeddings_collection.create_indexes([
                IndexModel([("document_id", ASCENDING)]),
                IndexModel([("chunk_id", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])

            # Questionnaires collection indexes
            questionnaires_collection = self.db.questionnaires
            await questionnaires_collection.create_indexes([
                IndexModel([("title", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])

            # Answers collection indexes
            answers_collection = self.db.answers
            await answers_collection.create_indexes([
                IndexModel([("questionnaire_id", ASCENDING)]),
                IndexModel([("question_id", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])

            # Snapshots collection indexes
            snapshots_collection = self.db.snapshots
            await snapshots_collection.create_indexes([
                IndexModel([("document_id", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])

            # Cache collection removed - no longer using caching

            # Chunks collection indexes
            chunks_collection = self.db.chunks
            try:
                await chunks_collection.create_indexes([
                    IndexModel([("doc_id", ASCENDING)]),
                    IndexModel([("section", ASCENDING)]),
                    IndexModel([("created_at", DESCENDING)]),
                    IndexModel([("chunk_type", ASCENDING)]),
                    IndexModel([("doc_id", ASCENDING), ("chunk_id", ASCENDING)], unique=True),
                    # Vector search indexes
                    IndexModel([("policy_id", ASCENDING)]),
                    IndexModel([("filename", ASCENDING)]),
                    IndexModel([("page", ASCENDING)]),
                    IndexModel([("embedding", ASCENDING)])  # For vector search
                ])
            except Exception as e:
                if "existing index has the same name" in str(e):
                    logger.info("ℹ️ Chunks collection indexes already exist, skipping...")
                else:
                    logger.error(f"❌ Failed to create chunks indexes: {e}")

            # Audit questions collection indexes
            audit_questions_collection = self.db.audit_questions
            try:
                await audit_questions_collection.create_indexes([
                    IndexModel([("question_id", ASCENDING)], unique=True),
                    IndexModel([("questionnaire_id", ASCENDING)]),
                    IndexModel([("requirement_hash", ASCENDING)]),
                    IndexModel([("answered", ASCENDING)]),
                    IndexModel([("created_at", DESCENDING)])
                ])
            except Exception as e:
                if "existing index has the same name" in str(e):
                    logger.info("ℹ️ Audit questions collection indexes already exist, skipping...")
                else:
                    logger.error(f"❌ Failed to create audit questions indexes: {e}")

            logger.info("✅ Database indexes created successfully")

        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")

    @property
    def documents(self):
        return self.db.documents

    @property
    def policy_folders(self):
        return self.db.policy_folders

    @property
    def embeddings(self):
        return self.db.embeddings

    @property
    def questionnaires(self):
        return self.db.questionnaires

    @property
    def answers(self):
        return self.db.answers

    @property
    def snapshots(self):
        return self.db.snapshots

    # Cache property removed - no longer using caching

    @property
    def enhanced_analysis(self):
        return self.db.enhanced_analysis

    @property
    def chunks(self):
        return self.db.chunks

    @property
    def audit_questions(self):
        return self.db.audit_questions

# NO GLOBAL INSTANCE - CREATE FRESH EVERY TIME
async def get_database():
    """Get fresh database instance - NO CACHING"""
    db = Database()
    await db.connect()
    return db

async def init_db():
    """Initialize database connection - NO CACHING"""
    # This function is kept for compatibility but doesn't cache anything
    pass