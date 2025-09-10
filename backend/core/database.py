import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from fastapi import HTTPException
from core.schema import Document, Embedding, Questionnaire, Answer, Snapshot, PolicyFolder, UploadedDocument
import logging
from dotenv import load_dotenv

# Load environment variables
# Try to load from local env file first, then fall back to system env vars
if os.path.exists("../env/example.env"):
    load_dotenv("../env/example.env")
else:
    # In production (Render), environment variables are set directly
    pass

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB - NO CACHING, FRESH CONNECTION EVERY TIME"""
        try:
            # Get MongoDB URI from environment variables
            mongodb_uri = os.getenv("MONGODB_URI")
            db_name = os.getenv("DB_NAME", "policiesdb")
            
            if not mongodb_uri:
                raise ValueError("MONGODB_URI environment variable is not set")
            
            # Log connection attempt (without exposing credentials)
            logger.info(f"🔗 Connecting to MongoDB...")
            logger.info(f"📊 Database: {db_name}")
            
            # Create fresh client every time with exact same parameters
            # Add SSL configuration for Render compatibility
            self.client = AsyncIOMotorClient(
                mongodb_uri,
                tls=True,
                tlsAllowInvalidCertificates=False,  # Use only this option, not tlsInsecure
                serverSelectionTimeoutMS=15000,  # Increased timeout for Render
                connectTimeoutMS=15000,  # Increased timeout for Render
                socketTimeoutMS=15000,  # Added socket timeout
                retryWrites=True,
                retryReads=True,
                maxPoolSize=10,  # Connection pool size
                minPoolSize=1,   # Minimum connections
                maxIdleTimeMS=30000,  # Close idle connections after 30s
                waitQueueTimeoutMS=5000,  # Wait for connection from pool
                heartbeatFrequencyMS=10000  # Heartbeat frequency
            )
            self.db = self.client[db_name]
            
            # Test connection with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.client.admin.command('ping')
                    logger.info(f"✅ Connected to MongoDB: {db_name}")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Connection attempt {attempt + 1} failed, retrying... Error: {e}")
                        await asyncio.sleep(2)  # Wait 2 seconds before retry
                    else:
                        raise e
            
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
    try:
        db = Database()
        await db.connect()
        return db
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        # Return a mock database object that will handle errors gracefully
        return MockDatabase(str(e))

class MockDatabase:
    """Mock database for when connection fails"""
    def __init__(self, error_message):
        self.error_message = error_message
        self._mock_collections = {}
    
    def __getattr__(self, name):
        if name in ['documents', 'questionnaires', 'answers', 'policy_folders', 'embeddings', 'snapshots', 'chunks', 'audit_questions']:
            return MockCollection(self.error_message)
        return super().__getattribute__(name)

class MockCollection:
    """Mock collection for when database connection fails"""
    def __init__(self, error_message):
        self.error_message = error_message
    
    def sort(self, *args, **kwargs):
        """Return self to allow chaining, but operations will fail"""
        return self
    
    def __aiter__(self):
        """Make it async iterable - return empty async generator"""
        return self._async_generator()
    
    async def _async_generator(self):
        """Empty async generator that yields nothing"""
        if False:  # This ensures it's a generator but never yields
            yield
    
    async def find(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def find_one(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def insert_one(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def update_one(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def delete_one(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def delete_many(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def create_indexes(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")

async def init_db():
    """Initialize database connection - NO CACHING"""
    # This function is kept for compatibility but doesn't cache anything
    pass