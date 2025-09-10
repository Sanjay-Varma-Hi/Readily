import os
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
import PyPDF2
from io import BytesIO
import aiofiles

logger = logging.getLogger(__name__)

class AuditQuestionExtractor:
    """Extract questions and references from audit PDFs"""
    
    def __init__(self):
        self.question_patterns = [
            # Pattern 1: Numbered questions with references in parentheses (same line)
            r'(\d+[\.\)]\s*[^?]+?\?)\s*\([Rr]eference:\s*([^)]+)\)',
            # Pattern 2: Numbered questions with references on next line
            r'(\d+[\.\)]\s*[^?]+?\?)\s*\n\s*\([Rr]eference:\s*([^)]+)\)',
            # Pattern 3: Questions with references separated by dash or colon
            r'(\d+[\.\)]\s*[^?]+?\?)\s*[-:]\s*\([Rr]eference:\s*([^)]+)\)',
            # Pattern 4: Questions with references in brackets
            r'(\d+[\.\)]\s*[^?]+?\?)\s*\[[Rr]eference:\s*([^\]]+)\]',
            # Pattern 5: Questions with references at the end (multiline)
            r'(\d+[\.\)]\s*[^?]+?\?)\s*[^?]*?\([Rr]eference:\s*([^)]+)\)',
            # Pattern 6: Questions with references without parentheses
            r'(\d+[\.\)]\s*[^?]+?\?)\s*\n\s*[Rr]eference:\s*([^\n]+)',
        ]
        
        # Fallback patterns for questions without clear references
        self.fallback_patterns = [
            r'(\d+[\.\)]\s*[^?]+?\?)',
            r'(Q\d+[\.\)]\s*[^?]+?\?)',
            r'(\d+\.\s*[^?]+?\?)',
        ]
    
    async def extract_questions_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract questions and references from audit PDF"""
        try:
            logger.info(f"🔍 Extracting questions from audit PDF: {file_path}")
            
            # Extract text from PDF
            text = await self._extract_text_from_pdf(file_path)
            if not text:
                logger.error("No text extracted from PDF")
                return []
            
            # Extract questions with references
            questions = self._extract_questions_with_references(text)
            
            logger.info(f"✅ Extracted {len(questions)} questions from audit PDF")
            return questions
            
        except Exception as e:
            logger.error(f"Error extracting questions from PDF {file_path}: {e}")
            return []
    
    async def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            async with aiofiles.open(file_path, 'rb') as file:
                content = await file.read()
                
                pdf_reader = PyPDF2.PdfReader(BytesIO(content))
                text = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text.strip():
                        text += f"\n--- PAGE {page_num + 1} ---\n"
                        text += page_text.strip() + "\n"
                
                # Clean up the text to fix spacing issues
                text = self._clean_pdf_text(text)
                return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def _clean_pdf_text(self, text: str) -> str:
        """Clean up PDF text to fix common formatting issues"""
        # Fix common PDF extraction issues
        text = re.sub(r'(\d+)\s+\.', r'\1.', text)  # Fix "1 ." -> "1."
        
        # Fix specific spacing issues in words
        text = re.sub(r'u\s+nder', 'under', text)
        text = re.sub(r'P\s+&P', 'P&P', text)
        text = re.sub(r'APL\s+25', 'APL 25', text)
        
        # Fix reference formatting
        text = re.sub(r'\(Reference:\s*([^)]+)\)', r'(Reference: \1)', text)
        
        # Fix multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _extract_questions_with_references(self, text: str) -> List[Dict[str, Any]]:
        """Extract questions and their references from text"""
        questions = []
        question_id = 1
        
        # First, try to find the "Review Findings" section
        review_findings_match = re.search(r'Review Findings:.*?(?=\n\n|\n[A-Z]|$)', text, re.IGNORECASE | re.DOTALL)
        if review_findings_match:
            review_section = review_findings_match.group(0)
            logger.info("Found Review Findings section, processing questions from it")
            text_to_process = review_section
        else:
            logger.info("No Review Findings section found, processing entire text")
            text_to_process = text
        
        # Use regex to find all questions in the text (not just line by line)
        # Look for patterns like "17. Does the P&P state..." followed by reference
        # Make the pattern more flexible to handle various spacing and formatting
        # Use a more permissive pattern that can handle very long questions
        question_pattern = r'(\d+\.\s*[^?]+?\?)\s*\([Rr]eference:\s*([^)]+)\)'
        matches = list(re.finditer(question_pattern, text_to_process, re.IGNORECASE | re.DOTALL))
        
        # Also try a more permissive pattern for very long questions
        long_question_pattern = r'(\d+\.\s*[^?]+?\?)\s*\([Rr]eference:\s*([^)]+)\)'
        long_matches = list(re.finditer(long_question_pattern, text_to_process, re.IGNORECASE | re.DOTALL | re.MULTILINE))
        
        # Combine and deduplicate
        all_matches = matches + long_matches
        unique_matches = []
        seen_questions = set()
        
        for match in all_matches:
            question_text = match.group(1).strip()
            if question_text not in seen_questions:
                unique_matches.append(match)
                seen_questions.add(question_text)
        
        matches = unique_matches
        
        
        # Process strict matches first
        for match in matches:
            question_text = match.group(1).strip()
            reference_text = match.group(2).strip()
            
            # Clean up the texts
            question_text = self._clean_question_text(question_text)
            reference_text = self._clean_reference_text(reference_text)
            
            if self._is_valid_question(question_text):
                questions.append({
                    "question_id": question_id,
                    "requirement": question_text,
                    "reference": reference_text
                })
                question_id += 1
        
        # If we didn't find enough with the strict pattern, try a more flexible approach
        if len(questions) < 60:
            logger.info("Trying more flexible question pattern")
            # Try a pattern that looks for questions anywhere, not just with immediate references
            # Use a more permissive pattern that can handle very long questions
            # Use a more robust pattern that can handle very long questions
            flexible_pattern = r'(\d+\.\s*[^?]+?\?)'
            flexible_matches = re.finditer(flexible_pattern, text_to_process, re.IGNORECASE | re.DOTALL)
            
            # Also try a pattern that's more specific for very long questions
            long_flexible_pattern = r'(\d+\.\s*[^?]+?\?)'
            long_flexible_matches = re.finditer(long_flexible_pattern, text_to_process, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            
            # Combine both patterns
            all_flexible_matches = list(flexible_matches) + list(long_flexible_matches)
            seen_flexible = set()
            unique_flexible_matches = []
            
            for match in all_flexible_matches:
                question_text = match.group(1).strip()
                if question_text not in seen_flexible:
                    unique_flexible_matches.append(match)
                    seen_flexible.add(question_text)
            
            flexible_matches = unique_flexible_matches
            
            # Process flexible matches and try to find references nearby
            for match in flexible_matches:
                question_text = match.group(1).strip()
                reference_text = ""
                
                # Look for reference in the next 500 characters (increased from 300)
                start_pos = match.end()
                next_text = text_to_process[start_pos:start_pos + 500]
                
                ref_match = re.search(r'\([Rr]eference:\s*([^)]+)\)', next_text)
                if ref_match:
                    reference_text = ref_match.group(1).strip()
                
                # Clean up the texts
                question_text = self._clean_question_text(question_text)
                reference_text = self._clean_reference_text(reference_text)
                
                if self._is_valid_question(question_text):
                    # Check if we already have this question
                    if not any(q['requirement'] == question_text for q in questions):
                        questions.append({
                            "question_id": question_id,
                            "requirement": question_text,
                            "reference": reference_text
                        })
                        question_id += 1
        
        # Special handling for very long questions that might be missed
        long_questions = [15, 56]  # Add more if needed
        
        for q_num in long_questions:
            if not any(q['requirement'].startswith(f'{q_num}.') for q in questions):
                logger.info(f"Question {q_num} not found, trying special extraction")
                # Look for the question specifically
                question_pattern = rf'{q_num}\.\s*[^?]+?\?'
                match = re.search(question_pattern, text_to_process, re.IGNORECASE | re.DOTALL)
                if match:
                    question_text = match.group(0).strip()
                    reference_text = ""
                    
                    # Look for reference after the question
                    start_pos = match.end()
                    next_text = text_to_process[start_pos:start_pos + 200]
                    ref_match = re.search(r'\([Rr]eference:\s*([^)]+)\)', next_text)
                    if ref_match:
                        reference_text = ref_match.group(1).strip()
                    
                    # Clean up the texts
                    question_text = self._clean_question_text(question_text)
                    reference_text = self._clean_reference_text(reference_text)
                    
                    if self._is_valid_question(question_text):
                        questions.append({
                            "question_id": question_id,
                            "requirement": question_text,
                            "reference": reference_text
                        })
                        question_id += 1
                        logger.info(f"Successfully extracted question {q_num}")
        
        # If we didn't find enough questions with the regex approach, try line-by-line
        if len(questions) < 10:
            logger.info("Not enough questions found with regex, trying line-by-line approach")
            lines = text_to_process.split('\n')
            
            # Process each line looking for questions
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                
                # Skip lines that are clearly not questions
                if self._should_skip_line(line):
                    i += 1
                    continue
                    
                # Look for numbered questions with more specific pattern
                # Pattern: number followed by period, then question text (may or may not end with question mark)
                question_match = re.match(r'^(\d+\.\s*.*)', line)
                if question_match:
                    question_text = question_match.group(1).strip()
                    reference_text = ""
                    
                    # Check if the question continues on the next lines
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if not next_line:
                            j += 1
                            continue
                        
                        # If we find a reference, stop collecting question text
                        if re.match(r'\([Rr]eference:\s*([^)]+)\)', next_line):
                            ref_match = re.match(r'\([Rr]eference:\s*([^)]+)\)', next_line)
                            reference_text = ref_match.group(1).strip()
                            break
                        elif re.match(r'[Rr]eference:\s*([^\n]+)', next_line):
                            ref_match = re.match(r'[Rr]eference:\s*([^\n]+)', next_line)
                            reference_text = ref_match.group(1).strip()
                            break
                        # If we find another numbered question, stop
                        elif re.match(r'^\d+\.\s*', next_line):
                            break
                        # If we find checkboxes or form elements, stop
                        elif any(char in next_line for char in ['☐', '☑', '□', '■', '○', '●']) or next_line.lower() in ['yes', 'no']:
                            break
                        # Otherwise, continue building the question text
                        else:
                            question_text += " " + next_line
                            j += 1
                    
                    # Ensure the question ends with a question mark
                    if not question_text.endswith('?'):
                        question_text += '?'
                    
                    # Clean up the texts
                    question_text = self._clean_question_text(question_text)
                    reference_text = self._clean_reference_text(reference_text)
                    
                    if self._is_valid_question(question_text):
                        questions.append({
                            "question_id": question_id,
                            "requirement": question_text,
                            "reference": reference_text
                        })
                        question_id += 1
                    
                    # Skip to the next question
                    i = j
                else:
                    i += 1
        
        # If no questions found with the line-by-line approach, try regex patterns
        if not questions:
            logger.info("No questions found with line-by-line approach, trying regex patterns")
            for pattern in self.question_patterns:
                matches = re.finditer(pattern, text_to_process, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for match in matches:
                    question_text = match.group(1).strip()
                    reference_text = match.group(2).strip()
                    
                    # Clean up the question text
                    question_text = self._clean_question_text(question_text)
                    reference_text = self._clean_reference_text(reference_text)
                    
                    if self._is_valid_question(question_text):
                        questions.append({
                            "question_id": question_id,
                            "requirement": question_text,
                            "reference": reference_text
                        })
                        question_id += 1
        
        # If still no questions found, try fallback patterns
        if not questions:
            logger.info("No questions with references found, trying fallback patterns")
            for pattern in self.fallback_patterns:
                matches = re.finditer(pattern, text_to_process, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for match in matches:
                    question_text = match.group(1).strip()
                    question_text = self._clean_question_text(question_text)
                    
                    if self._is_valid_question(question_text):
                        questions.append({
                            "question_id": question_id,
                            "requirement": question_text,
                            "reference": ""
                        })
                        question_id += 1
        
        # Remove duplicates and sort by position in text
        questions = self._deduplicate_questions(questions)
        questions = self._sort_questions_by_position(questions, text_to_process)
        
        # Renumber questions sequentially
        for i, question in enumerate(questions, 1):
            question["question_id"] = i
        
        return questions
    
    def _clean_question_text(self, text: str) -> str:
        """Clean and normalize question text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common prefixes but keep the question number
        # text = re.sub(r'^\d+[\.\)]\s*', '', text)
        # text = re.sub(r'^Q\d+[\.\)]\s*', '', text)
        
        # Remove trailing punctuation that's not a question mark
        text = re.sub(r'[.,;:]+$', '', text)
        
        # Ensure it ends with a question mark
        if not text.endswith('?'):
            text += '?'
        
        return text.strip()
    
    def _clean_reference_text(self, text: str) -> str:
        """Clean and normalize reference text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common prefixes
        text = re.sub(r'^[Rr]eference:\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^[Rr]ef:\s*', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _should_skip_line(self, line: str) -> bool:
        """Check if a line should be skipped during processing"""
        line_lower = line.lower().strip()
        
        # Skip empty lines
        if not line_lower:
            return True
        
        # Skip headers and form elements
        skip_patterns = [
            'review findings:',
            'submission review form',
            'dhcs mcod',
            'reviewer:',
            'unit:',
            'return to:',
            'date received',
            'dhcs review due',
            'plan name:',
            'county(s):',
            'submission item:',
            'approved as submitted',
            'additional information requested',
            'denied',
            'review criteria',
            'your submission will be reviewed',
            'note:',
            'citations:',
        'policies and procedures',
        'managed care plans',
            'yes',
            'no',
            'citation:',
            'rev.',
            'page',
            'signature',
            'unit chief',
            'reviewer',
            'date:',
            '☐',
            '☑',
            '□',
            '■',
            '○',
            '●'
        ]
        
        for pattern in skip_patterns:
            if pattern in line_lower:
                return True
        
        # Skip lines that are just numbers or single characters
        if re.match(r'^[\d\s\.\-_]+$', line_lower):
            return True
        
        # Skip lines that are just punctuation
        if re.match(r'^[^\w\s]+$', line_lower):
            return True
        
        return False
    
    def _is_valid_question(self, text: str) -> bool:
        """Check if text is a valid question"""
        if not text or len(text) < 10:
            return False
        
        # Must contain a question mark
        if '?' not in text:
            return False
        
        # Must not be too short or too long
        if len(text) < 15 or len(text) > 1000:
            return False
        
        # Must not be a header or footer
        if text.lower().startswith(('page', 'section', 'chapter', 'appendix')):
            return False
        
        # Must not be a signature or approval text
        if any(word in text.lower() for word in ['signature', 'approved', 'reviewed', 'date:', 'signature:']):
            return False
        
        # Must not be a checkbox or form element
        if any(char in text for char in ['☐', '☑', '□', '■', '○', '●']):
            return False
        
        # Must start with a number followed by a period
        if not re.match(r'^\d+\.', text.strip()):
            return False
        
        return True
    
    def _deduplicate_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate questions based on text similarity"""
        unique_questions = []
        seen_texts = set()
        
        for question in questions:
            # Normalize text for comparison
            normalized_text = re.sub(r'\s+', ' ', question["requirement"].lower().strip())
            
            if normalized_text not in seen_texts:
                unique_questions.append(question)
                seen_texts.add(normalized_text)
        
        return unique_questions
    
    def _sort_questions_by_position(self, questions: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """Sort questions by their position in the original text"""
        def get_position(question):
            return text.find(question["requirement"])
        
        return sorted(questions, key=get_position)
    
    def extract_questions_to_json(self, file_path: str) -> str:
        """Extract questions and return as JSON string"""
        import json
        
        questions = self.extract_questions_from_pdf(file_path)
        return json.dumps(questions, indent=2)

# Convenience function for backward compatibility
async def extract_audit_questions_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """Extract questions and references from audit PDF"""
    extractor = AuditQuestionExtractor()
    return await extractor.extract_questions_from_pdf(file_path)
