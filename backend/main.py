from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
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
    print("✅ Application startup completed")

@app.get("/")
async def root():
    return {"message": "READILY - Policy Document Analysis API", "status": "running"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

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
        
        # Check if we got a MockDatabase (connection failed)
        if hasattr(db, 'error_message'):
            logger.error(f"Database connection failed: {db.error_message}")
            raise HTTPException(status_code=500, detail=f"Database connection failed: {db.error_message}")
        
        # Test both client and database
        await db.client.admin.command("ping")
        await db.db.command("ping")
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/env")
async def debug_environment():
    """Debug environment variables (without exposing sensitive data)"""
    try:
        import os
        env_vars = {
            "MONGODB_URI": "***" if os.getenv("MONGODB_URI") else "Not set",
            "DB_NAME": os.getenv("DB_NAME", "Not set"),
            "RENDER": os.getenv("RENDER", "Not set"),
            "PORT": os.getenv("PORT", "Not set"),
            "NODE_ENV": os.getenv("NODE_ENV", "Not set"),
        }
        
        # Check MongoDB URI format
        mongodb_uri = os.getenv("MONGODB_URI")
        if mongodb_uri:
            uri_parts = mongodb_uri.split('@')
            if len(uri_parts) > 1:
                host_part = uri_parts[1].split('/')[0]
                env_vars["MONGODB_HOST"] = host_part
            else:
                env_vars["MONGODB_URI_FORMAT"] = "Invalid format"
        
        return {
            "environment": env_vars,
            "python_version": os.sys.version,
            "platform": os.name
        }
    except Exception as e:
        logger.error(f"Debug environment failed: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for Render compatibility, fallback to 8000 for local development
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)