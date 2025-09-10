#!/usr/bin/env python3
"""
Simple test server to debug the audit system
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
# Answering functionality removed

app = FastAPI(title="Debug Server")

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
    return {"message": "Debug server running"}

@app.post("/api/audit-answers/single")
async def test_audit_endpoint(request: dict):
    return {
        "success": False,
        "message": "Answering functionality has been removed"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
