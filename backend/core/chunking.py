import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Simple text chunking function
    """
    try:
        # Split text into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            # If adding this sentence would exceed max size, save current chunk
            if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "chunk_id": f"chunk_{chunk_id}",
                    "length": len(current_chunk)
                })
                chunk_id += 1
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_id": f"chunk_{chunk_id}",
                "length": len(current_chunk)
            })
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
        
    except Exception as e:
        logger.error(f"Error chunking text: {e}")
        return [{
            "text": text[:max_chunk_size],
            "chunk_id": "chunk_0",
            "length": len(text[:max_chunk_size])
        }]
