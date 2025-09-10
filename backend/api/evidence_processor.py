from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from core.evidence_processor import process_evidence_chunks
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class EvidenceProcessingRequest(BaseModel):
    question_id: str
    candidates: List[Dict[str, Any]]
    requirement: str = ""

@router.post("/evidence-processor/process", response_model=Dict[str, Any])
async def process_evidence(request: EvidenceProcessingRequest):
    """Process candidate chunks to select and clean evidence"""
    try:
        logger.info(f"🔍 Processing evidence for question: {request.question_id}")
        
        # Validate input
        if not request.candidates:
            raise HTTPException(status_code=400, detail="Candidates list cannot be empty")
        
        if not request.question_id:
            raise HTTPException(status_code=400, detail="Question ID is required")
        
        result = process_evidence_chunks(
            question_id=request.question_id,
            candidates=request.candidates,
            requirement=request.requirement
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evidence-processor/test", response_model=Dict[str, Any])
async def test_evidence_processing():
    """Test endpoint with sample data"""
    try:
        # Sample test data
        test_candidates = [
            {
                "policy_id": "GG.1508",
                "filename": "Authorization and Processing of Referrals Revised",
                "page": 10,
                "text": "For a retrospective request involving direct payment to the Member, CalOptima Health shall complete the CD, notify the Member or Member's Authorized Representative and the Prescriber, and effectuate the decision, if applicable, no later than fourteen (14) calendar days after the date and time CalOptima Health received the request.",
                "score": 0.89
            },
            {
                "policy_id": "AA.1204",
                "filename": "Gifts, Honoraria, and Travel Payments",
                "page": 3,
                "text": "Employees may not accept honoraria in connection with CalOptima responsibilities.",
                "score": 0.52
            }
        ]
        
        test_requirement = "Does the P&P state the MCP must respond to retrospective requests no longer than 14 calendar days from receipt?"
        
        result = process_evidence_chunks(
            question_id="123",
            candidates=test_candidates,
            requirement=test_requirement
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in test evidence processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
