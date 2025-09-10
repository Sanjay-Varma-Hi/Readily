from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from api import policies, questionnaires, answers, summaries, chunking, audit_answers

# Load environment variables
# Try to load from local env file first, then fall back to system env vars
if os.path.exists("../env/example.env"):
    load_dotenv("../env/example.env")
elif os.path.exists("../env/production.env"):
    load_dotenv("../env/production.env")
else:
    # In production (Render), environment variables are set directly
    pass

app = FastAPI(
    title="READILY - Policy Document Analysis",
    description="Simple policy document analysis system with MongoDB",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "https://readily-kappa.vercel.app",  # Vercel frontend
        "https://readily.vercel.app",  # Alternative Vercel domain
        "https://readily-mgtk.onrender.com",  # Render backend (for self-referencing)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
    try:
        # Initialize database connection
        from core.database import get_database
        db = await get_database()
        await db.client.admin.command("ping")
        print("✅ Database connection established")
        print("✅ Application startup completed")
    except Exception as e:
        print(f"⚠️ Database connection failed during startup: {e}")
        print("✅ Application startup completed (will retry on first request)")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown"""
    try:
        from core.database import _client_instance
        if _client_instance:
            _client_instance.close()
            print("✅ Database connection closed")
    except Exception as e:
        print(f"⚠️ Error closing database connection: {e}")
    print("✅ Application shutdown completed")

@app.get("/")
async def root():
    return {"message": "READILY - Policy Document Analysis API", "status": "running"}

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        from core.database import get_database
        db = await get_database()
        
        # Test database connection
        await asyncio.wait_for(db.client.admin.command("ping"), timeout=3.0)
        
        # Get basic stats
        doc_count = await db.documents.count_documents({})
        questionnaire_count = await db.questionnaires.count_documents({})
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": "connected",
            "stats": {
                "documents": doc_count,
                "questionnaires": questionnaire_count
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }

@app.get("/healthz")
async def healthz():
    """Kubernetes-style health check endpoint for Render"""
    return {"status": "ok"}

@app.head("/")
async def head_root():
    """Handle HEAD requests for health checks"""
    return {"message": "OK"}

@app.head("/health")
async def head_health():
    """Handle HEAD requests to health endpoint"""
    return {"status": "healthy"}

@app.get("/health/db")
async def database_health_check():
    """Check database connection - returns 500 if DB ping fails"""
    try:
        from core.database import get_database
        db = await get_database()
        
        # Test connection with timeout
        await asyncio.wait_for(db.client.admin.command("ping"), timeout=5.0)
        
        # Test a simple query to ensure database is responsive
        await asyncio.wait_for(db.documents.count_documents({}), timeout=5.0)
        
        return {
            "ok": True, 
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": "connected"
        }
    except asyncio.TimeoutError:
        logger.error("Database health check timed out")
        raise HTTPException(status_code=503, detail="Database connection timeout")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for Render compatibility, fallback to 8000 for local development
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)