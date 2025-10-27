#!/usr/bin/env python3
"""
Simple security test for Hex Explorer
"""
import requests

def test_authentication():
    """Test that endpoints require authentication"""
    print("Testing authentication requirements...")
    
    endpoints = [
        '/api/list_sessions',
        '/api/load_map_session/test', 
        '/api/get_player_positions/test'
    ]
    
    base_url = 'http://localhost:5000'
    passed = 0
    total = len(endpoints)
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 401:
                print(f"[PASS] {endpoint} requires authentication")
                passed += 1
            else:
                print(f"[FAIL] {endpoint} returned {response.status_code}")
        except Exception as e:
            print(f"[ERROR] {endpoint}: {e}")
    
    return passed, total

def test_rate_limiting():
    """Test rate limiting"""
    print("\nTesting rate limiting...")
    base_url = 'http://localhost:5000'
    
    # Make multiple requests quickly
    for i in range(5):
        try:
            response = requests.get(f"{base_url}/api/test", timeout=2)
            print(f"Request {i+1}: {response.status_code}")
            if response.status_code == 429:
                print("[PASS] Rate limiting is working")
                return True
        except Exception as e:
            print(f"Error: {e}")
            break
    
    print("[INFO] Rate limiting not triggered (may need more requests)")
    return False

def main():
    print("Hex Explorer Security Test")
    print("=" * 40)
    
    # Test connectivity
    try:
        response = requests.get('http://localhost:5000/api/test', timeout=5)
        print(f"[INFO] App is running (status: {response.status_code})")
    except:
        print("[ERROR] Cannot connect to app on localhost:5000")
        return
    
    # Run tests
    auth_passed, auth_total = test_authentication()
    rate_limit_works = test_rate_limiting()
    
    print(f"\nResults:")
    print(f"Authentication: {auth_passed}/{auth_total} passed")
    print(f"Rate limiting: {'Working' if rate_limit_works else 'Not detected'}")
    
    if auth_passed == auth_total:
        print("\n[SUCCESS] Authentication security is working!")
    else:
        print(f"\n[WARNING] {auth_total - auth_passed} authentication issues found")

if __name__ == '__main__':
    main()