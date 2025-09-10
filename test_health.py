#!/usr/bin/env python3
"""
Test script to verify health endpoints and database connectivity
"""
import requests
import json
import time
import sys

# Configuration
BASE_URL = "https://readily-mgtk.onrender.com"
# For local testing, uncomment the line below:
# BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, description):
    """Test a single endpoint"""
    print(f"\n🔍 Testing {description}...")
    print(f"   URL: {BASE_URL}{endpoint}")
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Timeout - endpoint took too long to respond")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection Error - could not connect to server")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints that were previously unreliable"""
    print(f"\n🔍 Testing API endpoints...")
    
    endpoints = [
        ("/api/policies/folders", "Policy Folders"),
        ("/api/questionnaires", "Questionnaires"),
        ("/api/policies", "Policies"),
    ]
    
    results = []
    for endpoint, description in endpoints:
        success = test_endpoint(endpoint, description)
        results.append((description, success))
        time.sleep(1)  # Small delay between requests
    
    return results

def main():
    """Main test function"""
    print("🚀 Starting READILY Health Check Tests")
    print(f"   Target: {BASE_URL}")
    print("=" * 50)
    
    # Test health endpoints
    health_tests = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/healthz", "Kubernetes health check"),
        ("/health/db", "Database health check"),
    ]
    
    print("\n📊 Health Endpoint Tests:")
    health_results = []
    for endpoint, description in health_tests:
        success = test_endpoint(endpoint, description)
        health_results.append((description, success))
        time.sleep(1)
    
    # Test API endpoints
    print("\n📊 API Endpoint Tests:")
    api_results = test_api_endpoints()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    print("\n🏥 Health Endpoints:")
    for description, success in health_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {description}")
    
    print("\n🔌 API Endpoints:")
    for description, success in api_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {description}")
    
    # Overall result
    all_health_passed = all(success for _, success in health_results)
    all_api_passed = all(success for _, success in api_results)
    
    if all_health_passed and all_api_passed:
        print("\n🎉 ALL TESTS PASSED! The system is working reliably.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
