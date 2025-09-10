import os
import logging
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    try:
        # Remove or replace unsafe characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        return filename
    except Exception as e:
        logger.error(f"Error sanitizing filename {filename}: {e}")
        return "sanitized_file"

def validate_file_type(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate file type based on extension"""
    try:
        if not filename:
            return False
        
        extension = os.path.splitext(filename)[1].lower()
        return extension in [ext.lower() for ext in allowed_extensions]
    except Exception as e:
        logger.error(f"Error validating file type {filename}: {e}")
        return False

def calculate_file_hash(file_path: str) -> Optional[str]:
    """Calculate SHA-256 hash of file"""
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash for {file_path}: {e}")
        return None

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    try:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    except Exception as e:
        logger.error(f"Error formatting file size: {e}")
        return "Unknown"

def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """Extract metadata from text content"""
    try:
        metadata = {
            "word_count": len(text.split()),
            "char_count": len(text),
            "line_count": len(text.split('\n')),
            "has_numbers": bool(re.search(r'\d', text)),
            "has_dates": bool(re.search(r'\b(19|20)\d{2}\b', text)),
            "has_emails": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            "has_urls": bool(re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text))
        }
        
        # Extract potential dates
        date_patterns = [
            r'\b(19|20)\d{2}\b',  # Years
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{4}\b',  # MM-DD-YYYY
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'  # Month DD, YYYY
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        metadata["extracted_dates"] = list(set(dates))
        
        return metadata

    except Exception as e:
        logger.error(f"Error extracting metadata from text: {e}")
        return {}

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    try:
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-]', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n+', '\n', text)
        
        return text.strip()

    except Exception as e:
        logger.error(f"Error cleaning text: {e}")
        return text

def chunk_text_by_sentences(text: str, max_chunk_size: int = 1000) -> List[str]:
    """Split text into chunks by sentences"""
    try:
        if not text:
            return []
        
        # Split by sentence endings
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # If adding this sentence would exceed max size, start new chunk
            if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    except Exception as e:
        logger.error(f"Error chunking text by sentences: {e}")
        return [text]

def validate_question_format(question: str) -> bool:
    """Validate if text looks like a question"""
    try:
        if not question or len(question.strip()) < 10:
            return False
        
        question = question.strip()
        
        # Check for question words
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'which', 'can', 'could', 'should', 'would', 'is', 'are', 'was', 'were']
        
        # Check for question mark
        if question.endswith('?'):
            return True
        
        # Check if starts with question word
        first_word = question.split()[0].lower() if question.split() else ""
        if first_word in question_words:
            return True
        
        # Check for question patterns
        question_patterns = [
            r'^[A-Z][^.!?]*\?$',  # Starts with capital, ends with ?
            r'^(What|How|When|Where|Why|Who|Which|Can|Could|Should|Would|Is|Are|Was|Were)\s+',  # Starts with question word
            r'.*\?$'  # Ends with question mark
        ]
        
        for pattern in question_patterns:
            if re.match(pattern, question, re.IGNORECASE):
                return True
        
        return False

    except Exception as e:
        logger.error(f"Error validating question format: {e}")
        return False

def retry_async(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator

def create_directory_if_not_exists(directory: str) -> bool:
    """Create directory if it doesn't exist"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False

def get_environment_config() -> Dict[str, Any]:
    """Get environment configuration"""
    try:
        return {
            "mongodb_uri": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            "db_name": os.getenv("DB_NAME", "policiesdb"),
            "chunk_tokens": int(os.getenv("CHUNK_TOKENS", "800")),
            "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "120")),
            "max_parallel_questions": int(os.getenv("MAX_PARALLEL_QUESTIONS", "6")),
            "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "50")),
            "allowed_extensions": os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt").split(","),
            "debug": os.getenv("DEBUG", "False").lower() == "true"
        }
    except Exception as e:
        logger.error(f"Error getting environment config: {e}")
        return {}

