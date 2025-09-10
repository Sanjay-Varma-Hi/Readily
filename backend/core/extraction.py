import os
import logging
from typing import List
import PyPDF2
from docx import Document as DocxDocument
import aiofiles
import re
import io

logger = logging.getLogger(__name__)

async def extract_text_from_file(file_path: str) -> List[str]:
    """Extract text from various file formats"""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return await extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            return await extract_text_from_docx(file_path)
        elif file_extension == '.txt':
            return await extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return []

async def extract_text_from_pdf(file_path: str) -> List[str]:
    """Extract text from PDF file, returning list of pages"""
    try:
        pages = []
        
        async with aiofiles.open(file_path, 'rb') as file:
            content = await file.read()
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                if text.strip():
                    pages.append(text.strip())
                else:
                    pages.append("")  # Empty page placeholder
        
        return pages

    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {e}")
        return []

async def extract_text_from_docx(file_path: str) -> List[str]:
    """Extract text from DOCX file"""
    try:
        doc = DocxDocument(file_path)
        pages = []
        
        # DOCX doesn't have clear page breaks, so we'll treat it as one page
        # or split by paragraph breaks
        text_content = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text.strip())
        
        # Join all text and split into pages (rough approximation)
        full_text = "\n".join(text_content)
        if full_text:
            pages = [full_text]  # Treat as single page for now
        
        return pages

    except Exception as e:
        logger.error(f"Error extracting text from DOCX {file_path}: {e}")
        return []

async def extract_text_from_txt(file_path: str) -> List[str]:
    """Extract text from TXT file"""
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            content = await file.read()
            
        if content.strip():
            return [content.strip()]
        else:
            return []

    except Exception as e:
        logger.error(f"Error extracting text from TXT {file_path}: {e}")
        return []

async def extract_questions_from_pdf(file_path: str) -> List[str]:
    """Extract questions from a questionnaire PDF"""
    try:
        pages = await extract_text_from_pdf(file_path)
        all_text = "\n".join(pages)
        
        # Extract questions using various patterns
        questions = []
        
        # Pattern 1: Numbered questions (Q1, Q2, etc.)
        q_pattern1 = r'Q\d+[\.\)]\s*([^\n]+(?:\n(?!Q\d+)[^\n]*)*)'
        matches1 = re.findall(q_pattern1, all_text, re.IGNORECASE | re.MULTILINE)
        questions.extend([match.strip() for match in matches1])
        
        # Pattern 2: Numbered questions (1., 2., etc.)
        q_pattern2 = r'^\d+[\.\)]\s*([^\n]+(?:\n(?!^\d+)[^\n]*)*)'
        matches2 = re.findall(q_pattern2, all_text, re.MULTILINE)
        questions.extend([match.strip() for match in matches2])
        
        # Pattern 3: Questions ending with question marks
        q_pattern3 = r'([^.!?]*\?)'
        matches3 = re.findall(q_pattern3, all_text)
        questions.extend([match.strip() for match in matches3 if len(match.strip()) > 10])
        
        # Clean and deduplicate questions
        cleaned_questions = []
        seen = set()
        
        for question in questions:
            question = question.strip()
            if (len(question) > 10 and 
                question not in seen and 
                not question.startswith(('http', 'www', 'email'))):
                cleaned_questions.append(question)
                seen.add(question)
        
        # Sort by position in original text
        def get_position(q):
            return all_text.find(q)
        
        cleaned_questions.sort(key=get_position)
        
        return cleaned_questions

    except Exception as e:
        logger.error(f"Error extracting questions from PDF {file_path}: {e}")
        return []
