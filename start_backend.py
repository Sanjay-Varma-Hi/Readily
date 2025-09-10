#!/usr/bin/env python3
"""
Startup script for READILY backend
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_requirements():
    """Check if requirements are installed"""
    try:
        import fastapi
        import uvicorn
        import pymongo
        import motor
        import sentence_transformers
        print("✓ All required packages are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("Please install requirements: pip install -r backend/requirements.txt")
        return False

def check_environment():
    """Check environment configuration"""
    env_file = Path("env/example.env")
    if not env_file.exists():
        print("✗ Environment file not found: env/example.env")
        print("Please create the environment file with your configuration")
        return False
    
    print("✓ Environment file found")
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "uploads/policies",
        "uploads/questionnaires",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def start_server():
    """Start the FastAPI server"""
    print("\n🚀 Starting READILY backend server...")
    print("Server will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        # Change to backend directory
        os.chdir("backend")
        
        # Start uvicorn server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
    except Exception as e:
        print(f"✗ Error starting server: {e}")

def main():
    """Main startup function"""
    print("🔧 READILY Backend Startup")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()


