"""
Single chunk creation mechanism for all document types
"""
import os
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import PyPDF2
import docx

logger = logging.getLogger(__name__)

async def create_single_chunk(file_path: str, doc_id: str, title: str, file_extension: str) -> Optional[Dict[str, Any]]:
    """
    Create a single chunk for any document type (PDF, DOCX, TXT)
    """
    try:
        logger.info(f"🔄 Creating single chunk for: {title}")
        
        # Extract text based on file type
        text = await extract_text_from_file(file_path, file_extension)
        if not text:
            logger.error(f"No text extracted from {file_extension} file")
            return None
        
        # Generate chunk ID
        chunk_id = f"chunk_{doc_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create single chunk with all content
        single_chunk = {
            "_id": chunk_id,
            "doc_id": doc_id,
            "page_from": 1,
            "page_to": 1,  # Single chunk covers entire document
            "text": text,
            "text_hash": hashlib.sha256(text.encode()).hexdigest(),
            "tokens": len(text.split()),  # Rough token count
            "summary": text[:200] + "..." if len(text) > 200 else text,
            "key_topics": [],
            "created_at": datetime.utcnow(),
            "chunk_type": "full_document",
            "file_type": file_extension.lower(),
            "analysed": False
        }
        
        logger.info(f"✅ Created single chunk: {len(text)} characters, {len(text.split())} tokens")
        return single_chunk
        
    except Exception as e:
        logger.error(f"Error creating single chunk: {e}")
        return None

async def extract_text_from_file(file_path: str, file_extension: str) -> str:
    """Extract text from various file types"""
    try:
        if file_extension.lower() == 'pdf':
            return await extract_text_from_pdf(file_path)
        elif file_extension.lower() == 'docx':
            return await extract_text_from_docx(file_path)
        elif file_extension.lower() == 'txt':
            return await extract_text_from_txt(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_extension}")
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from {file_extension}: {e}")
        return ""

async def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

async def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file_path)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        return ""

async def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        logger.error(f"Error extracting text from TXT: {e}")
        return ""
