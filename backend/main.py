from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

from api import policies, questionnaires, answers, summaries, chunking, audit_answers

# Load environment variables
load_dotenv("../env/example.env")

app = FastAPI(
    title="READILY - Policy Document Analysis",
    description="Simple policy document analysis system with MongoDB",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(policies.router, prefix="/api", tags=["policies"])
app.include_router(questionnaires.router, prefix="/api", tags=["questionnaires"])
app.include_router(answers.router, prefix="/api", tags=["answers"])
app.include_router(summaries.router, prefix="/api", tags=["summaries"])
app.include_router(chunking.router, prefix="/api", tags=["chunking"])
app.include_router(audit_answers.router, prefix="/api", tags=["audit-answers"])

# Serve static files (only if directory exists)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("✅ Application startup completed")

@app.get("/")
async def root():
    return {"message": "READILY - Policy Document Analysis API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)