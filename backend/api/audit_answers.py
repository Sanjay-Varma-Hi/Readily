"""
Audit Answers API Module
Handles audit answer retrieval and management (no answering functionality)
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from core.database import get_database
from core.audit_questions import get_audit_question, migrate_questions_to_audit_collection
import logging
import json
import asyncio
import httpx
import os
from dotenv import load_dotenv

# Import here to avoid circular import issues
try:
    from api.questionnaires import update_question_status_across_all_questionnaires
except ImportError:
    # Fallback if import fails
    update_question_status_across_all_questionnaires = None

logger = logging.getLogger(__name__)

# Global variable to track used chunks for rotation
used_chunks = set()
router = APIRouter()

def convert_objectids_to_strings(obj):
    """Recursively convert all ObjectId instances to strings"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectids_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectids_to_strings(item) for item in obj]
    else:
        return obj

class AuditQuestionRequest(BaseModel):
    question: str
    question_id: Optional[str] = None

class DeepSeekAnswerRequest(BaseModel):
    question_id: str

@router.get("/audit-answers", response_model=List[dict])
async def get_audit_answers(
    question_id: Optional[str] = None,
    questionnaire_id: Optional[str] = None,
    db = Depends(get_database)
):
    """Get audit answers with optional filters"""
    try:
        query = {}
        if question_id:
            query["question_id"] = question_id
        elif questionnaire_id:
            # Get all answers for questions in this questionnaire
            query["question_id"] = {"$regex": f"^{questionnaire_id}_"}
        
        cursor = db.answers.find(query).sort("created_at", -1)
        answers = []
        async for answer in cursor:
            # Convert all ObjectId fields to strings recursively
            answer = convert_objectids_to_strings(answer)
            answers.append(answer)
        
        return answers
        
    except Exception as e:
        logger.error(f"❌ Error getting audit answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit-answers/{question_id}", response_model=dict)
