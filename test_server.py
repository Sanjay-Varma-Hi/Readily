#!/usr/bin/env python3
"""
Simple test server to debug the audit answers endpoint
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Test Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Test server running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/audit-answers/single")
async def test_audit_endpoint(request: dict):
    return {
        "success": True,
        "question_id": request.get("question_id"),
        "answer": {
            "requirement": request.get("question"),
            "evidence": "Test evidence",
            "answer": "YES",
            "quote": "Test quote",
            "confidence": 0.8
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
