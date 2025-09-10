import logging
import re
from typing import List, Dict, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

def rerank_chunks(question: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    Rerank chunks based on multiple scoring factors
    """
    try:
        if not candidates:
            return []
        
        # Calculate additional scores for each candidate
        for candidate in candidates:
            candidate["rerank_score"] = calculate_rerank_score(question, candidate)
        
        # Sort by rerank score
        reranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        return reranked[:top_k]
        
    except Exception as e:
        logger.error(f"Error reranking chunks: {e}")
        return candidates[:top_k]

def calculate_rerank_score(question: str, candidate: Dict[str, Any]) -> float:
    """
    Calculate a comprehensive rerank score for a candidate
    """
    try:
        score = 0.0
        
        # Base similarity score (if available)
        similarity_score = candidate.get("similarity_score", 0.0)
        score += similarity_score * 0.4
        
        # Text similarity with question
        text = candidate.get("text", "")
        text_similarity = calculate_text_similarity(question, text)
        score += text_similarity * 0.3
        
        # Keyword matching
        keyword_score = calculate_keyword_score(question, text)
        score += keyword_score * 0.2
        
        # Metadata relevance
        metadata_score = calculate_metadata_score(candidate)
        score += metadata_score * 0.1
        
        return score
        
    except Exception as e:
        logger.error(f"Error calculating rerank score: {e}")
        return 0.0

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity using sequence matching
    """
    try:
        if not text1 or not text2:
            return 0.0
        
        # Normalize text
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        return similarity
        
    except Exception as e:
        logger.error(f"Error calculating text similarity: {e}")
        return 0.0

def calculate_keyword_score(question: str, text: str) -> float:
    """
    Calculate keyword matching score
    """
    try:
        if not question or not text:
            return 0.0
        
        # Extract keywords from question
        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        text_words = set(re.findall(r'\b\w+\b', text.lower()))
        
        if not question_words:
            return 0.0
        
        # Calculate overlap
        overlap = len(question_words.intersection(text_words))
        return overlap / len(question_words)
        
    except Exception as e:
        logger.error(f"Error calculating keyword score: {e}")
        return 0.0

def calculate_metadata_score(candidate: Dict[str, Any]) -> float:
    """
    Calculate metadata relevance score
    """
    try:
        score = 0.0
        
        # Check for important metadata fields
        if candidate.get("page_number"):
            score += 0.1
        
        if candidate.get("section_title"):
            score += 0.2
        
        if candidate.get("document_type"):
            score += 0.1
        
        return min(score, 1.0)
        
    except Exception as e:
        logger.error(f"Error calculating metadata score: {e}")
        return 0.0

def calculate_confidence(answer: str, sources: List[Dict[str, Any]]) -> float:
    """
    Calculate confidence score for an answer based on sources
    """
    try:
        if not answer or not sources:
            return 0.0
        
        # Base confidence from number of sources
        source_count = len(sources)
        base_confidence = min(source_count / 3.0, 1.0)  # Max at 3 sources
        
        # Boost confidence if answer is detailed
        answer_length = len(answer.split())
        length_boost = min(answer_length / 50.0, 0.3)  # Max 0.3 boost
        
        # Boost confidence if sources have high similarity scores
        avg_similarity = 0.0
        if sources:
            similarities = [s.get("similarity_score", 0.0) for s in sources]
            avg_similarity = sum(similarities) / len(similarities)
        
        similarity_boost = avg_similarity * 0.2
        
        total_confidence = base_confidence + length_boost + similarity_boost
        return min(total_confidence, 1.0)
        
    except Exception as e:
        logger.error(f"Error calculating confidence: {e}")
        return 0.5  # Default moderate confidence
