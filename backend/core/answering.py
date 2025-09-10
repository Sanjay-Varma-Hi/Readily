import os
import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from core.database import get_database

logger = logging.getLogger(__name__)

async def simple_text_search(question: str) -> List[Dict[str, Any]]:
    """Simple text-based search without vector embeddings"""
    try:
        db = await get_database()
        
        # Simple text search using MongoDB text search
        # This is a basic implementation - in production you'd want more sophisticated text search
        query_words = question.lower().split()
        
        # Build a simple text search query
        text_query = {"$or": []}
        for word in query_words:
            if len(word) > 2:  # Skip very short words
                text_query["$or"].append({"text": {"$regex": word, "$options": "i"}})
        
        # If no meaningful words, return empty
        if not text_query["$or"]:
            return []
        
        # Get some chunks that match
        chunks = []
        async for chunk in db.chunks.find(text_query).limit(5):
            # Get document details
            doc = await db.documents.find_one({"_id": chunk.get("doc_id")})
            
            chunks.append({
                "chunk_id": str(chunk["_id"]),
                "doc_id": str(chunk.get("doc_id", "")),
                "title": doc.get("title", "Unknown") if doc else "Unknown",
                "page_from": chunk.get("page_from", 1),
                "page_to": chunk.get("page_to", 1),
                "text": chunk.get("text", ""),
                "tokens": chunk.get("tokens", 0)
            })
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error in simple text search: {e}")
        return []

async def generate_answers_batch(questionnaire_id: str, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate answers for a batch of questions"""
    try:
        answers = []
        max_parallel = int(os.getenv("MAX_PARALLEL_QUESTIONS", "6"))
        
        # Process questions in batches to respect rate limits
        for i in range(0, len(questions), max_parallel):
            batch = questions[i:i + max_parallel]
            
            # Process batch concurrently
            batch_tasks = [
                generate_single_answer(questionnaire_id, question)
                for question in batch
            ]
            
            batch_answers = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Filter out exceptions and add successful answers
            for answer in batch_answers:
                if isinstance(answer, dict) and "error" not in answer:
                    answers.append(answer)
                elif isinstance(answer, Exception):
                    logger.error(f"Error processing question: {answer}")
        
        return answers

    except Exception as e:
        logger.error(f"Error generating batch answers: {e}")
        return []

async def generate_single_answer(questionnaire_id: str, question: Dict[str, Any]) -> Dict[str, Any]:
    """Generate answer for a single question"""
    try:
        qid = question["qid"]
        question_text = question["text"]
        
        # Simple text-based search (no vector search)
        relevant_chunks = await simple_text_search(question_text)
        
        if not relevant_chunks:
            return {
                "questionnaire_id": questionnaire_id,
                "qid": qid,
                "question_text": question_text,
                "snapshot_id": await get_latest_snapshot_id(),
                "answer": "Not found in provided docs.",
                "citations": [],
                "confidence": 0.0
            }
        
        # Generate simple answer based on relevant chunks
        answer_data = generate_simple_answer(question_text, relevant_chunks)
        
        # Simple confidence calculation
        confidence = 0.5  # Default confidence without vector search
        
        return {
            "questionnaire_id": questionnaire_id,
            "qid": qid,
            "question_text": question_text,
            "snapshot_id": await get_latest_snapshot_id(),
            "answer": answer_data.get("answer", "Not found in provided docs."),
            "citations": answer_data.get("citations", []),
            "confidence": confidence
        }

    except Exception as e:
        logger.error(f"Error generating answer for question {question.get('qid', 'unknown')}: {e}")
        return {
            "questionnaire_id": questionnaire_id,
            "qid": question.get("qid", "unknown"),
            "question_text": question.get("text", ""),
            "snapshot_id": await get_latest_snapshot_id(),
            "answer": "Error processing question.",
            "citations": [],
            "confidence": 0.0,
            "error": str(e)
        }

def generate_simple_answer(question: str, passages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate intelligent answer based on question analysis and relevant passages"""
    try:
        if not passages:
            return {
                "answer": "NO",
                "citations": [],
                "confidence": 0.0,
                "reasoning": "No relevant information found in the provided documents."
            }
        
        # Analyze the question to understand what we're looking for
        question_lower = question.lower()
        
        # Look for specific keywords that indicate what type of answer we need
        positive_keywords = ['does', 'is', 'are', 'will', 'can', 'must', 'should', 'required', 'state', 'specify', 'indicate']
        negative_keywords = ['not', 'no', 'never', 'cannot', 'must not', 'should not', 'prohibited', 'restricted']
        
        # Find the most relevant passage by analyzing content
        best_passage = None
        best_score = 0
        best_evidence = ""
        
        for passage in passages:
            text = passage.get('text', '').lower()
            score = 0
            
            # Score based on keyword matches
            for keyword in positive_keywords:
                if keyword in text:
                    score += 1
            
            # Look for specific policy terms that might be relevant
            policy_terms = ['policy', 'procedure', 'requirement', 'standard', 'guideline', 'must', 'shall', 'required']
            for term in policy_terms:
                if term in text:
                    score += 2
            
            # Look for specific content that matches the question context
            if 'hospice' in question_lower and 'hospice' in text:
                score += 3
            if 'prior authorization' in question_lower and 'prior authorization' in text:
                score += 3
            if 'medicare' in question_lower and 'medicare' in text:
                score += 2
            if 'certification' in question_lower and 'certification' in text:
                score += 2
            
            if score > best_score:
                best_score = score
                best_passage = passage
                best_evidence = text
        
        if not best_passage:
            return {
                "answer": "NO",
                "citations": [],
                "confidence": 0.0,
                "reasoning": "No relevant information found that directly addresses the question."
            }
        
        # Analyze the best passage to determine the answer
        evidence_text = best_passage.get('text', '')
        evidence_lower = evidence_text.lower()
        
        # Look for positive indicators
        positive_indicators = ['yes', 'required', 'must', 'shall', 'will', 'can', 'should', 'specified', 'indicated', 'stated']
        negative_indicators = ['no', 'not', 'never', 'cannot', 'must not', 'should not', 'prohibited', 'restricted', 'excluded']
        
        positive_count = sum(1 for indicator in positive_indicators if indicator in evidence_lower)
        negative_count = sum(1 for indicator in negative_indicators if indicator in evidence_lower)
        
        # Determine answer based on evidence
        if positive_count > negative_count:
            answer = "YES"
            confidence = min(0.9, 0.5 + (positive_count * 0.1))
        elif negative_count > positive_count:
            answer = "NO"
            confidence = min(0.9, 0.5 + (negative_count * 0.1))
        else:
            # If unclear, look for specific policy language
            if any(term in evidence_lower for term in ['policy states', 'procedure requires', 'standard specifies']):
                answer = "YES"
                confidence = 0.7
            else:
                answer = "NO"
                confidence = 0.3
        
        # Create meaningful reasoning
        reasoning = f"Based on analysis of the document '{best_passage.get('title', 'Unknown')}', "
        if answer == "YES":
            reasoning += f"the policy does address this requirement. "
        else:
            reasoning += f"the policy does not clearly address this requirement. "
        
        reasoning += f"Found {positive_count} positive indicators and {negative_count} negative indicators in the relevant text."
        
        # Extract a meaningful quote (not the entire document)
        quote = evidence_text[:300] + "..." if len(evidence_text) > 300 else evidence_text
        
        # Create citations
        citations = [{
            "docId": best_passage.get('doc_id', ''),
            "title": best_passage.get('title', ''),
            "pageFrom": best_passage.get('page_from', 1),
            "pageTo": best_passage.get('page_to', 1),
            "chunkId": best_passage.get('chunk_id', ''),
            "quote": quote
        }]
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "reasoning": reasoning,
            "evidence": quote
        }

    except Exception as e:
        logger.error(f"Error generating simple answer: {e}")
        return {
            "answer": "NO",
            "citations": [],
            "confidence": 0.0,
            "reasoning": f"Error analyzing question: {str(e)}"
        }

