#!/usr/bin/env python3
"""
Test Authentication Routes

This script demonstrates the simplified authentication routes
for the Cancer Genomics Analysis Suite.
"""

import requests
import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_auth_routes():
    """Test the authentication routes."""
    
    base_url = "http://localhost:8050/auth"
    
    print("🔐 Testing Authentication Routes")
    print("=" * 50)
    
    # Test 1: Check authentication status
    print("\n1. Testing authentication status...")
    try:
        response = requests.get(f"{base_url}/status")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Could not connect to server. Make sure Flask app is running.")
        print("   Run: python run_flask_app.py")
        return
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Register a new user
    print("\n2. Testing user registration...")
    register_data = {
        "username": "testuser",
        "password": "TestPass123!",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    }
    
    try:
        response = requests.post(
            f"{base_url}/register",
            json=register_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Try to register the same user again (should fail)
    print("\n3. Testing duplicate user registration...")
    try:
        response = requests.post(
            f"{base_url}/register",
            json=register_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Login with correct credentials
    print("\n4. Testing login with correct credentials...")
    login_data = {
        "username": "testuser",
        "password": "TestPass123!"
    }
    
    try:
        response = requests.post(
            f"{base_url}/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Login with incorrect credentials
    print("\n5. Testing login with incorrect credentials...")
    wrong_login_data = {
        "username": "testuser",
        "password": "WrongPassword"
    }
    
    try:
        response = requests.post(
            f"{base_url}/login",
            json=wrong_login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 6: Login with non-existent user
    print("\n6. Testing login with non-existent user...")
    nonexistent_login_data = {
        "username": "nonexistent",
        "password": "SomePassword"
    }
    
    try:
        response = requests.post(
            f"{base_url}/login",
            json=nonexistent_login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 7: Logout
    print("\n7. Testing logout...")
    try:
        response = requests.post(
            f"{base_url}/logout",
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 8: Test with missing data
    print("\n8. Testing registration with missing data...")
    incomplete_data = {
        "username": "incomplete"
        # Missing password
    }
    
    try:
        response = requests.post(
            f"{base_url}/register",
            json=incomplete_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Authentication routes testing completed!")
    print("\nTo run these tests:")
    print("1. Start the Flask app: python run_flask_app.py")
    print("2. Run this test: python test_auth_routes.py")

def show_curl_examples():
    """Show curl examples for testing the API."""
    
    print("\n📋 cURL Examples for Testing:")
    print("=" * 50)
    
    print("\n1. Check authentication status:")
    print("curl -X GET http://localhost:8050/auth/status")
    
    print("\n2. Register a new user:")
    print('curl -X POST http://localhost:8050/auth/register \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"username": "newuser", "password": "SecurePass123!", "email": "newuser@example.com"}\'')
    
    print("\n3. Login:")
    print('curl -X POST http://localhost:8050/auth/login \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"username": "newuser", "password": "SecurePass123!"}\'')
    
    print("\n4. Logout:")
    print("curl -X POST http://localhost:8050/auth/logout")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--curl":
        show_curl_examples()
    else:
        test_auth_routes()
        show_curl_examples()
