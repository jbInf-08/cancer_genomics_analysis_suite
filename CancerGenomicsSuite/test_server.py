#!/usr/bin/env python3
"""Quick test script to verify the server is responding."""
import time
import requests

# Wait for server to start
print("Waiting for server to start...")
time.sleep(8)

try:
    # Test root route
    print("\nTesting root route (/)...")
    response = requests.get("http://localhost:8050/", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("SUCCESS: Root route is working!")
        print(f"Content length: {len(response.text)} characters")
    else:
        print(f"ERROR: Root route returned {response.status_code}")
        print(f"Response: {response.text[:500]}")
except requests.exceptions.RequestException as e:
    print(f"ERROR: Error accessing root route: {e}")

try:
    # Test test route
    print("\nTesting test route (/test)...")
    response = requests.get("http://localhost:8050/test", timeout=5)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("SUCCESS: Test route is working!")
        print(f"Response: {response.json()}")
    else:
        print(f"ERROR: Test route returned {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"ERROR: Error accessing test route: {e}")

print("\nTest complete!")

