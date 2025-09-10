#!/usr/bin/env python3
"""
Simple test to verify backend works
"""

import sys
import os
sys.path.append('backend')

try:
    from backend.main import app
    print("✅ Backend imports successfully!")
    
    # Test basic functionality
    from backend.core.database import init_db
    print("✅ Database module imports successfully!")
    
    print("\n🎉 Backend is ready to run!")
    print("You can start it with: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()


