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
    
    def __bool__(self):
        """Prevent boolean evaluation of database objects"""
        return True

    async def connect(self):
        """Connect to MongoDB - NO CACHING, FRESH CONNECTION EVERY TIME"""
        try:
            # Get MongoDB URI from environment variables with environment-specific fallback
            mongodb_uri = os.getenv("MONGODB_URI")
            db_name = os.getenv("DB_NAME", "policiesdb")
            
            # Check if we're in production (Render) and use production-specific settings
            is_production = os.getenv("RENDER", "false").lower() == "true"
            
            if not mongodb_uri:
                # Try alternative environment variable names
                mongodb_uri = os.getenv("MONGODB_URL") or os.getenv("DATABASE_URL")
                if not mongodb_uri:
                    raise ValueError("MONGODB_URI environment variable is not set")
            
            # Log connection attempt (without exposing credentials)
            logger.info(f"🔗 Connecting to MongoDB...")
            logger.info(f"📊 Database: {db_name}")
            logger.info(f"🌍 Environment: {'Production' if is_production else 'Development'}")
            
            # Log URI format for debugging (without credentials)
            uri_parts = mongodb_uri.split('@')
            if len(uri_parts) > 1:
                logger.info(f"🔗 MongoDB Host: {uri_parts[1].split('/')[0]}")
            else:
                logger.info(f"🔗 MongoDB URI format: {mongodb_uri[:20]}...")
            
            # Create fresh client with proper Atlas SRV URI format
            # No deprecated SSL options - let Atlas SRV handle SSL automatically
            self.client = AsyncIOMotorClient(
                mongodb_uri,
                serverSelectionTimeoutMS=10000,  # Increased timeout
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            # Get database - use default database from URI or specified db_name
            default_db = self.client.get_default_database()
            self.db = default_db if default_db is not None else self.client[db_name]
            
            # Test connection with retry logic
            max_retries = 5  # Increased retries
            for attempt in range(max_retries):
                try:
                    await self.client.admin.command('ping')
                    logger.info(f"✅ Connected to MongoDB: {db_name}")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Connection attempt {attempt + 1} failed, retrying... Error: {e}")
                        await asyncio.sleep(3)  # Wait 3 seconds before retry
                    else:
                        logger.error(f"❌ All connection attempts failed. Last error: {e}")
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
            try:
                # Check existing indexes first
                existing_indexes = await embeddings_collection.list_indexes().to_list(length=None)
                existing_index_names = [idx['name'] for idx in existing_indexes]
                
                indexes_to_create = []
                
                # Only create indexes that don't already exist
                if "document_id_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("document_id", ASCENDING)]))
                if "chunk_id_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("chunk_id", ASCENDING)]))
                if "created_at_-1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("created_at", DESCENDING)]))
                
                if indexes_to_create:
                    await embeddings_collection.create_indexes(indexes_to_create)
                    logger.info(f"✅ Created {len(indexes_to_create)} new indexes for embeddings collection")
                else:
                    logger.info("ℹ️ All embeddings collection indexes already exist, skipping...")
                    
            except Exception as e:
                logger.error(f"❌ Failed to create embeddings indexes: {e}")

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
                # Check existing indexes first
                existing_indexes = await chunks_collection.list_indexes().to_list(length=None)
                existing_index_names = [idx['name'] for idx in existing_indexes]
                
                indexes_to_create = []
                
                # Only create indexes that don't already exist
                if "doc_id_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("doc_id", ASCENDING)]))
                if "section_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("section", ASCENDING)]))
                if "created_at_-1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("created_at", DESCENDING)]))
                if "chunk_type_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("chunk_type", ASCENDING)]))
                if "doc_id_1_chunk_id_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("doc_id", ASCENDING), ("chunk_id", ASCENDING)], unique=True))
                
                # Vector search indexes (only if they don't exist)
                if "policy_id_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("policy_id", ASCENDING)]))
                if "filename_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("filename", ASCENDING)]))
                if "page_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("page", ASCENDING)]))
                if "embedding_1" not in existing_index_names:
                    indexes_to_create.append(IndexModel([("embedding", ASCENDING)]))
                
                if indexes_to_create:
                    await chunks_collection.create_indexes(indexes_to_create)
                    logger.info(f"✅ Created {len(indexes_to_create)} new indexes for chunks collection")
                else:
                    logger.info("ℹ️ All chunks collection indexes already exist, skipping...")
                    
            except Exception as e:
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
        self.client = None  # Add client attribute
    
    def __bool__(self):
        """Prevent boolean evaluation of database objects"""
        return True
    
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
    
    def project(self, *args, **kwargs):
        """Return self to allow chaining, but operations will fail"""
        return self
    
    def limit(self, *args, **kwargs):
        """Return self to allow chaining, but operations will fail"""
        return self
    
    def to_list(self, *args, **kwargs):
        """Return empty list for async operations"""
        async def _to_list():
            return []
        return _to_list()
    
    def find(self, *args, **kwargs):
        """Return self to allow chaining, but operations will fail"""
        return self
    
    def limit(self, *args, **kwargs):
        """Return self to allow chaining, but operations will fail"""
        return self
    
    def __aiter__(self):
        """Make it async iterable - return empty async generator"""
        return self._async_generator()
    
    async def _async_generator(self):
        """Empty async generator that yields nothing"""
        if False:  # This ensures it's a generator but never yields
            yield
    
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
    
    async def replace_one(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def count_documents(self, *args, **kwargs):
        return 0  # Return 0 for count operations
    
    def aggregate(self, *args, **kwargs):
        """Return self to allow chaining, but operations will fail"""
        return self
    
    async def insert_many(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    async def update_many(self, *args, **kwargs):
        raise HTTPException(status_code=503, detail=f"Database connection failed: {self.error_message}")
    
    def list_indexes(self, *args, **kwargs):
        """Return empty list for index operations"""
        return []

async def init_db():
    """Initialize database connection - NO CACHING"""
    # This function is kept for compatibility but doesn't cache anything
    pass