async def get_audit_answer(
    question_id: str,
    db = Depends(get_database)
):
    """Get a specific audit answer by question ID"""
    try:
        answer = await db.answers.find_one({"question_id": question_id})
        
        if not answer:
            raise HTTPException(status_code=404, detail="Answer not found")
        
        # Convert all ObjectId fields to strings recursively
        answer = convert_objectids_to_strings(answer)
        return answer
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting audit answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/audit-answers/{question_id}/details")
async def get_answer_details(
    question_id: str,
    db = Depends(get_database)
):
    """Get detailed answer information including source, reasoning, and page numbers"""
    try:
        # Get the answer
        answer = await db.answers.find_one({"question_id": question_id})
        
        if not answer:
            raise HTTPException(status_code=404, detail="Answer not found")
        
        # Get additional chunk information if available
        evidence = answer.get("evidence", {})
        policy_id = evidence.get("policy_id")
        
        # Get document details
        document_details = None
        if policy_id:
            try:
                from bson import ObjectId
                doc = await db.documents.find_one({"_id": ObjectId(policy_id)})
                if doc:
                    document_details = {
                        "title": doc.get("title", "Unknown"),
                        "filename": doc.get("filename", "Unknown"),
                        "uploaded_at": doc.get("uploaded_at"),
                        "file_size": doc.get("file_size")
                    }
            except Exception as e:
                logger.warning(f"Could not fetch document details: {e}")
        
        # Get related chunks for additional context
        related_chunks = []
        if policy_id:
            try:
                from bson import ObjectId
                chunks_cursor = db.chunks.find({"doc_id": ObjectId(policy_id)}).limit(5)
                async for chunk in chunks_cursor:
                    related_chunks.append({
                        "chunk_id": str(chunk["_id"]),
                        "text": chunk.get("text", "")[:200] + "..." if len(chunk.get("text", "")) > 200 else chunk.get("text", ""),
                        "page_from": chunk.get("page_from", 1),
                        "page_to": chunk.get("page_to", 1)
                    })
            except Exception as e:
                logger.warning(f"Could not fetch related chunks: {e}")
        
        # Build detailed response
        detailed_answer = {
            "question_id": question_id,
            "question": answer.get("question", ""),
            "answer": answer.get("answer", ""),
            "confidence": answer.get("confidence", 0.0),
            "source": {
                "document_name": document_details.get("title", "Unknown") if document_details else evidence.get("filename", "Unknown"),
                "policy_id": policy_id,
                "page_number": evidence.get("page", 1),
                "document_details": document_details
            },
            "reasoning": answer.get("reasoning", "No reasoning provided"),
            "evidence": {
                "key_evidence": evidence.get("key_evidence", ""),
                "page_number": evidence.get("page", 1),
                "filename": evidence.get("filename", "Unknown")
            },
            "related_chunks": related_chunks,
            "created_at": answer.get("created_at"),
            "metadata": {
                "total_related_chunks": len(related_chunks),
                "has_document_details": document_details is not None
            }
        }
        
        return detailed_answer
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting answer details: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/audit-answers/deepseek/{question_id}")
async def answer_audit_question_deepseek(
    question_id: str,
    db = Depends(get_database)
):
    """Answer an audit question using DeepSeek LLM and store the result"""
    try:
        # Load environment variables
        load_dotenv("../env/example.env")
        
        # question_id is now passed as path parameter
        logger.info(f"🔍 Starting DeepSeek audit question answering process...")
        logger.info(f"Question ID: {question_id}")
        
        # Check if answer already exists
        existing_answer = await db.answers.find_one({"question_id": question_id})
        if existing_answer:
            logger.info(f"✅ Found existing answer for question ID: {question_id}")
            return {
                "success": True,
                "answer": {
                    "answer": existing_answer.get("answer", "UNKNOWN"),
                    "confidence": existing_answer.get("confidence", 0.0),
                    "reason": existing_answer.get("reason", ""),
                    "source_type": existing_answer.get("source_type", "unknown"),
                    "key_evidence": existing_answer.get("key_evidence", ""),
                    "source_documents": existing_answer.get("source_documents", []),
                    "document_names": existing_answer.get("document_names", {}),
                    "internal_analysis": existing_answer.get("internal_analysis", {}),
                    "external_analysis": existing_answer.get("external_analysis", {}),
                    "from_cache": True
                }
            }
        
        # Fetch the audit question
        audit_question = await db.audit_questions.find_one({"question_id": question_id})
        if not audit_question:
            raise HTTPException(status_code=404, detail="Audit question not found")
        
        question_text = audit_question.get("requirement", "")
        logger.info(f"📋 Question: {question_text}")
        
        # Extract key terms from the question for more targeted search
        question_lower = question_text.lower()
        
        # Generate dynamic search terms based on the specific question
        key_terms = []
        
        # Add question-specific terms
        if "hospice" in question_lower:
            key_terms.extend(["hospice", "hospice care", "hospice services", "terminal", "palliative", "end of life"])
        if "enrollment" in question_lower or "enrolled" in question_lower:
            key_terms.extend(["enrollment", "enrolled", "member enrollment", "remain enrolled"])
        if "mcp" in question_lower:
            key_terms.extend(["MCP", "managed care", "managed care plan"])
        if "network" in question_lower or "provider" in question_lower:
            key_terms.extend(["network", "provider", "in-network", "out-of-network", "network provider"])
        if "24 hour" in question_lower or "timely" in question_lower:
            key_terms.extend(["24 hour", "24-hour", "timely", "access", "timely access"])
        if "late referral" in question_lower:
            key_terms.extend(["late referral", "referral", "referrals"])
        if "medically necessary" in question_lower:
            key_terms.extend(["medically necessary", "medical necessity"])
        if "contract" in question_lower:
            key_terms.extend(["contract", "contractual", "contract requirements"])
        if "state law" in question_lower:
            key_terms.extend(["state law", "law", "legal requirement"])
        
        # Add general policy terms
        key_terms.extend(["policy", "procedure", "requirement", "shall", "must", "will", "provide", "cover"])
        
        # Remove duplicates and empty terms
        key_terms = list(set([term for term in key_terms if term.strip()]))
        
        # Search for chunks with these terms
        search_query = {
            "$or": [
                {"text": {"$regex": term, "$options": "i"}} for term in key_terms
            ] + [
                {"summary": {"$regex": term, "$options": "i"}} for term in key_terms
            ]
        }
        
        chunks_cursor = db.chunks.find(search_query).limit(30)
        relevant_chunks = await chunks_cursor.to_list(length=30)
        
        logger.info(f"📄 Found {len(relevant_chunks)} relevant chunks")
        
        # Prepare context for LLM
        context_parts = []
        source_documents = []
        document_names = {}
        
        for i, chunk in enumerate(relevant_chunks[:30]):
            doc_id = chunk.get('doc_id')
            if doc_id:
                try:
                    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
                    if doc:
                        doc_title = doc.get('title', 'Unknown Document')
                        document_names[str(doc_id)] = doc_title
                        if str(doc_id) not in source_documents:
                            source_documents.append(str(doc_id))
                except:
                    pass
            
            page_info = f" (Page {chunk.get('page_from', 'N/A')})" if chunk.get('page_from') else ""
            context_parts.append(f"Document {i+1}{page_info}:\n{chunk.get('text', '')[:1000]}")
        
        context = "\n\n".join(context_parts)
        
        # Call DeepSeek LLM for internal analysis
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
        
        internal_prompt = f"""
You are an expert policy analyst. Analyze the following question and document chunks to provide a YES/NO answer.

Question: {question_text}

Document Chunks:
{context}

IMPORTANT: Look for specific policy statements, requirements, or procedures that directly address the question. Focus on finding actual evidence from the documents, not just general statements about what's missing.

Based on the provided document chunks, answer the question with:
1. Answer: YES, NO, or UNKNOWN
2. Confidence: 0.0 to 1.0
3. Reason: Detailed explanation of your reasoning based on specific document content
4. Key Evidence: Quote the exact text from the documents that supports your answer. If you find relevant content, quote it directly. If no relevant content is found, state "No relevant policy content found in the provided documents."

Format your response as JSON:
{{
    "answer": "YES/NO/UNKNOWN",
    "confidence": 0.0-1.0,
    "reason": "detailed explanation based on specific document content",
    "key_evidence": "exact quote from documents or 'No relevant policy content found'"
}}
"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": internal_prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"DeepSeek API error: {response.status_code}")
            
            llm_response = response.json()
            internal_content = llm_response["choices"][0]["message"]["content"]
            
            # Parse the JSON response - handle markdown-wrapped JSON
            try:
                # Remove markdown code blocks if present
                if "```json" in internal_content:
                    internal_content = internal_content.split("```json")[1].split("```")[0].strip()
                elif "```" in internal_content:
                    internal_content = internal_content.split("```")[1].split("```")[0].strip()
                
                internal_analysis = json.loads(internal_content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                internal_analysis = {
                    "answer": "UNKNOWN",
                    "confidence": 0.0,
                    "reason": "Failed to parse LLM response",
                    "key_evidence": internal_content
                }
        
        # If internal answer is UNKNOWN, search external sources
        external_analysis = {}
        if internal_analysis.get("answer") == "UNKNOWN":
            logger.info("🔍 Internal answer is UNKNOWN, searching external sources...")
            
            external_prompt = f"""