def validate_answer_data(answer_data: Dict[str, Any], passages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and clean answer data"""
    try:
        # Ensure required fields
        if "answer" not in answer_data:
            answer_data["answer"] = "Not found in provided docs."
        
        if "citations" not in answer_data:
            answer_data["citations"] = []
        
        if "confidence" not in answer_data:
            answer_data["confidence"] = 0.0
        
        # Validate confidence range
        confidence = float(answer_data["confidence"])
        answer_data["confidence"] = max(0.0, min(1.0, confidence))
        
        # Validate citations
        valid_citations = []
        passage_lookup = {p["chunk_id"]: p for p in passages}
        
        for citation in answer_data["citations"]:
            if isinstance(citation, dict):
                chunk_id = citation.get("chunkId")
                if chunk_id in passage_lookup:
                    valid_citations.append({
                        "docId": citation.get("docId", ""),
                        "title": citation.get("title", ""),
                        "pageFrom": int(citation.get("pageFrom", 0)),
                        "pageTo": int(citation.get("pageTo", 0)),
                        "chunkId": chunk_id
                    })
        
        answer_data["citations"] = valid_citations
        
        return answer_data

    except Exception as e:
        logger.error(f"Error validating answer data: {e}")
        return {
            "answer": "Not found in provided docs.",
            "citations": [],
            "confidence": 0.0
        }

async def get_latest_snapshot_id() -> str:
    """Get the latest snapshot ID"""
    try:
        from core.ingestion import get_latest_snapshot_id as get_snapshot
        return await get_snapshot() or "unknown"
    except Exception as e:
        logger.error(f"Error getting latest snapshot ID: {e}")
        return "unknown"

# Enhanced answering functions removed - keeping simple approach
