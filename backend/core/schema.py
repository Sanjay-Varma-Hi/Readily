from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    COMPLETED = "completed"
    ERROR = "error"

class PolicyType(str, Enum):
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    ENVIRONMENT = "environment"
    ECONOMIC = "economic"
    SOCIAL = "social"
    TECHNOLOGY = "technology"
    GOVERNANCE = "governance"
    CUSTOM = "custom"

class DocumentOverview(BaseModel):
    executive_summary: str
    main_topics: List[str] = []
    key_requirements: List[str] = []
    compliance_notes: List[str] = []
    document_type: str = "policy"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EnhancedAnalysis(BaseModel):
    """Enhanced analysis results (simplified)"""
    id: Optional[str] = Field(None, alias="_id")
    document_id: str
    analysis_timestamp: str
    total_chunks: int
    
    # Cross-chunk insights
    common_concepts: Dict[str, int] = {}
    concept_relationships: List[Dict[str, Any]] = []
    
    # Document insights
    document_summary: str
    document_type: str = "general"
    compliance_areas: List[str] = []
    key_requirements: List[Dict[str, str]] = []
    
    # Q&A pairs for future answering
    qa_pairs: List[Dict[str, Any]] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Document(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    title: str
    path: str
    jurisdiction: str
    policy_type: PolicyType
    version: str = "1.0"
    effective_date: datetime
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    checksum: str
    status: DocumentStatus = DocumentStatus.PENDING
    file_size: int
    file_type: str
    # Document overview for hybrid model
    overview: Optional[DocumentOverview] = None
    
    # State machine fields for batch processing
    total_chunks: int = 0
    processed_chunks: int = 0
    progress: int = 0
    lease: Optional[Dict[str, Any]] = None  # { owner: str, until: datetime }
    attempts: int = 0
    next_action_at: Optional[datetime] = None
    error: Optional[str] = None

class Chunk(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    doc_id: str
    page_from: int
    page_to: int
    section: Optional[str] = None
    text: str
    text_hash: str
    tokens: int
    # Summary fields for hybrid model
    summary: Optional[str] = None
    key_topics: List[str] = []
    important_details: List[str] = []
    
    # Enhanced analysis fields
    key_concepts: List[str] = []
    entities: List[Dict[str, str]] = []
    requirements: List[Dict[str, str]] = []
    importance_score: float = 0.5
    generated_questions: List[Dict[str, str]] = []
    chunk_id: Optional[str] = None
    analysis_timestamp: Optional[str] = None
    enhanced_analysis: bool = False
    analysed: bool = False  # For state machine tracking
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"

class Embedding(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    chunk_id: str
    model: str
    vector: List[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Question(BaseModel):
    qid: str
    text: str
    normalized: str
    tags: List[str] = []
    hash: str
    reference: str = ""  # Reference text for audit questions

class Questionnaire(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    filename: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    questions: List[Question] = []

class Citation(BaseModel):
    doc_id: str
    title: str
    page_from: int
    page_to: int
    chunk_id: str

class Answer(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    questionnaire_id: str
    qid: str
    question_text: str
    snapshot_id: str
    answer: str
    citations: List[Citation] = []
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Snapshot(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_model: str
    notes: Optional[str] = None

# CacheEntry removed - no longer using caching

class PolicyFolder(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    policy_type: PolicyType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    documents: List[str] = []  # Document IDs

class UploadedDocument(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    filename: str
    questionnaire_id: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    answers: List[str] = []  # Answer IDs

# Utility functions
def generate_checksum(content: bytes) -> str:
    """Generate SHA-256 checksum for content"""
    return hashlib.sha256(content).hexdigest()

def generate_text_hash(text: str) -> str:
    """Generate hash for text content"""
    return hashlib.md5(text.encode()).hexdigest()

def normalize_question(question: str) -> str:
    """Normalize question text for consistent processing"""
    return question.lower().strip()

def extract_tags_from_question(question: str) -> List[str]:
    """Extract relevant tags from question text"""
    tags = []
    question_lower = question.lower()
    
    # Jurisdiction tags
    jurisdictions = ["federal", "state", "local", "county", "city", "national", "international"]
    for jurisdiction in jurisdictions:
        if jurisdiction in question_lower:
            tags.append(jurisdiction)
    
    # Policy type tags
    policy_types = ["healthcare", "education", "environment", "economic", "social", "technology", "governance"]
    for policy_type in policy_types:
        if policy_type in question_lower:
            tags.append(policy_type)
    
    # Date tags
    import re
    date_patterns = [
        r'\b\d{4}\b',  # Years
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
        r'\b\d{1,2}/\d{1,2}/\d{4}\b'  # MM/DD/YYYY
    ]
    for pattern in date_patterns:
        if re.search(pattern, question_lower):
            tags.append("date_mentioned")
            break
    
    return tags