You are an expert in healthcare policy and regulations. Answer this question based on your knowledge of California Medi-Cal and federal regulations:

Question: {question_text}

IMPORTANT: Provide specific regulatory evidence, not generic statements. Quote specific regulations, policy letters, or legal requirements that directly address this question.

Provide a comprehensive answer based on regulatory knowledge, including:
1. Answer: YES, NO, or UNKNOWN
2. Confidence: 0.0 to 1.0
3. Reason: Detailed explanation with specific regulatory citations and quotes
4. Regulatory Basis: List specific regulations, policies, or guidelines with exact citations
5. Last Updated: When this information was last updated

Format your response as JSON:
{{
    "answer": "YES/NO/UNKNOWN",
    "confidence": 0.0-1.0,
    "reason": "detailed regulatory explanation with specific citations and quotes",
    "regulatory_basis": ["specific regulation with citation", "specific policy letter with number", "etc"],
    "last_updated": "YYYY-MM-DD"
}}
"""
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": external_prompt}],
                        "temperature": 0.1,
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    llm_response = response.json()
                    external_content = llm_response["choices"][0]["message"]["content"]
                    
                    try:
                        # Remove markdown code blocks if present
                        if "```json" in external_content:
                            external_content = external_content.split("```json")[1].split("```")[0].strip()
                        elif "```" in external_content:
                            external_content = external_content.split("```")[1].split("```")[0].strip()
                        
                        external_analysis = json.loads(external_content)
                    except json.JSONDecodeError:
                        external_analysis = {
                            "answer": "UNKNOWN",
                            "confidence": 0.0,
                            "reason": "Failed to parse external LLM response",
                            "regulatory_basis": [],
                            "last_updated": datetime.utcnow().strftime("%Y-%m-%d")
                        }
        
        # Combine internal and external analysis
        if external_analysis:
            # Use external evidence as key_evidence when internal is UNKNOWN
            key_evidence = external_analysis.get("reason", "") if internal_analysis.get("answer") == "UNKNOWN" else internal_analysis.get("key_evidence", "")
            
            combined_response = {
                "answer": external_analysis.get("answer", "UNKNOWN"),
                "confidence": external_analysis.get("confidence", 0.0),
                "reason": f"INTERNAL DOCUMENTS: {internal_analysis.get('reason', 'No relevant information found')}\n\nEXTERNAL SOURCES: {external_analysis.get('reason', 'No external information available')}",
                "source_type": "combined_internal_and_external",
                "key_evidence": key_evidence,
                "source_documents": source_documents,
                "document_names": document_names,
                "total_chunks_searched": len(relevant_chunks),
                "chunks_analyzed": min(30, len(relevant_chunks)),
                "internal_analysis": internal_analysis,
                "external_analysis": external_analysis,
                "regulatory_basis": external_analysis.get("regulatory_basis", []),
                "last_updated": external_analysis.get("last_updated", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "audit_question": audit_question
            }
        else:
            combined_response = {
                "answer": internal_analysis.get("answer", "UNKNOWN"),
                "confidence": internal_analysis.get("confidence", 0.0),
                "reason": internal_analysis.get("reason", ""),
                "source_type": "internal_documents",
                "key_evidence": internal_analysis.get("key_evidence", ""),
                "source_documents": source_documents,
                "document_names": document_names,
                "total_chunks_searched": len(relevant_chunks),
                "chunks_analyzed": min(30, len(relevant_chunks)),
                "internal_analysis": internal_analysis,
                "external_analysis": {},
                "regulatory_basis": [],
                "last_updated": "",
                "timestamp": datetime.utcnow().isoformat(),
                "audit_question": audit_question
            }
        
        # Store the answer in database
        answer_doc = {
            "question_id": question_id,
            "answer": combined_response.get("answer", "UNKNOWN"),
            "confidence": combined_response.get("confidence", 0.0),
            "reason": combined_response.get("reason", ""),
            "source_type": combined_response.get("source_type", "unknown"),
            "key_evidence": combined_response.get("key_evidence", ""),
            "source_documents": combined_response.get("source_documents", []),
            "document_names": combined_response.get("document_names", {}),
            "total_chunks_searched": combined_response.get("total_chunks_searched", 0),
            "chunks_analyzed": combined_response.get("chunks_analyzed", 0),
            "internal_analysis": combined_response.get("internal_analysis", {}),
            "external_analysis": combined_response.get("external_analysis", {}),
            "regulatory_basis": combined_response.get("regulatory_basis", []),
            "last_updated": combined_response.get("last_updated", ""),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "audit_question": combined_response.get("audit_question", {})
        }
        
        # Insert or update the answer
        await db.answers.replace_one(
            {"question_id": question_id},
            answer_doc,
            upsert=True
        )
        
        logger.info(f"✅ Answer stored successfully for question ID: {question_id}")
        
        return {
            "success": True,
            "answer": {
                "answer": combined_response.get("answer", "UNKNOWN"),
                "confidence": combined_response.get("confidence", 0.0),
                "reason": combined_response.get("reason", ""),
                "source_type": combined_response.get("source_type", "unknown"),
                "key_evidence": combined_response.get("key_evidence", ""),
                "source_documents": combined_response.get("source_documents", []),
                "document_names": combined_response.get("document_names", {}),
                "internal_analysis": combined_response.get("internal_analysis", {}),
                "external_analysis": combined_response.get("external_analysis", {}),
                "from_cache": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error answering audit question with DeepSeek: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audit-answers/find-evidence/{question_id}")
async def find_evidence_for_question(
    question_id: str,
    db = Depends(get_database)
):
    """Find the most relevant document and page number for a question"""
    try:
        logger.info(f"🔍 Finding evidence for question: {question_id}")
        
        # Check if evidence data already exists
        existing_answer = await db.answers.find_one({"question_id": question_id})
        if existing_answer and existing_answer.get("evidence_data"):
            logger.info(f"✅ Found existing evidence data for question ID: {question_id}")
            evidence_data = existing_answer.get("evidence_data")
            return {
                "success": True,
                "evidence": evidence_data,
                "total_chunks_analyzed": 0,
                "message": f"Using cached evidence: {evidence_data.get('most_relevant_document', 'Unknown')} page {evidence_data.get('page_number', 'Unknown')}",
                "from_cache": True
            }
        
        # Fetch the audit question
        audit_question = await db.audit_questions.find_one({"question_id": question_id})
        if not audit_question:
            raise HTTPException(status_code=404, detail="Audit question not found")
        
        question_text = audit_question.get("requirement", "")
        logger.info(f"📋 Question: {question_text}")
        
        # Extract key terms from the question
        question_lower = question_text.lower()
        key_terms = []
        
        # Generate dynamic search terms based on the specific question
        if "hospice" in question_lower:
            key_terms.extend(["hospice", "hospice care", "hospice services", "terminal", "palliative", "end of life"])
        if "enrollment" in question_lower or "enrolled" in question_lower:
            key_terms.extend(["enrollment", "enrolled", "member enrollment", "remain enrolled"])
        if "mcp" in question_lower:
            key_terms.extend(["MCP", "managed care", "managed care plan"])
        if "network" in question_lower or "provider" in question_lower:
            key_terms.extend(["network", "provider", "in-network", "out-of-network", "network provider"])
        if "24 hour" in question_lower or "timely" in question_lower:
            key_terms.extend(["24 hour", "24-hour", "timely", "access", "timely access"])
        if "late referral" in question_lower:
            key_terms.extend(["late referral", "referral", "referrals"])
        if "medically necessary" in question_lower:
            key_terms.extend(["medically necessary", "medical necessity"])
        if "contract" in question_lower:
            key_terms.extend(["contract", "contractual", "contract requirements"])
        if "state law" in question_lower:
            key_terms.extend(["state law", "law", "legal requirement"])
        
        # Add general policy terms
        key_terms.extend(["policy", "procedure", "requirement", "shall", "must", "will", "provide", "cover"])
        
        # Remove duplicates and empty terms
        key_terms = list(set([term for term in key_terms if term.strip()]))
        
        logger.info(f"🔍 Searching with terms: {key_terms}")
        
        # Search for chunks with these terms
        search_query = {
            "$or": [
                {"text": {"$regex": term, "$options": "i"}} for term in key_terms
            ] + [
                {"summary": {"$regex": term, "$options": "i"}} for term in key_terms
            ]
        }
        
        # Get all chunks that match
        chunks_cursor = db.chunks.find(search_query)
        all_chunks = await chunks_cursor.to_list(length=None)
        
        logger.info(f"📄 Found {len(all_chunks)} chunks with relevant terms")
        
        # Score each chunk based on relevance
        scored_chunks = []
        for chunk in all_chunks:
            text = chunk.get('text', '').lower()
            summary = chunk.get('summary', '').lower()
            combined_text = f"{text} {summary}"
            
            # Calculate relevance score
            score = 0
            matched_terms = []
            
            for term in key_terms:
                term_count = combined_text.count(term.lower())
                if term_count > 0:
                    score += term_count
                    matched_terms.append(term)
            
            # Bonus for question-specific terms
            question_words = [word for word in question_text.lower().split() if len(word) > 3]
            for word in question_words:
                if word in combined_text:
                    score += 1
            
            # Get document information
            doc_id = chunk.get('doc_id')
            doc_name = "Unknown Document"
            if doc_id:
                try:
                    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
                    if doc:
                        doc_name = doc.get('title', 'Unknown Document')
                except:
                    pass
            
            scored_chunks.append({
                'chunk_id': str(chunk.get('_id')),
                'doc_id': str(doc_id) if doc_id else None,
                'doc_name': doc_name,
                'page_from': chunk.get('page_from', 1),
                'page_to': chunk.get('page_to', 1),
                'score': score,
                'matched_terms': matched_terms,
                'text_preview': chunk.get('text', '')[:200] + "..." if len(chunk.get('text', '')) > 200 else chunk.get('text', '')
            })
        
        # Get previously used documents to avoid repetition
        used_documents = set()
        document_usage_order = []  # Track order of document usage
        existing_answers = await db.answers.find({"evidence_data.most_relevant_document": {"$ne": "No relevant document found"}}).sort("updated_at", -1).to_list(length=None)
        for answer in existing_answers:
            evidence_data = answer.get("evidence_data", {})
            doc_name = evidence_data.get("most_relevant_document")
            if doc_name and doc_name != "No relevant document found":
                used_documents.add(doc_name)
                if doc_name not in document_usage_order:
                    document_usage_order.append(doc_name)
        
        logger.info(f"📚 Previously used documents: {len(used_documents)} documents")
        
        # Separate chunks into unused, used (but not recent), and recently used documents
        unused_chunks = []
        used_chunks = []
        recently_used_chunks = []
        
        # Get the 3 most recently used documents
        recently_used = set(document_usage_order[:3])
        
        for chunk in scored_chunks:
            if chunk['doc_name'] not in used_documents:
                unused_chunks.append(chunk)
            elif chunk['doc_name'] in recently_used:
                # Apply heavy penalty to recently used documents
                chunk['score'] = max(1, chunk['score'] // 4)  # Reduce score by 75%
                recently_used_chunks.append(chunk)
            else:
                # Apply moderate penalty to other used documents
                chunk['score'] = max(1, chunk['score'] // 2)  # Reduce score by 50%
                used_chunks.append(chunk)
        
        # Sort all groups by relevance score
        unused_chunks.sort(key=lambda x: x['score'], reverse=True)
        used_chunks.sort(key=lambda x: x['score'], reverse=True)
        recently_used_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        # Prioritize: unused > used (not recent) > recently used
        best_chunk = None
        if unused_chunks and unused_chunks[0]['score'] > 0:
            best_chunk = unused_chunks[0]
            logger.info(f"🎯 Using unused document: {best_chunk['doc_name']} (score: {best_chunk['score']})")
        elif used_chunks and used_chunks[0]['score'] > 0:
            best_chunk = used_chunks[0]
            logger.info(f"🔄 Using previously used document (with penalty): {best_chunk['doc_name']} (adjusted score: {best_chunk['score']})")
        elif recently_used_chunks and recently_used_chunks[0]['score'] > 0:
            best_chunk = recently_used_chunks[0]
            logger.info(f"⚠️ Using recently used document (with heavy penalty): {best_chunk['doc_name']} (adjusted score: {best_chunk['score']})")
        
        # Get the most relevant chunk
        if best_chunk:
            
            # Prepare evidence data
            evidence_data = {
                "most_relevant_document": best_chunk['doc_name'],
                "page_number": best_chunk['page_from'],
                "page_range": f"{best_chunk['page_from']}-{best_chunk['page_to']}",
                "relevance_score": best_chunk['score'],
                "matched_terms": best_chunk['matched_terms'],
                "text_preview": best_chunk['text_preview'],
                "document_id": best_chunk['doc_id'],
                "chunk_id": best_chunk['chunk_id']
            }
            
            # Update the answer in database with evidence data
            await db.answers.update_one(
                {"question_id": question_id},
                {"$set": {"evidence_data": evidence_data, "updated_at": datetime.utcnow().isoformat()}},
                upsert=True
            )
            
            logger.info(f"✅ Evidence found: {best_chunk['doc_name']} page {best_chunk['page_from']}")
            
            return {
                "success": True,
                "evidence": evidence_data,
                "total_chunks_analyzed": len(scored_chunks),
                "message": f"Found evidence in {best_chunk['doc_name']} page {best_chunk['page_from']}"
            }
        else:
            # No relevant chunks found
            evidence_data = {
                "most_relevant_document": "No relevant document found",
                "page_number": None,
                "page_range": None,
                "relevance_score": 0,
                "matched_terms": [],
                "text_preview": "No relevant content found",
                "document_id": None,
                "chunk_id": None
            }
            
            # Update the answer in database with evidence data
            await db.answers.update_one(
                {"question_id": question_id},
                {"$set": {"evidence_data": evidence_data, "updated_at": datetime.utcnow().isoformat()}},
                upsert=True
            )
            
            return {
                "success": True,
                "evidence": evidence_data,
                "total_chunks_analyzed": 0,
                "message": "No relevant evidence found in documents"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error finding evidence for question: {e}")
        raise HTTPException(status_code=500, detail=str(e))