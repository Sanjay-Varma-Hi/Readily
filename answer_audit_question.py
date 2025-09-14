#!/usr/bin/env python3
"""
Question Answering System for Specific Audit Question
Fetches question from audit_questions collection and answers it
"""

import os
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv("env/example.env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditQuestionAnsweringSystem:
    def __init__(self):
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.db_name = os.getenv("DB_NAME", "policiesdb")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.client = None
        self.db = None
        
    async def connect_to_mongodb(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongodb_uri)
            self.db = self.client[self.db_name]
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    async def fetch_audit_question(self, question_id: str) -> Dict[str, Any]:
        """Fetch specific audit question by ID"""
        try:
            question = await self.db.audit_questions.find_one({"question_id": question_id})
            if question:
                logger.info(f"✅ Found audit question: {question_id}")
                return question
            else:
                logger.warning(f"⚠️ No audit question found with ID: {question_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Error fetching audit question: {e}")
            return None
    
    async def check_existing_answer(self, question_id: str) -> Dict[str, Any]:
        """Check if answer already exists in the database"""
        try:
            existing_answer = await self.db.answers.find_one({"question_id": question_id})
            if existing_answer:
                logger.info(f"✅ Found existing answer for question ID: {question_id}")
                return existing_answer
            else:
                logger.info(f"📝 No existing answer found for question ID: {question_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Error checking existing answer: {e}")
            return None
    
    async def search_relevant_chunks(self, question: str, limit: int = 375) -> List[Dict[str, Any]]:
        """Search for chunks relevant to the question"""
        try:
            # Extract key terms from the question for better search
            key_terms = [
                "hospice", "enrollment", "MCP", "member", "elect", "receive", 
                "care services", "remain enrolled", "qualify", "managed care",
                "hospice care", "terminal", "palliative", "end of life",
                "benefit periods", "90-day", "60-day", "election", "coverage",
                "APL 25-008", "contract requirements", "state law", "provide",
                "hospice services", "member election", "start", "receive"
            ]
            
            # Create search query for the correct field structure
            search_query = {
                "$or": [
                    {"text": {"$regex": term, "$options": "i"}} for term in key_terms
                ] + [
                    {"summary": {"$regex": term, "$options": "i"}} for term in key_terms
                ]
            }
            
            logger.info(f"🔍 Searching for chunks with terms: {key_terms}")
            
            # Query chunks collection
            chunks = []
            async for chunk in self.db.chunks.find(search_query).limit(limit):
                chunk.pop("_id", None)
                chunks.append(chunk)
            
            logger.info(f"📄 Found {len(chunks)} chunks with specific terms")
            
            # If no specific matches, get all chunks with text for analysis
            if not chunks:
                logger.info("🔍 No specific matches found, getting all chunks with text...")
                all_chunks = []
                async for chunk in self.db.chunks.find({"text": {"$exists": True, "$ne": ""}}).limit(100):
                    chunk.pop("_id", None)
                    all_chunks.append(chunk)
                chunks = all_chunks
                logger.info(f"📄 Retrieved {len(chunks)} chunks with text for analysis")
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Error searching chunks: {e}")
            return []
    
    async def call_deepseek_llm(self, question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call DeepSeek LLM to answer the question based on chunks"""
        try:
            # Prepare context from chunks (limit to avoid token limits)
            context_parts = []
            document_sources = set()
            
            # Limit context to avoid token limits (use first 30 chunks)
            limited_chunks = chunks[:30]
            logger.info(f"📄 Using {len(limited_chunks)} chunks for LLM analysis (out of {len(chunks)} total)")
            
            for i, chunk in enumerate(limited_chunks):
                context_parts.append(f"--- Document {i+1} ---")
                context_parts.append(f"Page: {chunk.get('page_from', 'N/A')}-{chunk.get('page_to', 'N/A')}")
                context_parts.append(f"Text: {chunk.get('text', '')[:2000]}...")  # Limit text length
                context_parts.append(f"Summary: {chunk.get('summary', '')}")
                if chunk.get('doc_id'):
                    document_sources.add(chunk.get('doc_id'))
                context_parts.append("")
            
            context = "\n".join(context_parts)
            
            # Create prompt for DeepSeek
            prompt = f"""
You are an expert policy analyst. Based on the provided document chunks, answer the following question with a clear YES or NO response, along with detailed reasoning and source identification.

QUESTION: {question}

DOCUMENT CHUNKS (showing {len(limited_chunks)} out of {len(chunks)} total chunks):
{context}

Please provide your answer in the following JSON format:
{{
    "answer": "YES" or "NO" or "UNKNOWN",
    "reason": "Detailed explanation of why the answer is YES, NO, or UNKNOWN, citing specific evidence from the documents",
    "confidence": 0.0 to 1.0,
    "source_documents": ["list of document IDs that contain relevant information"],
    "key_evidence": "Specific quotes or references from the documents that support your answer",
    "total_chunks_searched": {len(chunks)},
    "chunks_analyzed": {len(limited_chunks)}
}}

Instructions:
1. Answer must be either "YES", "NO", or "UNKNOWN"
2. If the information is clearly stated in the documents, answer YES or NO
3. If the information is not found or unclear, answer UNKNOWN
4. Provide clear, detailed reasoning based on the document content
5. Identify which specific documents contain the relevant information
6. Include specific quotes or references when possible
7. If the information is not found in the provided chunks, state this clearly
"""

            # Call DeepSeek API
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 3000
            }
            
            logger.info("🤖 Calling DeepSeek LLM...")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.deepseek_base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info("✅ DeepSeek LLM response received")
                    
                    # Try to parse JSON response
                    try:
                        # Extract JSON from response (in case there's extra text)
                        start_idx = content.find('{')
                        end_idx = content.rfind('}') + 1
                        if start_idx != -1 and end_idx != -1:
                            json_str = content[start_idx:end_idx]
                            parsed_response = json.loads(json_str)
                            return parsed_response
                        else:
                            # Fallback if JSON parsing fails
                            return {
                                "answer": "UNKNOWN",
                                "reason": content,
                                "confidence": 0.5,
                                "source_documents": list(document_sources),
                                "key_evidence": "Could not parse structured response",
                                "total_chunks_searched": len(chunks),
                                "chunks_analyzed": len(limited_chunks)
                            }
                    except json.JSONDecodeError:
                        logger.warning("⚠️ Could not parse JSON response, returning raw content")
                        return {
                            "answer": "UNKNOWN",
                            "reason": content,
                            "confidence": 0.5,
                            "source_documents": list(document_sources),
                            "key_evidence": "Raw LLM response (JSON parsing failed)",
                            "total_chunks_searched": len(chunks),
                            "chunks_analyzed": len(limited_chunks)
                        }
                else:
                    logger.error(f"❌ DeepSeek API error: {response.status_code} - {response.text}")
                    return {
                        "answer": "ERROR",
                        "reason": f"API Error: {response.status_code} - {response.text}",
                        "confidence": 0.0,
                        "source_documents": [],
                        "key_evidence": "API call failed",
                        "total_chunks_searched": len(chunks),
                        "chunks_analyzed": 0
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error calling DeepSeek LLM: {e}")
            return {
                "answer": "ERROR",
                "reason": f"LLM Error: {str(e)}",
                "confidence": 0.0,
                "source_documents": [],
                "key_evidence": "LLM call failed",
                "total_chunks_searched": len(chunks),
                "chunks_analyzed": 0
            }
    
    async def search_external_sources_with_llm(self, question: str) -> Dict[str, Any]:
        """Search external sources using DeepSeek LLM with regulatory knowledge"""
        try:
            # Create prompt for external source search
            prompt = f"""
You are an expert policy analyst with access to current regulatory information. Based on your knowledge of healthcare regulations, particularly Medi-Cal, Medicare, and managed care plans, answer the following question.

QUESTION: {question}

Please search your knowledge for information about:
1. Medi-Cal Managed Care Plans (MCPs) and hospice services
2. California Department of Health Care Services (DHCS) requirements
3. All Plan Letters (APLs) related to hospice services, particularly APL 25-008
4. Medicare Advantage plans and hospice coverage
5. Federal and state regulations regarding hospice enrollment
6. Contract requirements for managed care plans

Please provide your answer in the following JSON format:
{{
    "answer": "YES" or "NO" or "UNKNOWN",
    "reason": "Detailed explanation based on regulatory knowledge and current policies",
    "confidence": 0.0 to 1.0,
    "source_type": "external_regulatory_knowledge",
    "key_evidence": "Specific regulatory references, APL numbers, or policy citations",
    "regulatory_basis": "List of relevant regulations, APLs, or policy documents",
    "last_updated": "Your knowledge cutoff date or when this information was last verified"
}}

Instructions:
1. Answer must be either "YES", "NO", or "UNKNOWN"
2. Base your answer on current regulatory requirements and policy knowledge
3. Include specific references to APLs, regulations, or policy documents when possible
4. Provide clear reasoning based on regulatory requirements
5. If you're uncertain about current requirements, answer UNKNOWN
6. Include confidence level based on the clarity of regulatory requirements
"""

            # Call DeepSeek API for external search
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 3000
            }
            
            logger.info("🌐 Calling DeepSeek LLM for external source analysis...")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.deepseek_base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info("✅ DeepSeek LLM external search response received")
                    
                    # Try to parse JSON response
                    try:
                        # Extract JSON from response (in case there's extra text)
                        start_idx = content.find('{')
                        end_idx = content.rfind('}') + 1
                        if start_idx != -1 and end_idx != -1:
                            json_str = content[start_idx:end_idx]
                            parsed_response = json.loads(json_str)
                            return parsed_response
                        else:
                            # Fallback if JSON parsing fails
                            return {
                                "answer": "UNKNOWN",
                                "reason": content,
                                "confidence": 0.5,
                                "source_type": "external_regulatory_knowledge",
                                "key_evidence": "Raw LLM response (JSON parsing failed)",
                                "regulatory_basis": "Unable to parse structured response",
                                "last_updated": "Unknown"
                            }
                    except json.JSONDecodeError:
                        logger.warning("⚠️ Could not parse JSON response from external search, returning raw content")
                        return {
                            "answer": "UNKNOWN",
                            "reason": content,
                            "confidence": 0.5,
                            "source_type": "external_regulatory_knowledge",
                            "key_evidence": "Raw LLM response (JSON parsing failed)",
                            "regulatory_basis": "Unable to parse structured response",
                            "last_updated": "Unknown"
                        }
                else:
                    logger.error(f"❌ DeepSeek API error for external search: {response.status_code} - {response.text}")
                    return {
                        "answer": "ERROR",
                        "reason": f"External search API Error: {response.status_code} - {response.text}",
                        "confidence": 0.0,
                        "source_type": "external_regulatory_knowledge",
                        "key_evidence": "External search API call failed",
                        "regulatory_basis": "API call failed",
                        "last_updated": "Unknown"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error in external source search: {e}")
            return {
                "answer": "ERROR",
                "reason": f"External search error: {str(e)}",
                "confidence": 0.0,
                "source_type": "external_regulatory_knowledge",
                "key_evidence": "External search failed",
                "regulatory_basis": "System error",
                "last_updated": "Unknown"
            }
    
    async def get_document_names(self, doc_ids: List[str]) -> Dict[str, str]:
        """Get document names for the given document IDs"""
        try:
            doc_names = {}
            for doc_id in doc_ids:
                doc = await self.db.documents.find_one({"_id": doc_id})
                if doc:
                    doc_names[doc_id] = doc.get("title", f"Document {doc_id}")
                else:
                    doc_names[doc_id] = f"Unknown Document {doc_id}"
            return doc_names
        except Exception as e:
            logger.error(f"❌ Error getting document names: {e}")
            return {doc_id: f"Document {doc_id}" for doc_id in doc_ids}
    
    async def store_answer_in_db(self, question_id: str, answer_data: Dict[str, Any]) -> bool:
        """Store the answer in the answers collection"""
        try:
            # Prepare answer document for storage
            answer_doc = {
                "question_id": question_id,
                "answer": answer_data.get("answer", "UNKNOWN"),
                "confidence": answer_data.get("confidence", 0.0),
                "reason": answer_data.get("reason", ""),
                "source_type": answer_data.get("source_type", "unknown"),
                "key_evidence": answer_data.get("key_evidence", ""),
                "source_documents": answer_data.get("source_documents", []),
                "document_names": answer_data.get("document_names", {}),
                "total_chunks_searched": answer_data.get("total_chunks_searched", 0),
                "chunks_analyzed": answer_data.get("chunks_analyzed", 0),
                "internal_analysis": answer_data.get("internal_analysis", {}),
                "external_analysis": answer_data.get("external_analysis", {}),
                "regulatory_basis": answer_data.get("external_analysis", {}).get("regulatory_basis", []),
                "last_updated": answer_data.get("external_analysis", {}).get("last_updated", ""),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "audit_question": answer_data.get("audit_question", {})
            }
            
            # Insert or update the answer
            result = await self.db.answers.replace_one(
                {"question_id": question_id},
                answer_doc,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.info(f"✅ Answer stored successfully for question ID: {question_id}")
                return True
            else:
                logger.warning(f"⚠️ No changes made when storing answer for question ID: {question_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error storing answer in database: {e}")
            return False
    
    async def answer_audit_question(self, question_id: str, force_reprocess: bool = False) -> Dict[str, Any]:
        """Main method to answer a specific audit question and store the result"""
        try:
            logger.info(f"🔍 Starting audit question answering process...")
            logger.info(f"Question ID: {question_id}")
            
            # Connect to MongoDB
            if not await self.connect_to_mongodb():
                return {
                    "answer": "ERROR",
                    "reason": "Failed to connect to database",
                    "confidence": 0.0,
                    "source_documents": [],
                    "document_names": {},
                    "source_type": "internal_documents"
                }
            
            # Check if answer already exists (unless force reprocess)
            if not force_reprocess:
                existing_answer = await self.check_existing_answer(question_id)
                if existing_answer:
                    logger.info(f"📋 Using existing answer for question ID: {question_id}")
                    return existing_answer
            
            # Fetch the audit question
            audit_question = await self.fetch_audit_question(question_id)
            if not audit_question:
                return {
                    "answer": "ERROR",
                    "reason": f"Audit question with ID {question_id} not found",
                    "confidence": 0.0,
                    "source_documents": [],
                    "document_names": {},
                    "source_type": "internal_documents"
                }
            
            # Extract the question text
            question_text = audit_question.get("requirement", "")
            reference = audit_question.get("reference", "")
            tags = audit_question.get("tags", [])
            
            logger.info(f"📋 Question: {question_text}")
            logger.info(f"📋 Reference: {reference}")
            logger.info(f"📋 Tags: {tags}")
            
            # Search for relevant chunks
            chunks = await self.search_relevant_chunks(question_text)
            if not chunks:
                logger.info("📄 No internal documents found, searching external sources...")
                external_response = await self.search_external_sources_with_llm(question_text)
                external_response["source_type"] = "external_regulatory_knowledge"
                external_response["timestamp"] = datetime.utcnow().isoformat()
                external_response["audit_question"] = audit_question
                
                # Store the answer in database
                await self.store_answer_in_db(question_id, external_response)
                return external_response
            
            # Call DeepSeek LLM for internal documents
            llm_response = await self.call_deepseek_llm(question_text, chunks)
            llm_response["source_type"] = "internal_documents"
            
            # Get document names
            doc_names = await self.get_document_names(llm_response.get("source_documents", []))
            llm_response["document_names"] = doc_names
            
            # If internal answer is UNKNOWN, search external sources
            if llm_response.get("answer") == "UNKNOWN":
                logger.info("🔍 Internal answer is UNKNOWN, searching external sources...")
                external_response = await self.search_external_sources_with_llm(question_text)
                
                # Combine internal and external results
                combined_response = {
                    "answer": external_response.get("answer", "UNKNOWN"),
                    "reason": f"INTERNAL DOCUMENTS: {llm_response.get('reason', 'No information found')}\n\nEXTERNAL SOURCES: {external_response.get('reason', 'No external information found')}",
                    "confidence": max(llm_response.get("confidence", 0.0), external_response.get("confidence", 0.0)),
                    "source_type": "combined_internal_and_external",
                    "internal_analysis": {
                        "answer": llm_response.get("answer"),
                        "reason": llm_response.get("reason"),
                        "confidence": llm_response.get("confidence"),
                        "source_documents": llm_response.get("source_documents", []),
                        "document_names": llm_response.get("document_names", {}),
                        "total_chunks_searched": llm_response.get("total_chunks_searched", 0),
                        "chunks_analyzed": llm_response.get("chunks_analyzed", 0)
                    },
                    "external_analysis": {
                        "answer": external_response.get("answer"),
                        "reason": external_response.get("reason"),
                        "confidence": external_response.get("confidence"),
                        "key_evidence": external_response.get("key_evidence"),
                        "regulatory_basis": external_response.get("regulatory_basis"),
                        "last_updated": external_response.get("last_updated")
                    },
                    "key_evidence": external_response.get("key_evidence", llm_response.get("key_evidence")),
                    "source_documents": llm_response.get("source_documents", []),
                    "document_names": llm_response.get("document_names", {}),
                    "total_chunks_searched": llm_response.get("total_chunks_searched", 0),
                    "chunks_analyzed": llm_response.get("chunks_analyzed", 0)
                }
                
                combined_response["timestamp"] = datetime.utcnow().isoformat()
                combined_response["audit_question"] = audit_question
                
                # Store the answer in database
                await self.store_answer_in_db(question_id, combined_response)
                return combined_response
            else:
                # Internal answer is clear, return it
                llm_response["timestamp"] = datetime.utcnow().isoformat()
                llm_response["audit_question"] = audit_question
                
                # Store the answer in database
                await self.store_answer_in_db(question_id, llm_response)
                return llm_response
            
        except Exception as e:
            logger.error(f"❌ Error in answer_audit_question: {e}")
            return {
                "answer": "ERROR",
                "reason": f"System error: {str(e)}",
                "confidence": 0.0,
                "source_documents": [],
                "document_names": {},
                "source_type": "internal_documents"
            }
        finally:
            if self.client:
                self.client.close()

async def main():
    """Main function to answer the specific audit question"""
    
    # The specific question ID to fetch and answer
    question_id = "68c0abd03473e5f64e173629_3"
    
    # Create the question answering system
    qa_system = AuditQuestionAnsweringSystem()
    
    # Force reprocess to generate new answer and store it
    print("🔄 Reprocessing question and storing answer in database...")
    result = await qa_system.answer_audit_question(question_id, force_reprocess=True)
    
    # Print results
    print("\n" + "="*100)
    print("AUDIT QUESTION ANSWERING RESULTS")
    print("="*100)
    
    if result.get("audit_question"):
        audit_q = result["audit_question"]
        print(f"Question ID: {audit_q.get('question_id', 'N/A')}")
        print(f"Questionnaire ID: {audit_q.get('questionnaire_id', 'N/A')}")
        print(f"Reference: {audit_q.get('reference', 'N/A')}")
        print(f"Tags: {audit_q.get('tags', [])}")
        print(f"Created At: {audit_q.get('created_at', 'N/A')}")
        print(f"Answered: {audit_q.get('answered', 'N/A')}")
        print(f"\nQuestion: {audit_q.get('requirement', 'N/A')}")
    
    print(f"\nAnswer: {result['answer']}")
    print(f"Confidence: {result.get('confidence', 0.0):.2f}")
    print(f"Source Type: {result.get('source_type', 'unknown')}")
    print(f"\nReason: {result['reason']}")
    
    # Handle combined internal and external results
    if result.get('source_type') == 'combined_internal_and_external':
        print(f"\n" + "="*60)
        print("INTERNAL DOCUMENT ANALYSIS:")
        print("="*60)
        internal = result.get('internal_analysis', {})
        print(f"Internal Answer: {internal.get('answer', 'N/A')}")
        print(f"Internal Confidence: {internal.get('confidence', 0.0):.2f}")
        print(f"Internal Reason: {internal.get('reason', 'N/A')}")
        print(f"Total Chunks Searched: {internal.get('total_chunks_searched', 0)}")
        print(f"Chunks Analyzed: {internal.get('chunks_analyzed', 0)}")
        
        print(f"\n" + "="*60)
        print("EXTERNAL REGULATORY ANALYSIS:")
        print("="*60)
        external = result.get('external_analysis', {})
        print(f"External Answer: {external.get('answer', 'N/A')}")
        print(f"External Confidence: {external.get('confidence', 0.0):.2f}")
        print(f"External Reason: {external.get('reason', 'N/A')}")
        print(f"Regulatory Basis: {external.get('regulatory_basis', 'N/A')}")
        print(f"Last Updated: {external.get('last_updated', 'N/A')}")
    
    # Handle regular results
    else:
        if result.get('source_documents'):
            print(f"\nSource Documents:")
            for doc_id in result['source_documents']:
                doc_name = result['document_names'].get(doc_id, f"Document {doc_id}")
                print(f"  - {doc_name} (ID: {doc_id})")
        
        if result.get('key_evidence'):
            print(f"\nKey Evidence: {result['key_evidence']}")
        
        print(f"\nTotal Chunks Searched: {result.get('total_chunks_searched', 0)}")
        print(f"Chunks Analyzed: {result.get('chunks_analyzed', 0)}")
    
    print(f"\nTimestamp: {result.get('timestamp', 'N/A')}")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())