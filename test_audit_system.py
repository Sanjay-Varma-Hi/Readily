#!/usr/bin/env python3
"""
Test script for the audit question answering system
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from core.audit_answering import answer_audit_question

async def test_audit_system():
    """Test the audit question answering system"""
    
    print("🧪 Testing Audit Question Answering System")
    print("=" * 50)
    
    # Test question
    test_question = "Does the P&P state the MCP must respond to retrospective requests no longer than 14 calendar days from receipt?"
    
    print(f"📝 Test Question: {test_question}")
    print("\n🔍 Processing...")
    
    try:
        # Answer the question
        result = await answer_audit_question(test_question, "test_question_1")
        
        print("\n✅ Result:")
        print(f"Requirement: {result.get('requirement', 'N/A')}")
        print(f"Evidence: {result.get('evidence', 'N/A')}")
        print(f"Answer: {result.get('answer', 'N/A')}")
        print(f"Quote: {result.get('quote', 'N/A')}")
        print(f"Confidence: {result.get('confidence', 0.0)}")
        
        if result.get('error'):
            print(f"❌ Error: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error testing audit system: {e}")
        return False
    
    print("\n🎉 Test completed successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_audit_system())
