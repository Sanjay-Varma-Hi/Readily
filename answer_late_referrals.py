#!/usr/bin/env python3
"""
Question Answering System for Late Referrals and 24-Hour Hospice Access
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

class LateReferralsQuestionAnsweringSystem:
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
    
    async def search_late_referrals_chunks(self, question: str) -> List[Dict[str, Any]]:
        """Search for chunks related to late referrals and 24-hour hospice access"""
        try:
            # Extract key terms from the question for better search
            key_terms = [
                "late referrals", "24 hours", "hospice care", "access", "timely manner",
                "in-network", "hospice providers", "referral", "problems", "clarify",
                "detail", "members", "MCP", "P&P", "policies", "procedures",
                "hospice services", "timely access", "referral process", "network",
                "providers", "urgent", "emergency", "response time", "coordination"
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
            async for chunk in self.db.chunks.find(search_query).limit(375):
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
1. Late referral problems in hospice care
2. 24-hour access requirements for hospice services
3. In-network hospice provider requirements
4. Timely access standards for managed care plans
5. California DHCS requirements for hospice access
6. Medicare/Medi-Cal hospice access standards
7. Managed care plan coordination requirements

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
    
    async def answer_question(self, question: str) -> Dict[str, Any]:
        """Main method to answer a question with automatic external search fallback"""
        try:
            logger.info(f"🔍 Starting comprehensive question answering process...")
            logger.info(f"Question: {question}")
            
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
            
            # Search for relevant chunks
            chunks = await self.search_late_referrals_chunks(question)
            if not chunks:
                logger.info("📄 No internal documents found, searching external sources...")
                external_response = await self.search_external_sources_with_llm(question)
                external_response["source_type"] = "external_regulatory_knowledge"
                external_response["timestamp"] = datetime.utcnow().isoformat()
                return external_response
            
            # Call DeepSeek LLM for internal documents
            llm_response = await self.call_deepseek_llm(question, chunks)
            llm_response["source_type"] = "internal_documents"
            
            # Get document names
            doc_names = await self.get_document_names(llm_response.get("source_documents", []))
            llm_response["document_names"] = doc_names
            
            # If internal answer is UNKNOWN, search external sources
            if llm_response.get("answer") == "UNKNOWN":
                logger.info("🔍 Internal answer is UNKNOWN, searching external sources...")
                external_response = await self.search_external_sources_with_llm(question)
                
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
                return combined_response
            else:
                # Internal answer is clear, return it
                llm_response["timestamp"] = datetime.utcnow().isoformat()
                return llm_response
            
        except Exception as e:
            logger.error(f"❌ Error in answer_question: {e}")
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
    """Main function to answer the specific question about late referrals"""
    
    # The specific question about late referrals and 24-hour access
    question = """Does the P&P state that to avoid problems caused by late referrals, MCP P&Ps should clarify and detail how Members may access hospice care services in a timely manner, preferably within 24 hours of the request from in-Network hospice Providers?"""
    
    # Create the question answering system
    qa_system = LateReferralsQuestionAnsweringSystem()
    result = await qa_system.answer_question(question)
    
    # Print results
    print("\n" + "="*100)
    print("LATE REFERRALS AND 24-HOUR HOSPICE ACCESS QUESTION ANSWERING RESULTS")
    print("="*100)
    print(f"Question: {question}")
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