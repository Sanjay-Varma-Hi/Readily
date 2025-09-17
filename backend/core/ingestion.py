import os
import hashlib
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiofiles
import PyPDF2
from io import BytesIO
import re

from .schema import Document, Chunk, DocumentStatus, PolicyType, DocumentOverview
# Removed old chunk_text import - using single chunk logic instead
# Embeddings functionality removed
# Summarization and enhanced analysis removed - not used by frontend

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, db):
        self.db = db
        
    async def process_document(self, doc_id: str, file_path: str, policy_type: str = "custom") -> Dict[str, Any]:
        """
        Process uploaded document through the full ingestion pipeline
        """
        try:
            logger.info(f"🔄 Starting document processing for {doc_id}")
            logger.info(f"📁 File path: {file_path}")
            logger.info(f"📋 Policy type: {policy_type}")
            
            # 1. Parse document and extract text
            pages = await self._parse_document(file_path)
            if not pages:
                raise ValueError("No text could be extracted from document")
            
            # 2. Calculate checksum
            checksum = await self._calculate_checksum(file_path)
            
            # 3. Check for existing document with same checksum (excluding current document)
            logger.info(f"🔍 Checking for duplicates with checksum: {checksum}")
            logger.info(f"🔍 Excluding document ID: {doc_id}")
            
            existing_doc = await self.db.documents.find_one({
                "checksum": checksum,
                "_id": {"$ne": doc_id}
            })
            
            logger.info(f"🔍 Duplicate check result: {existing_doc is not None}")
            if existing_doc:
                logger.info(f"📄 Document with same checksum already exists: {existing_doc['_id']}")
                return {"status": "duplicate", "doc_id": str(existing_doc["_id"])}
            
            # 4. Update document status to processing
            await self.db.documents.update_one(
                {"_id": doc_id},
                {"$set": {"status": DocumentStatus.PENDING, "checksum": checksum}}
            )
            
            # 5. Create chunks for batch processing
            chunks = await self._chunk_pages(pages, doc_id)
            logger.info(f"📝 Created {len(chunks)} chunks from document")
            
            # Debug: Log chunk details
            for i, chunk in enumerate(chunks[:3]):  # Log first 3 chunks
                logger.info(f"🔍 Chunk {i+1}: {chunk['text'][:100]}... (tokens: {chunk['tokens']})")
            
            # 6. Deduplicate chunks
            new_chunks = await self._deduplicate_chunks(chunks)
            logger.info(f"🔄 {len(new_chunks)} new chunks after deduplication")
            
            if not new_chunks:
                logger.info("📄 All chunks already exist, marking document as ready")
                await self.db.documents.update_one(
                    {"_id": doc_id},
                    {"$set": {"status": DocumentStatus.READY}}
                )
                return {"status": "ready", "chunks_added": 0}
            
            # 7. Save chunks to database (without analysis yet)
            await self._save_chunks_only(new_chunks)
            
            # 8. Update document with state machine fields
            await self.db.documents.update_one(
                {"_id": doc_id},
                {
                    "$set": {
                        "status": DocumentStatus.PENDING,
                        "total_chunks": len(new_chunks),
                        "processed_chunks": 0,
                        "progress": 0,
                        "attempts": 0,
                        "error": None
                    }
                }
            )
            
            logger.info(f"📄 Document ready for batch processing: {len(new_chunks)} chunks to analyze")
            
            # 12. Auto-trigger worker processing
            await self._trigger_worker_processing(doc_id)
            
            # 13. Create new snapshot
            snapshot_id = await self._create_snapshot()
            
            # 13. Mark document as ready
            await self.db.documents.update_one(
                {"_id": doc_id},
                {"$set": {"status": DocumentStatus.READY}}
            )
            
            logger.info(f"✅ Document processing completed for {doc_id}")
            return {
                "status": "ready",
                "chunks_added": len(new_chunks),
                "snapshot_id": snapshot_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing document {doc_id}: {e}")
            await self.db.documents.update_one(
                {"_id": doc_id},
                {"$set": {"status": DocumentStatus.ERROR}}
            )
            raise
    
    async def _parse_document(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse document and extract text per page"""
        try:
            pages = []
            file_extension = os.path.splitext(file_path)[1].lower()
            logger.info(f"🔍 Parsing document: {file_path} (extension: {file_extension})")
            
            if file_extension == '.pdf':
                # Parse PDF
                logger.info(f"📄 Processing PDF file: {file_path}")
                async with aiofiles.open(file_path, 'rb') as file:
                    content = await file.read()
                    
                try:
                    pdf_reader = PyPDF2.PdfReader(BytesIO(content))
                    logger.info(f"✅ PDF reader created successfully, {len(pdf_reader.pages)} pages found")
                except Exception as e:
                    logger.error(f"❌ Failed to create PDF reader: {e}")
                    # Try to detect if this is actually a text file with .pdf extension
                    try:
                        text_content = content.decode('utf-8')
                        logger.warning(f"⚠️ File appears to be text, not PDF. Content preview: {text_content[:100]}...")
                        pages.append({
                            "page_number": 1,
                            "text": text_content.strip(),
                            "char_count": len(text_content)
                        })
                        logger.info(f"📄 Parsed as text file: 1 page, {len(text_content)} characters")
                        return pages
                    except:
                        raise e
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            pages.append({
                                "page_number": page_num,
                                "text": text.strip(),
                                "char_count": len(text)
                            })
                    except Exception as e:
                        logger.warning(f"⚠️ Error extracting text from page {page_num}: {e}")
                        continue
                        
            elif file_extension == '.txt':
                # Parse text file
                logger.info(f"📄 Processing text file: {file_path}")
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                    content = await file.read()
                    
                if content.strip():
                    pages.append({
                        "page_number": 1,
                        "text": content.strip(),
                        "char_count": len(content)
                    })
                    logger.info(f"✅ Text file parsed: 1 page, {len(content)} characters")
                    
            elif file_extension == '.docx':
                # Parse DOCX file
                logger.info(f"📄 Processing DOCX file: {file_path}")
                from docx import Document as DocxDocument
                doc = DocxDocument(file_path)
                
                text_content = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_content.append(paragraph.text.strip())
                
                full_text = "\n".join(text_content)
                if full_text:
                    pages.append({
                        "page_number": 1,
                        "text": full_text,
                        "char_count": len(full_text)
                    })
                    logger.info(f"✅ DOCX file parsed: 1 page, {len(full_text)} characters")
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            logger.info(f"📄 Parsed {len(pages)} pages from {file_extension} document")
            
            if not pages:
                logger.warning(f"⚠️ No content extracted from {file_path}")
                # Create a dummy page to prevent complete failure
                pages.append({
                    "page_number": 1,
                    "text": "No content could be extracted from this document.",
                    "char_count": 0
                })
            
            return pages
            
        except Exception as e:
            logger.error(f"❌ Error parsing document {file_path}: {e}")
            raise
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _chunk_pages(self, pages: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        """Create a single chunk containing all pages of the document"""
        # Combine all pages into one single chunk
        full_text = ""
        page_from = 1
        page_to = len(pages)
        
        for page in pages:
            full_text += page["text"] + "\n"
        
        # Create single chunk with all content
        single_chunk = {
            "_id": f"chunk_{doc_id}_{int(datetime.utcnow().timestamp())}",
            "doc_id": doc_id,
            "page_from": page_from,
            "page_to": page_to,
            "text": full_text.strip(),
            "text_hash": hashlib.sha256(full_text.encode()).hexdigest(),
            "tokens": len(full_text.split()),  # Rough token count
            "summary": self._extract_summary(full_text.split('\n')),
            "key_topics": [],
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"✅ Created single chunk for document {doc_id} with {len(full_text)} characters")
        return [single_chunk]  # Return as list with single element
    
    def _extract_summary(self, lines: List[str]) -> str:
        """Extract a simple summary from text lines"""
        try:
            # Take first few non-empty lines as summary
            summary_lines = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Skip very short lines
                    summary_lines.append(line)
                    if len(summary_lines) >= 3:  # Take first 3 meaningful lines
                        break
            
            return " ".join(summary_lines)[:200] + "..." if len(" ".join(summary_lines)) > 200 else " ".join(summary_lines)
        except Exception as e:
            logger.error(f"Error extracting summary: {e}")
            return "Document summary not available"
    
    async def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks based on text hash"""
        new_chunks = []
        
        for chunk in chunks:
            # Check if chunk with same text hash already exists
            existing = await self.db.chunks.find_one({"text_hash": chunk["text_hash"]})
            if not existing:
                new_chunks.append(chunk)
            else:
                logger.debug(f"🔄 Skipping duplicate chunk: {chunk['text_hash'][:8]}...")
        
        return new_chunks
    
    # Embedding generation removed - no longer using vector search
    
    async def _save_chunks(self, chunks: List[Dict[str, Any]]):
        """Save chunks to database (embeddings removed)"""
        try:
            # Save chunks
            if chunks:
                chunk_docs = []
                for chunk in chunks:
                    chunk_doc = Chunk(
                        doc_id=chunk["doc_id"],
                        page_from=chunk["page_from"],
                        page_to=chunk["page_to"],
                        section=chunk.get("section"),
                        text=chunk["text"],
                        text_hash=chunk["text_hash"],
                        tokens=chunk["tokens"],
                        summary=chunk.get("summary"),
                        key_topics=chunk.get("key_topics", []),
                        important_details=chunk.get("important_details", []),
                        created_at=datetime.utcnow(),
                        version="1.0"
                    )
                    chunk_docs.append(chunk_doc.dict(by_alias=True, exclude={"id"}))
                
                await self.db.chunks.insert_many(chunk_docs)
                logger.info(f"💾 Saved {len(chunks)} chunks to database")
                
        except Exception as e:
            logger.error(f"❌ Error saving chunks: {e}")
            raise
    
    async def _create_snapshot(self) -> str:
        """Create a new snapshot record"""
        try:
            snapshot = {
                "created_at": datetime.utcnow(),
                "embedding_model": "text-embedding-3-small",
                "notes": "Document ingestion snapshot"
            }
            
            result = await self.db.snapshots.insert_one(snapshot)
            snapshot_id = str(result.inserted_id)
            logger.info(f"📸 Created snapshot: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"❌ Error creating snapshot: {e}")
            raise
    
    async def _get_document_title(self, doc_id: str) -> str:
        """Get document title for summarization context"""
        try:
            doc = await self.db.documents.find_one({"_id": doc_id})
            return doc.get("title", "Unknown Document") if doc else "Unknown Document"
        except Exception as e:
            logger.error(f"Error getting document title: {e}")
            return "Unknown Document"
    
    async def _save_document_overview(self, doc_id: str, overview: Dict[str, Any]):
        """Save document overview to database"""
        try:
            overview_doc = DocumentOverview(**overview)
            overview_data = overview_doc.dict(by_alias=True, exclude={"id"})
            
            await self.db.documents.update_one(
                {"_id": doc_id},
                {"$set": {"overview": overview_data}}
            )
            
            logger.info(f"💾 Saved document overview for {doc_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving document overview: {e}")
            raise
    
    def _convert_analysis_to_chunks(self, analysis_result: Dict[str, Any], doc_id: str) -> List[Dict[str, Any]]:
        """Convert enhanced analysis results to single chunk format for storage"""
        # Combine all analysis results into one single chunk
        all_text = ""
        all_summaries = []
        all_key_concepts = []
        all_entities = []
        all_requirements = []
        all_questions = []
        
        # Combine all chunk analyses into one
        for chunk_analysis in analysis_result.get("chunk_analyses", []):
            all_text += chunk_analysis.get("text", "") + "\n"
            if chunk_analysis.get("summary"):
                all_summaries.append(chunk_analysis.get("summary"))
            all_key_concepts.extend(chunk_analysis.get("key_concepts", []))
            all_entities.extend(chunk_analysis.get("entities", []))
            all_requirements.extend(chunk_analysis.get("requirements", []))
            all_questions.extend(chunk_analysis.get("generated_questions", []))
        
        # Create single chunk with all combined content
        single_chunk = {
            "doc_id": doc_id,
            "page_from": 1,
            "page_to": 1,
            "section": "full_document_analysis",
            "text": all_text.strip(),
            "text_hash": hashlib.sha256(all_text.encode()).hexdigest(),
            "tokens": len(all_text.split()),
            
            # Enhanced analysis data (combined)
            "summary": " | ".join(all_summaries) if all_summaries else "Document analysis completed",
            "key_concepts": list(set(all_key_concepts)),  # Remove duplicates
            "entities": list(set(all_entities)),  # Remove duplicates
            "requirements": list(set(all_requirements)),  # Remove duplicates
            "importance_score": 1.0,  # High importance for full document
            "generated_questions": list(set(all_questions)),  # Remove duplicates
            
            # Metadata
            "chunk_id": f"enhanced_analysis_{doc_id}_{int(datetime.utcnow().timestamp())}",
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "enhanced_analysis": True
        }
        
        logger.info(f"✅ Created single enhanced analysis chunk for document {doc_id}")
        return [single_chunk]  # Return as list with single element
    
    async def _save_enhanced_chunks(self, chunks: List[Dict[str, Any]], 
                                   analysis_result: Dict[str, Any]):
        """Save enhanced chunks and analysis results (embeddings removed)"""
        try:
            # Save chunks with enhanced data
            for chunk in chunks:
                chunk_doc = Chunk(
                    doc_id=chunk["doc_id"],
                    page_from=chunk["page_from"],
                    page_to=chunk["page_to"],
                    section=chunk.get("section"),
                    text=chunk["text"],
                    text_hash=chunk["text_hash"],
                    tokens=chunk["tokens"],
                    summary=chunk.get("summary"),
                    key_topics=chunk.get("key_concepts", []),
                    important_details=chunk.get("requirements", []),
                    created_at=datetime.utcnow(),
                    version="2.0"  # Enhanced version
                )
                
                await self.db.chunks.insert_one(chunk_doc.dict(by_alias=True, exclude={"id"}))
            
            # Save enhanced analysis results
            await self._save_enhanced_analysis_results(analysis_result)
            
            logger.info(f"💾 Saved {len(chunks)} enhanced chunks")
            
        except Exception as e:
            logger.error(f"Error saving enhanced chunks: {e}")
            raise
    
    async def _save_enhanced_analysis_results(self, analysis_result: Dict[str, Any]):
        """Save enhanced analysis results to a separate collection"""
        try:
            # Create analysis document
            analysis_doc = {
                "document_id": analysis_result.get("analysis_metadata", {}).get("document_title", ""),
                "analysis_timestamp": analysis_result.get("analysis_metadata", {}).get("analysis_timestamp"),
                "total_chunks": analysis_result.get("analysis_metadata", {}).get("total_chunks", 0),
                
                # Cross-chunk insights
                "common_concepts": analysis_result.get("cross_chunk_insights", {}).get("common_concepts", {}),
                "concept_relationships": analysis_result.get("cross_chunk_insights", {}).get("concept_relationships", []),
                
                # Document insights
                "document_summary": analysis_result.get("document_insights", {}).get("document_summary", ""),
                "document_type": analysis_result.get("document_insights", {}).get("document_type", "general"),
                "compliance_areas": analysis_result.get("document_insights", {}).get("compliance_areas", []),
                "key_requirements": analysis_result.get("document_insights", {}).get("key_requirements", []),
                
                # Q&A pairs for future answering
                "qa_pairs": analysis_result.get("qa_pairs", []),
                
                "created_at": datetime.utcnow()
            }
            
            # Save to enhanced_analysis collection
            await self.db.enhanced_analysis.insert_one(analysis_doc)
            logger.info("💾 Saved enhanced analysis results")
            
        except Exception as e:
            logger.error(f"Error saving enhanced analysis results: {e}")
            # Don't raise here as this is supplementary data
    
    async def _save_chunks_only(self, chunks: List[Dict[str, Any]]):
        """Save chunks to database without analysis (for state machine processing)"""
        try:
            for chunk in chunks:
                chunk_doc = Chunk(
                    doc_id=chunk["doc_id"],
                    page_from=chunk["page_from"],
                    page_to=chunk["page_to"],
                    section=chunk.get("section"),
                    text=chunk["text"],
                    text_hash=chunk["text_hash"],
                    tokens=chunk["tokens"],
                    created_at=datetime.utcnow(),
                    version="1.0",
                    analysed=False  # Will be set to True by worker
                )
                
                await self.db.chunks.insert_one(chunk_doc.dict(by_alias=True, exclude={"id"}))
            
            logger.info(f"💾 Saved {len(chunks)} chunks for batch processing")
            
        except Exception as e:
            logger.error(f"Error saving chunks: {e}")
            raise
    
    async def _trigger_worker_processing(self, doc_id: str):
        """Trigger immediate processing for the document (simplified)"""
        try:
            logger.info(f"🚀 Auto-triggering processing for document {doc_id}")
            
            # Simple processing without worker
            await self.process_document(doc_id, "", "custom")
            
            logger.info(f"✅ Auto-processing completed for document {doc_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in auto-trigger processing: {e}")
            # Don't raise - let the document stay in pending state

# Global processor instance
processor = None

def get_processor(db):
    global processor
    if processor is None:
        processor = DocumentProcessor(db)
    return processor