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

class AuditQuestionRequest(BaseModel):
    question: str
    question_id: Optional[str] = None

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
            answer["_id"] = str(answer["_id"])
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
        
        answer["_id"] = str(answer["_id"])
        return answer
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting audit answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/audit-answers/{question_id}")
async def delete_audit_answer(
    question_id: str,
    db = Depends(get_database)
):
    """Delete a specific audit answer"""
    try:
        result = await db.answers.delete_one({"question_id": question_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Answer not found")
        
        return {
            "success": True,
            "message": f"Deleted answer for question {question_id}",
            "deleted_count": result.deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting audit answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/audit-answers")
async def delete_all_audit_answers(
    db = Depends(get_database)
):
    """Delete all audit answers"""
    try:
        result = await db.answers.delete_many({})
        
        return {
            "success": True,
            "message": f"Deleted {result.deleted_count} answers",
            "deleted_count": result.deleted_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error deleting all audit answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audit-answers/single")
async def answer_audit_question(
    request: AuditQuestionRequest,
    db = Depends(get_database)
):
    """Answer a single audit question with detailed information"""
    try:
        question_text = request.question
        question_id = request.question_id
        questionnaire_id, qid = question_id.split('_', 1) if '_' in question_id else (question_id, 'Q1')
        
        logger.info(f"🔍 Answering audit question: {question_text[:100]}...")
        
        # Check if answer already exists - if it does, return the existing answer immediately
        existing_answer = await db.answers.find_one({"question_id": question_id})
        print(f"🔍 CHECKING FOR EXISTING ANSWER:")
        print(f"  - Question ID: {question_id}")
        print(f"  - Existing answer found: {existing_answer is not None}")
        if existing_answer:
            print(f"  - Existing answer: {existing_answer.get('answer', 'NO')}")
            print(f"  - Existing confidence: {existing_answer.get('confidence', 0.0)}")
            print(f"  - Existing reasoning: {existing_answer.get('reasoning', '')[:100]}...")
        
        if existing_answer:
            print(f"🚀 RETURNING EXISTING ANSWER FOR QUESTION {question_id}")
            logger.info(f"⚠️ Answer already exists for question {question_id}, returning existing answer")
            try:
                if update_question_status_across_all_questionnaires:
                    updated_count = await update_question_status_across_all_questionnaires(question_id, True, db)                                                                                                        
                    logger.info(f"✅ Marked question {question_id} as answered in {updated_count} questionnaires (returned existing answer)")                                                                            
                else:
                    logger.warning(f"⚠️ update_question_status_across_all_questionnaires not available, skipping status update")
                
                # Return the existing answer instead of generating a new one
                return {
                    "success": True,
                    "answer": {
                        "answer": existing_answer.get("answer", "NO"),
                        "confidence": existing_answer.get("confidence", 0.0),
                        "evidence": existing_answer.get("evidence", {}),
                        "reasoning": existing_answer.get("reasoning", ""),
                        "source": existing_answer.get("source", {}),
                        "page_number": existing_answer.get("page_number", 1),
                        "quote": existing_answer.get("quote", ""),
                        "from_cache": True  # Indicate this is from cache/existing answer
                    }
                }
            except Exception as e:
                logger.error(f"❌ Error marking question as answered: {e}")
        else:
            print(f"🚀 NO EXISTING ANSWER FOUND, GENERATING NEW ANSWER FOR QUESTION {question_id}")
        
        # Step 1: Parse the reference to get document name and page
        reference = request.question_id  # We'll get this from the question object
        print(f"🔍 Question: {question_text}")
        print(f"🔍 Question ID: {question_id}")
        print("🚀 NEW CODE VERSION 2.0 - CHUNK SEARCH ACTIVE!")
        
        # Search for question content in all chunks
        print(f"🔍 Searching for question content in all chunks...")
        print(f"🔍 Question: {question_text}")
        
        # Get all chunks (up to 400)
        chunks_cursor = db.chunks.find({}).limit(400)
        all_chunks = await chunks_cursor.to_list(length=400)
        print(f"🔍 Found {len(all_chunks)} total chunks")
        
        # Extract key terms from the question - make it more general
        question_lower = question_text.lower()
        key_terms = []
        
        # Extract important words from the question
        important_words = ['policy', 'state', 'require', 'shall', 'must', 'will', 'provide', 'cover', 'payment', 'pay', 'center', 'services', 'member', 'health', 'caloptima', 'dhcs', 'ccs', 'transplant', 'evaluation', 'medically', 'necessary', 'covered', 'network', 'kaiser', 'bone', 'marrow', 'organ', 'mot', 'approved', 'special', 'care']
        
        for word in important_words:
            if word in question_lower:
                key_terms.append(word)
        
        # Also add any 3+ character words from the question
        words = question_lower.split()
        for word in words:
            if len(word) >= 3 and word not in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'man', 'men', 'put', 'say', 'she', 'too', 'use']:
                if word not in key_terms:
                    key_terms.append(word)
        
        print(f"🔍 Key terms to search for: {key_terms}")
        
        # Search for chunks containing these key terms
        relevant_chunks = []
        for chunk in all_chunks:
            text = chunk.get('text', '').lower()
            score = 0
            matched_terms = []
            
            for term in key_terms:
                if term in text:
                    score += 1
                    matched_terms.append(term)
            
            if score > 0:
                relevant_chunks.append({
                    'chunk': chunk,
                    'score': score,
                    'matched_terms': matched_terms
                })
        
        # Sort by relevance score
        relevant_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"🔍 Found {len(relevant_chunks)} chunks with relevant content")
        
        # Show the top 5 chunks and their documents
        print(f"🔍 TOP 5 CHUNKS BY SCORE:")
        for i, chunk_data in enumerate(relevant_chunks[:5]):
            chunk = chunk_data['chunk']
            doc_id = chunk.get('doc_id')
            print(f"  - Chunk #{i+1}: Score={chunk_data['score']}, Doc_ID={doc_id}, Page={chunk.get('page_from', 'N/A')}")
        
        # Show top 5 most relevant chunks
        for i, item in enumerate(relevant_chunks[:5]):
            chunk = item['chunk']
            score = item['score']
            matched_terms = item['matched_terms']
            
            # Get document details
            doc_id = chunk.get('doc_id')
            doc = None
            if doc_id:
                try:
                    from bson import ObjectId
                    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
                except Exception as e:
                    print(f"Error fetching document {doc_id}: {e}")
                    doc = None
            
            print(f"🎯 RELEVANT CHUNK #{i+1} (Score: {score}):")
            print(f"  - Document: {doc.get('title', 'Unknown') if doc else 'Unknown'}")
            print(f"  - Chunk page_from: {chunk.get('page_from', 'N/A')}")
            print(f"  - Chunk page_to: {chunk.get('page_to', 'N/A')}")
            print(f"  - Text contains page info: {'Page' in chunk.get('text', '')}")
            print(f"  - Matched terms: {matched_terms}")
            print(f"  - Text preview: {chunk.get('text', 'N/A')[:300]}...")
            print()
        
        # Determine answer based on content
        actual_page = 1  # Default page number
        quote = "No relevant content found"  # Default quote
        if relevant_chunks:
            # Instead of always picking the first chunk, find the best chunk for this specific question
            best_chunk = None
            best_question_score = 0
            
            # Get question-specific terms for scoring
            question_lower = question_text.lower()
            if 'hospice' in question_lower:
                question_terms = ['hospice', 'palliative', 'end-of-life', 'terminal']
            elif 'transplant' in question_lower:
                question_terms = ['transplant', 'bone marrow', 'organ', 'dhcs-approved', 'ccs-approved']
            elif 'medical review' in question_lower or 'site review' in question_lower:
                question_terms = ['medical review', 'site review', 'prepayment review', 'utilization management', 'claims processing']
            elif 'continuous home care' in question_lower:
                question_terms = ['continuous home care', 'home care', '24-hour care']
            else:
                # For other questions, use key terms
                question_terms = key_terms[:5]
            
            print(f"🔍 FINDING BEST CHUNK FOR QUESTION (WITH ROTATION):")
            print(f"  - Question: {question_text[:100]}...")
            print(f"  - Question-specific terms: {question_terms}")
            print(f"  - Previously used chunks: {len(used_chunks)}")
            print(f"  - Total chunks to evaluate: {min(20, len(relevant_chunks))}")
            
            # Separate chunks into used and unused
            unused_chunks = []
            used_chunks_list = []
            
            for chunk_data in relevant_chunks[:20]:  # Check top 20 chunks
                chunk = chunk_data['chunk']
                chunk_id = chunk.get('_id') or str(chunk.get('doc_id', '')) + '_' + str(chunk.get('page_from', 0))
                
                if chunk_id in used_chunks:
                    used_chunks_list.append(chunk_data)
                else:
                    unused_chunks.append(chunk_data)
            
            print(f"  - Unused chunks: {len(unused_chunks)}")
            print(f"  - Used chunks: {len(used_chunks_list)}")
            
            # Score each UNUSED chunk based on question-specific content
            for i, chunk_data in enumerate(unused_chunks):
                chunk = chunk_data['chunk']
                chunk_text = chunk.get('text', '').lower()
                
                # Count how many question-specific terms are in this chunk
                question_terms_found = sum(1 for term in question_terms if term in chunk_text)
                question_score = question_terms_found / len(question_terms) if question_terms else 0
                
                # Also check for general key terms as a secondary score
                general_terms_found = sum(1 for term in key_terms if term in chunk_text)
                general_score = general_terms_found / len(key_terms) if key_terms else 0
                
                # Combined score: prioritize question-specific terms heavily
                combined_score = (question_score * 0.9) + (general_score * 0.1)
                
                print(f"  - Unused Chunk #{i+1}: Q-score={question_score:.2f}, G-score={general_score:.2f}, Combined={combined_score:.2f}")
                print(f"    - Question terms found: {[term for term in question_terms if term in chunk_text]}")
                print(f"    - Chunk preview: {chunk_text[:100]}...")
                
                # Only select this chunk if it has some question-specific content
                if question_score > 0 and combined_score > best_question_score:
                    best_question_score = combined_score
                    best_chunk = chunk
                    print(f"  - NEW BEST CHUNK! Combined score: {combined_score:.2f}")
            
            # If no unused chunk found, use the first unused chunk regardless of score
            if not best_chunk and unused_chunks:
                best_chunk = unused_chunks[0]['chunk']
                print(f"  - Using first unused chunk (no question-specific match found)")
            
            # If still no chunk found, use the first used chunk (fallback)
            if not best_chunk and used_chunks_list:
                best_chunk = used_chunks_list[0]['chunk']
                print(f"  - Using first used chunk (fallback)")
            
            # If still no chunk found, use the first chunk overall (last resort)
            if not best_chunk:
                best_chunk = relevant_chunks[0]['chunk']
                print(f"  - Using first chunk overall (last resort)")
            
            # Mark the selected chunk as used
            if best_chunk:
                chunk_id = best_chunk.get('_id') or str(best_chunk.get('doc_id', '')) + '_' + str(best_chunk.get('page_from', 0))
                used_chunks.add(chunk_id)
                print(f"  - Marked chunk as used: {chunk_id}")
                print(f"  - Total used chunks now: {len(used_chunks)}")
            
            print(f"🔍 SELECTED CHUNK:")
            print(f"  - Question-specific score: {best_question_score:.2f}")
            print(f"  - Chunk text preview: {best_chunk.get('text', '')[:200]}...")
            best_doc_id = best_chunk.get('doc_id')
            best_doc = None
            if best_doc_id:
                try:
                    from bson import ObjectId
                    best_doc = await db.documents.find_one({"_id": ObjectId(best_doc_id)})
                except Exception as e:
                    print(f"Error fetching best document {best_doc_id}: {e}")
                    best_doc = None
            
            # Look for policy content that answers the question
            text = best_chunk.get('text', '').lower()
            
            # Check for policy indicators and requirements
            policy_indicators = ['policy', 'state', 'require', 'shall', 'must', 'will', 'provide', 'cover', 'payment', 'pay']
            requirement_indicators = ['required', 'must', 'shall', 'will provide', 'ensure', 'contract requires', 'state law requires', 'policy states']
            
            has_policy_content = any(indicator in text for indicator in policy_indicators)
            has_requirements = any(indicator in text for indicator in requirement_indicators)
            
            # Check if the text contains key terms from the question
            question_terms_in_text = sum(1 for term in key_terms if term in text)
            relevance_score = question_terms_in_text / len(key_terms) if key_terms else 0
            
            print(f"🔍 ANALYSIS RESULTS:")
            print(f"  - Has policy content: {has_policy_content}")
            print(f"  - Has requirements: {has_requirements}")
            print(f"  - Relevance score: {relevance_score:.2f} ({question_terms_in_text}/{len(key_terms)} terms matched)")
            print(f"  - Text sample: {text[:200]}...")
            
            # Determine answer based on relevance and specific question content
            # Check if the text actually addresses the specific question asked
            question_specific_terms = []
            if 'hospice' in question_lower:
                question_specific_terms = ['hospice', 'palliative', 'end-of-life', 'terminal']
            elif 'transplant' in question_lower:
                question_specific_terms = ['transplant', 'bone marrow', 'organ', 'dhcs-approved', 'ccs-approved']
            elif 'medical review' in question_lower or 'site review' in question_lower:
                question_specific_terms = ['medical review', 'site review', 'prepayment review', 'utilization management', 'claims processing']
            elif 'continuous home care' in question_lower:
                question_specific_terms = ['continuous home care', 'home care', '24-hour care']
            else:
                # For other questions, use the key terms we extracted
                question_specific_terms = key_terms[:5]  # Use top 5 key terms
            
            # Check if the text contains question-specific terms
            specific_terms_found = sum(1 for term in question_specific_terms if term in text)
            specific_relevance = specific_terms_found / len(question_specific_terms) if question_specific_terms else 0
            
            print(f"🔍 QUESTION-SPECIFIC ANALYSIS:")
            print(f"  - Question-specific terms: {question_specific_terms}")
            print(f"  - Specific terms found: {specific_terms_found}/{len(question_specific_terms)}")
            print(f"  - Specific relevance: {specific_relevance:.2f}")
            
            # Much more strict criteria: need BOTH high general relevance AND high question-specific content
            # Also check that the question-specific terms are actually meaningful (not just common words)
            # Only count domain-specific terms that are actually relevant to the question
            domain_specific_terms = []
            if 'hospice' in question_lower:
                domain_specific_terms = ['hospice', 'palliative', 'end-of-life', 'terminal']
            elif 'transplant' in question_lower:
                domain_specific_terms = ['transplant', 'bone marrow', 'organ', 'dhcs-approved', 'ccs-approved']
            elif 'medical review' in question_lower or 'site review' in question_lower:
                domain_specific_terms = ['medical review', 'site review', 'prepayment review', 'utilization management', 'claims processing']
            elif 'continuous home care' in question_lower:
                domain_specific_terms = ['continuous home care', 'home care', '24-hour care']
            else:
                # For other questions, only count terms that are not common policy words
                domain_specific_terms = [term for term in question_specific_terms if term not in ['policy', 'state', 'will', 'provide', 'services', 'does', 'that', 'health', 'care', 'healthcare']]
            
            domain_specific_relevance = sum(1 for term in domain_specific_terms if term in text) / len(domain_specific_terms) if domain_specific_terms else 0
            
            print(f"🔍 DOMAIN-SPECIFIC TERMS ANALYSIS:")
            print(f"  - Domain-specific terms: {domain_specific_terms}")
            print(f"  - Domain-specific relevance: {domain_specific_relevance:.2f}")
            
            # Check for specific question content that would indicate a clear YES answer
            # Look for exact phrases or very specific content that directly answers the question
            question_phrases = []
            if 'hospice' in question_lower:
                question_phrases = ['hospice care', 'hospice services', 'terminal illness', 'palliative care']
            elif 'transplant' in question_lower:
                question_phrases = ['transplant services', 'bone marrow transplant', 'organ transplant']
            elif 'medical review' in question_lower:
                question_phrases = ['medical review', 'utilization review', 'prepayment review']
            else:
                # For general questions, look for very specific policy language
                question_phrases = ['policy states', 'contract requires', 'state law requires', 'shall provide', 'must provide']
            
            # Check if any of these specific phrases appear in the text
            specific_phrases_found = sum(1 for phrase in question_phrases if phrase in text)
            phrase_relevance = specific_phrases_found / len(question_phrases) if question_phrases else 0
            
            print(f"🔍 PHRASE ANALYSIS:")
            print(f"  - Question phrases: {question_phrases}")
            print(f"  - Specific phrases found: {specific_phrases_found}/{len(question_phrases)}")
            print(f"  - Phrase relevance: {phrase_relevance:.2f}")
            
            # Ultra-conservative approach - default to NO unless there's extremely clear evidence
            # Look for explicit policy statements that directly answer the question
            question_lower = question_text.lower()
            
            # Extract the core question without common words
            core_question = question_lower.replace('does the p&p state that', '').replace('does the policy state that', '').replace('does the policy state', '').replace('does the p&p state', '').strip()
            
            print(f"🔍 ULTRA-CONSERVATIVE ANALYSIS:")
            print(f"  - Core question: {core_question}")
            print(f"  - Text sample: {text[:200]}...")
            
            # Look for very specific policy language that directly addresses the question
            # Only answer YES if the policy explicitly states something about the specific topic
            if 'hospice' in core_question:
                # Look for explicit hospice policy statements
                hospice_policy_found = ('hospice' in text and 
                                      ('policy' in text or 'shall' in text or 'must' in text) and
                                      ('hospice care' in text or 'hospice services' in text or 'terminal illness' in text))
                if hospice_policy_found:
                    answer = "YES"
                    confidence = 0.9
                    reasoning = f"Found explicit hospice policy content. Document '{best_doc.get('title', 'Unknown') if best_doc else 'Unknown'}' contains clear policy statements about hospice care."
                else:
                    answer = "NO"
                    confidence = 0.8
                    reasoning = f"No explicit hospice policy content found that directly addresses the question."
            elif 'transplant' in core_question:
                # Look for explicit transplant policy statements
                transplant_policy_found = ('transplant' in text and 
                                         ('policy' in text or 'shall' in text or 'must' in text) and
                                         ('transplant services' in text or 'bone marrow' in text or 'organ transplant' in text))
                if transplant_policy_found:
                    answer = "YES"
                    confidence = 0.9
                    reasoning = f"Found explicit transplant policy content. Document '{best_doc.get('title', 'Unknown') if best_doc else 'Unknown'}' contains clear policy statements about transplant services."
                else:
                    answer = "NO"
                    confidence = 0.8
                    reasoning = f"No explicit transplant policy content found that directly addresses the question."
            elif 'medical review' in core_question:
                # Look for explicit medical review policy statements
                review_policy_found = (('medical review' in text or 'utilization review' in text) and 
                                     ('policy' in text or 'shall' in text or 'must' in text))
                if review_policy_found:
                    answer = "YES"
                    confidence = 0.9
                    reasoning = f"Found explicit medical review policy content. Document '{best_doc.get('title', 'Unknown') if best_doc else 'Unknown'}' contains clear policy statements about medical review."
                else:
                    answer = "NO"
                    confidence = 0.8
                    reasoning = f"No explicit medical review policy content found that directly addresses the question."
            else:
                # For all other questions, be extremely conservative
                # Only answer YES if there's very specific policy language
                specific_policy_found = (any(phrase in text for phrase in ['policy states', 'contract requires', 'state law requires']) and
                                       core_question.split()[0] in text and
                                       ('shall' in text or 'must' in text))
                
                if specific_policy_found:
                    answer = "YES"
                    confidence = 0.9
                    reasoning = f"Found explicit policy content addressing the question. Document '{best_doc.get('title', 'Unknown') if best_doc else 'Unknown'}' contains clear policy statements about the topic."
                else:
                    answer = "NO"
                    confidence = 0.8
                    reasoning = f"No explicit policy content found that directly addresses the question. The policy documents contain general information but do not specifically address the question asked."
            
            # Set default values for NO answers
            if answer == "NO":
                quote = "No specific policy requirements found that address the question asked."
                actual_page = best_chunk.get('page_from', 1) if best_chunk else 1
                
            # Extract a more relevant quote that actually answers the question
            if answer in ["YES", "PARTIALLY"]:
                full_text = best_chunk.get('text', '')
                actual_page = best_chunk.get('page_from', 1)
                
                # Try to find the most relevant section by looking for key terms from the question
                best_quote = ""
                best_score = 0
                
                # Split text into sentences for better analysis
                sentences = full_text.split('. ')
                
                # Focus on question-specific terms for better quote selection
                question_focus_terms = question_specific_terms if question_specific_terms else key_terms[:5]
                
                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    # Score this sentence based on how many question-specific terms it contains
                    sentence_score = sum(1 for term in question_focus_terms if term in sentence_lower)
                    
                    # Also look for policy action words
                    action_words = ['shall', 'must', 'will', 'required', 'provide', 'pay', 'cover', 'policy states', 'contract requires', 'state law', 'mcp', 'hospice', 'transplant', 'medical review']
                    action_score = sum(1 for word in action_words if word in sentence_lower)
                    
                    # Bonus for sentences that contain the actual question keywords
                    question_keywords = [word for word in question_text.lower().split() if len(word) > 4 and word not in ['does', 'that', 'with', 'from', 'this', 'will', 'shall']]
                    keyword_score = sum(1 for word in question_keywords if word in sentence_lower)
                    
                    total_score = (sentence_score * 3) + (action_score * 2) + keyword_score  # Weight question terms most heavily
                    
                    if total_score > best_score and len(sentence) > 50:  # Avoid very short sentences
                        best_score = total_score
                        best_quote = sentence
                
                # If we found a good sentence, use it with some context
                if best_quote and best_score > 0:
                    # Find the position of this sentence in the full text
                    sentence_pos = full_text.find(best_quote)
                    if sentence_pos != -1:
                        # Get context around this sentence
                        start_pos = max(0, sentence_pos - 100)
                        end_pos = min(len(full_text), sentence_pos + len(best_quote) + 200)
                        quote = full_text[start_pos:end_pos]
                        if end_pos < len(full_text):
                            quote += "..."
                    else:
                        quote = best_quote + "..."
                else:
                    # Fallback: try to find a section that's not just the header
                    # Skip the first few sentences which are usually headers
                    content_sentences = sentences[3:] if len(sentences) > 3 else sentences
                    if content_sentences:
                        quote = '. '.join(content_sentences[:3]) + "..."
                    else:
                        quote = full_text[:500] + "..."
                
                # Extract page number from the final quote
                import re
                page_match = re.search(r'Page (\d+) of \d+', quote)
                if page_match:
                    actual_page = int(page_match.group(1))
                    print(f"🔍 Extracted page number from quote: {actual_page}")
                else:
                    print(f"🔍 No page number found in quote, using chunk metadata: {actual_page}")
            
        else:
            answer = "NO"
            confidence = 0.8
            reasoning = f"No relevant policy content found in any of the {len(all_chunks)} chunks that addresses the question asked."
            quote = "No relevant content found"
            best_doc = None
            best_chunk = None
        
        # Store the answer in the database
        answer_data = {
            "question_id": question_id,
            "questionnaire_id": questionnaire_id,
            "qid": qid,
            "question_text": question_text,
            "answer": answer,
            "confidence": confidence,
            "evidence": {
                "policy_id": str(best_chunk.get('doc_id', '')) if best_chunk else None,
                "filename": best_doc.get('title', 'Unknown') if best_doc else 'Unknown',
                "page": actual_page,
                "quote": quote
            },
            "reasoning": reasoning,
            "source": {
                "document_name": best_doc.get('title', 'Unknown') if best_doc else 'Unknown',
                "policy_id": str(best_chunk.get('doc_id', '')) if best_chunk else None,
                "page_number": actual_page
            },
            "page_number": actual_page,
            "quote": quote,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Save new answer to database
        await db.answers.insert_one(answer_data)
        logger.info(f"💾 New answer saved to database for question {question_id}")
        
        # Mark question as answered across all questionnaires
        try:
            if update_question_status_across_all_questionnaires:
                updated_count = await update_question_status_across_all_questionnaires(question_id, True, db)
                logger.info(f"✅ Marked question {question_id} as answered in {updated_count} questionnaires")
            else:
                logger.warning(f"⚠️ update_question_status_across_all_questionnaires not available, skipping status update")
        except Exception as e:
            logger.error(f"❌ Error marking question as answered: {e}")
        
        print(f"💾 Answer saved to database for question {question_id}")

        return {
            "success": True,
            "answer": {
                "answer": answer,
                "confidence": confidence,
                "evidence": {
                    "policy_id": str(best_chunk.get('doc_id', '')) if best_chunk else None,
                    "filename": best_doc.get('title', 'Unknown') if best_doc else 'Unknown',
                    "page": actual_page,
                    "quote": quote
                },
                "reasoning": reasoning,
                "source": {
                    "document_name": best_doc.get('title', 'Unknown') if best_doc else 'Unknown',
                    "policy_id": str(best_chunk.get('doc_id', '')) if best_chunk else None,
                    "page_number": actual_page
                },
                "page_number": actual_page,
                "quote": quote
            },
            "from_cache": False
        }
        
    except Exception as e:
        logger.error(f"❌ Error answering audit question: {e}")
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
                "quote": evidence.get("quote", ""),
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


@router.post("/audit-answers/migrate/{questionnaire_id}")
async def migrate_questionnaire_questions(
    questionnaire_id: str,
    db = Depends(get_database)
):
    """Migrate questions from questionnaires collection to audit_questions collection"""
    try:
        logger.info(f"🔄 Migrating questions for questionnaire: {questionnaire_id}")
        
        migrated_count = await migrate_questions_to_audit_collection(questionnaire_id)
        
        return {
            "success": True,
            "message": f"Migrated {migrated_count} questions to audit_questions collection",
            "migrated_count": migrated_count,
            "questionnaire_id": questionnaire_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error migrating questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit-answers/{question_id}/status")
async def get_answer_status(
    question_id: str,
    db = Depends(get_database)
):
    """Check if a question is already answered and get basic answer info"""
    try:
        # Get the answer
        answer = await db.answers.find_one({"question_id": question_id})
        
        if not answer:
            return {
                "question_id": question_id,
                "is_answered": False,
                "message": "Question not yet answered"
            }
        
        return {
            "question_id": question_id,
            "is_answered": True,
            "answer": answer.get("answer", ""),
            "confidence": answer.get("confidence", 0),
            "created_at": answer.get("created_at"),
            "message": "Question already answered - existing answer preserved"
        }
        
    except Exception as e:
        logger.error(f"❌ Error checking answer status: {e}")
        raise HTTPException(status_code=500, detail=str(e))