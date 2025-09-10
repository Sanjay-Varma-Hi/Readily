import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)

class PDFChunker:
    """Converts PDF documents into structured JSON chunks"""
    
    def __init__(self):
        self.chunk_counter = 0
    
    def chunk_pdf_to_json(self, file_path: str, doc_id: str, title: str) -> List[Dict[str, Any]]:
        """
        Convert PDF to structured JSON chunks
        """
        try:
            logger.info(f"🔄 Starting PDF chunking for: {title}")
            
            # Extract text from PDF
            text = self._extract_text_from_pdf(file_path)
            if not text:
                logger.error("No text extracted from PDF")
                return []
            
            # Parse the document into structured chunks
            chunks = self._parse_document_to_chunks(text, doc_id, title)
            
            logger.info(f"✅ Created {len(chunks)} chunks from PDF: {title}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking PDF {file_path}: {e}")
            return []
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
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
    
    def _parse_document_to_chunks(self, text: str, doc_id: str, title: str) -> List[Dict[str, Any]]:
        """Parse document text into a single chunk (one chunk per document)"""
        # Create only ONE chunk per document - ignore all section splitting
        single_chunk = self._create_single_document_chunk(text, doc_id, title)
        return [single_chunk]  # Return as list with single element
    
    def _create_single_document_chunk(self, text: str, doc_id: str, title: str) -> Dict[str, Any]:
        """Create a single chunk containing the entire document text"""
        try:
            # Generate single chunk ID
            self.chunk_counter += 1
            chunk_id = f"doc-{self.chunk_counter}"
            
            # Create single chunk with entire document content
            chunk = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "title": title,
                "content": text.strip(),
                "content_length": len(text.strip()),
                "chunk_type": "full_document",
                "created_at": datetime.now().isoformat(),
                "summary": self._extract_summary(text.split('\n')),
                "department": "CalOptima Health Administrative",
                "applicable_to": ["Administrative"],
                "effective_date": datetime.now().strftime("%Y-%m-%d"),
                "revised_date": datetime.now().strftime("%Y-%m-%d"),
                "ceo_approval": {
                    "name": "To be determined",
                    "approval_date": datetime.now().strftime("%Y-%m-%d")
                },
                "notes": f"Complete policy document: {title}"
            }
            
            logger.info(f"✅ Created single chunk for document: {title} (length: {len(text.strip())} chars)")
            return chunk
            
        except Exception as e:
            logger.error(f"Error creating single document chunk: {e}")
            # Fallback: create basic chunk
            return {
                "chunk_id": f"doc-{self.chunk_counter}",
                "doc_id": doc_id,
                "title": title,
                "content": text.strip(),
                "content_length": len(text.strip()),
                "chunk_type": "full_document",
                "created_at": datetime.now().isoformat()
            }
    
    def _create_metadata_chunk(self, doc_id: str, title: str) -> Dict[str, Any]:
        """Create metadata chunk from document info"""
        return {
            "chunk_id": "meta-0",
            "policy_id": doc_id,
            "title": title,
            "department": "CalOptima Health Administrative",  # Default, can be extracted from PDF
            "applicable_to": ["Administrative"],  # Default, can be extracted from PDF
            "effective_date": datetime.now().strftime("%Y-%m-%d"),
            "revised_date": datetime.now().strftime("%Y-%m-%d"),
            "ceo_approval": {
                "name": "To be determined",
                "approval_date": datetime.now().strftime("%Y-%m-%d")
            },
            "notes": f"Policy document: {title}",
            "created_at": datetime.now().isoformat(),
            "doc_id": doc_id
        }
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into sections based on common patterns"""
        # Common section patterns
        section_patterns = [
            r'^I+\.\s+[A-Z\s]+',  # Roman numerals (I., II., III., etc.)
            r'^\d+\.\s+[A-Z\s]+',  # Numbers (1., 2., 3., etc.)
            r'^[A-Z]\.\s+[A-Z\s]+',  # Letters (A., B., C., etc.)
            r'^[A-Z][A-Z\s]+:',  # All caps with colon
            r'^[A-Z][a-z\s]+:',  # Title case with colon
        ]
        
        # Split by sections
        sections = []
        current_section = ""
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new section
            is_section_header = False
            for pattern in section_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_section_header = True
                    break
            
            if is_section_header and current_section:
                sections.append(current_section.strip())
                current_section = line + "\n"
            else:
                current_section += line + "\n"
        
        # Add the last section
        if current_section.strip():
            sections.append(current_section.strip())
        
        return sections
    
    def _create_section_chunk(self, section_text: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Create a structured chunk from section text"""
        try:
            lines = [line.strip() for line in section_text.split('\n') if line.strip()]
            if not lines:
                return None
            
            # Extract section title (first line)
            section_title = lines[0]
            
            # Generate chunk ID
            self.chunk_counter += 1
            chunk_id = f"section-{self.chunk_counter}"
            
            # Create base chunk
            chunk = {
                "chunk_id": chunk_id,
                "section": section_title,
                "doc_id": doc_id,
                "created_at": datetime.now().isoformat()
            }
            
            # Parse content based on section type
            content_lines = lines[1:] if len(lines) > 1 else []
            
            if self._is_purpose_section(section_title):
                chunk["summary"] = self._extract_summary(content_lines)
            elif self._is_policy_section(section_title):
                chunk.update(self._extract_policy_content(content_lines))
            elif self._is_procedure_section(section_title):
                chunk["requirements"] = self._extract_requirements(content_lines)
            elif self._is_reference_section(section_title):
                chunk["references"] = self._extract_references(content_lines)
            elif self._is_glossary_section(section_title):
                chunk["terms"] = self._extract_glossary_terms(content_lines)
            else:
                # Generic section
                chunk["content"] = "\n".join(content_lines)
                chunk["summary"] = self._extract_summary(content_lines)
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error creating section chunk: {e}")
            return None
    
    def _is_purpose_section(self, title: str) -> bool:
        """Check if section is a purpose section"""
        purpose_keywords = ['purpose', 'objective', 'goal', 'aim']
        return any(keyword in title.lower() for keyword in purpose_keywords)
    
    def _is_policy_section(self, title: str) -> bool:
        """Check if section is a policy section"""
        policy_keywords = ['policy', 'rule', 'regulation', 'prohibition', 'requirement']
        return any(keyword in title.lower() for keyword in policy_keywords)
    
    def _is_procedure_section(self, title: str) -> bool:
        """Check if section is a procedure section"""
        procedure_keywords = ['procedure', 'process', 'step', 'requirement', 'guideline']
        return any(keyword in title.lower() for keyword in procedure_keywords)
    
    def _is_reference_section(self, title: str) -> bool:
        """Check if section is a reference section"""
        reference_keywords = ['reference', 'citation', 'source', 'bibliography']
        return any(keyword in title.lower() for keyword in reference_keywords)
    
    def _is_glossary_section(self, title: str) -> bool:
        """Check if section is a glossary section"""
        glossary_keywords = ['glossary', 'definition', 'term', 'acronym']
        return any(keyword in title.lower() for keyword in glossary_keywords)
    
    def _extract_summary(self, lines: List[str]) -> str:
        """Extract summary from content lines"""
        if not lines:
            return ""
        
        # Take first meaningful sentence as summary
        text = " ".join(lines)
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Meaningful sentence
                return sentence
        
        return text[:200] + "..." if len(text) > 200 else text
    
    def _extract_policy_content(self, lines: List[str]) -> Dict[str, Any]:
        """Extract policy-specific content"""
        content = {}
        
        # Look for rules, exceptions, examples
        current_list = []
        current_key = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for bullet points or numbered items
            if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+\.\s+', line):
                if current_key:
                    current_list.append(line)
                else:
                    current_key = "rules"
                    current_list = [line]
            elif line.endswith(':'):
                # Save previous list
                if current_key and current_list:
                    content[current_key] = current_list
                
                # Start new section
                current_key = line.lower().replace(':', '').replace(' ', '_')
                current_list = []
            else:
                # Regular text
                if current_key and current_list:
                    current_list.append(line)
                else:
                    content["content"] = content.get("content", "") + line + " "
        
        # Save last list
        if current_key and current_list:
            content[current_key] = current_list
        
        return content
    
    def _extract_requirements(self, lines: List[str]) -> List[str]:
        """Extract requirements from procedure section"""
        requirements = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for requirement patterns
            if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+\.\s+', line):
                requirements.append(line)
            elif 'must' in line.lower() or 'shall' in line.lower() or 'required' in line.lower():
                requirements.append(line)
        
        return requirements
    
    def _extract_references(self, lines: List[str]) -> List[str]:
        """Extract references from reference section"""
        references = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for reference patterns
            if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+\.\s+', line):
                references.append(line)
            elif any(keyword in line.lower() for keyword in ['code', 'regulation', 'statute', 'policy']):
                references.append(line)
        
        return references
    
    def _extract_glossary_terms(self, lines: List[str]) -> Dict[str, str]:
        """Extract glossary terms and definitions"""
        terms = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for term: definition pattern
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    term = parts[0].strip()
                    definition = parts[1].strip()
                    terms[term] = definition
        
        return terms

# Global chunker instance
chunker = None

def get_pdf_chunker():
    """Get PDF chunker instance"""
    global chunker
    if chunker is None:
        chunker = PDFChunker()
    return chunker
