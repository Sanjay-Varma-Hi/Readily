import logging
import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

def process_evidence_chunks(
    question_id: str, 
    candidates: List[Dict[str, Any]], 
    requirement: str = ""
) -> Dict[str, Any]:
    """
    Post-process candidate chunks to select and clean evidence
    
    Args:
        question_id: Question ID for tracking
        candidates: List of candidate chunks from vector search
        requirement: Original requirement text for relevance scoring
    
    Returns:
        Dict containing question_id and refined evidence blocks
    """
    try:
        logger.info(f"🔍 Processing evidence for question {question_id} with {len(candidates)} candidates")
        
        # Step 1: Filter out low similarity chunks (score < 0.5)
        filtered_candidates = [
            candidate for candidate in candidates 
            if candidate.get("score", 0) >= 0.5
        ]
        
        if not filtered_candidates:
            logger.warning(f"⚠️ No candidates with score >= 0.5 for question {question_id}")
            return {
                "question_id": question_id,
                "evidence": []
            }
        
        # Step 2: Process each candidate to extract relevant sentences
        processed_evidence = []
        
        for candidate in filtered_candidates:
            evidence_block = _extract_relevant_sentences(candidate, requirement)
            if evidence_block:
                processed_evidence.append(evidence_block)
        
        # Step 3: Sort by relevance and select top 1-3 strongest evidence blocks
        processed_evidence.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        top_evidence = processed_evidence[:3]  # Top 1-3 strongest
        
        # Step 4: Clean up the evidence (remove relevance_score from final output)
        final_evidence = []
        for evidence in top_evidence:
            clean_evidence = {
                "policy_id": evidence.get("policy_id"),
                "filename": evidence.get("filename"),
                "page": evidence.get("page"),
                "quote": evidence.get("quote")
            }
            final_evidence.append(clean_evidence)
        
        result = {
            "question_id": question_id,
            "evidence": final_evidence
        }
        
        logger.info(f"✅ Processed evidence: {len(final_evidence)} evidence blocks selected")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing evidence chunks: {e}")
        return {
            "question_id": question_id,
            "evidence": []
        }

def _extract_relevant_sentences(candidate: Dict[str, Any], requirement: str) -> Optional[Dict[str, Any]]:
    """
    Extract the most relevant sentence(s) from a candidate chunk
    
    Args:
        candidate: Candidate chunk with text, policy_id, filename, page, score
        requirement: Original requirement text for relevance scoring
    
    Returns:
        Evidence block with most relevant sentence(s) or None if no relevant content
    """
    try:
        text = candidate.get("text", "")
        if not text:
            return None
        
        # Step 1: Break text into sentences
        sentences = _split_into_sentences(text)
        if not sentences:
            return None
        
        # Step 2: Score each sentence for relevance
        scored_sentences = []
        for sentence in sentences:
            relevance_score = _calculate_sentence_relevance(sentence, requirement)
            scored_sentences.append({
                "sentence": sentence,
                "relevance_score": relevance_score
            })
        
        # Step 3: Select the most relevant sentence(s)
        scored_sentences.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Take the top sentence if it has good relevance, otherwise take top 2-3
        best_sentence = scored_sentences[0]
        if best_sentence["relevance_score"] >= 0.3:
            selected_sentences = [best_sentence]
        else:
            # Take top 2-3 sentences if no single sentence is highly relevant
            selected_sentences = scored_sentences[:min(3, len(scored_sentences))]
        
        # Step 4: Combine selected sentences into quote
        quote = " ".join([s["sentence"] for s in selected_sentences])
        
        # Step 5: Calculate overall relevance score for this evidence block
        overall_relevance = max([s["relevance_score"] for s in selected_sentences])
        
        # Only return if relevance is above threshold
        if overall_relevance < 0.05:
            return None
        
        evidence_block = {
            "policy_id": candidate.get("policy_id", "unknown"),
            "filename": candidate.get("filename", "unknown"),
            "page": candidate.get("page", 1),
            "quote": quote,
            "relevance_score": overall_relevance
        }
        
        return evidence_block
        
    except Exception as e:
        logger.error(f"❌ Error extracting relevant sentences: {e}")
        return None

def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex patterns
    """
    try:
        # Enhanced sentence splitting regex
        # Handles common sentence endings and abbreviations
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$'
        
        # Split by sentence boundaries
        sentences = re.split(sentence_pattern, text)
        
        # Clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter out very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
        
    except Exception as e:
        logger.error(f"❌ Error splitting sentences: {e}")
        return [text]  # Fallback to original text

def _calculate_sentence_relevance(sentence: str, requirement: str) -> float:
    """
    Calculate relevance score for a sentence against the requirement
    
    Args:
        sentence: The sentence to score
        requirement: The original requirement text
    
    Returns:
        Relevance score between 0.0 and 1.0
    """
    try:
        if not sentence or not requirement:
            return 0.0
        
        # Normalize text for comparison
        sentence_lower = sentence.lower().strip()
        requirement_lower = requirement.lower().strip()
        
        # Method 1: Keyword overlap
        sentence_words = set(re.findall(r'\b\w+\b', sentence_lower))
        requirement_words = set(re.findall(r'\b\w+\b', requirement_lower))
        
        if not requirement_words:
            return 0.0
        
        keyword_overlap = len(sentence_words.intersection(requirement_words)) / len(requirement_words)
        
        # Method 2: Sequence similarity
        sequence_similarity = SequenceMatcher(None, sentence_lower, requirement_lower).ratio()
        
        # Method 3: Key phrase matching (for audit-specific terms)
        key_phrases = [
            "calendar days", "business days", "within", "no later than", "deadline",
            "timeframe", "period", "response", "request", "retrospective", "prospective",
            "authorization", "approval", "denial", "decision", "process", "procedure",
            "abuse", "fraud", "waste", "fiscal", "business", "medical", "standards",
            "practices", "inconsistent", "sound", "unnecessary", "cost", "medi-cal"
        ]
        
        phrase_bonus = 0.0
        for phrase in key_phrases:
            if phrase in sentence_lower and phrase in requirement_lower:
                phrase_bonus += 0.1
        
        # Method 4: Number/date matching (important for audit requirements)
        number_pattern = r'\b\d+\b'
        sentence_numbers = set(re.findall(number_pattern, sentence))
        requirement_numbers = set(re.findall(number_pattern, requirement))
        
        number_bonus = 0.0
        if requirement_numbers and sentence_numbers:
            number_overlap = len(sentence_numbers.intersection(requirement_numbers))
            number_bonus = min(number_overlap * 0.2, 0.4)
        
        # Combine scores with weights
        relevance_score = (
            keyword_overlap * 0.4 +
            sequence_similarity * 0.3 +
            phrase_bonus +
            number_bonus
        )
        
        # Cap at 1.0
        return min(relevance_score, 1.0)
        
    except Exception as e:
        logger.error(f"❌ Error calculating sentence relevance: {e}")
        return 0.0

def _clean_quote(quote: str) -> str:
    """
    Clean up the quote text for better presentation
    """
    try:
        # Remove extra whitespace
        quote = re.sub(r'\s+', ' ', quote.strip())
        
        # Ensure proper sentence ending
        if quote and not quote.endswith(('.', '!', '?')):
            quote += '.'
        
        return quote
        
    except Exception as e:
        logger.error(f"❌ Error cleaning quote: {e}")
        return quote
