"""
Test script for Plugin API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:5000"
session = requests.Session()

def test_health_check():
    """Test the health check endpoint"""
    response = session.get(f"{BASE_URL}/api/plugin/health")
    print("Health Check:", response.json())
    return response.status_code == 200

def test_new_game():
    """Test creating a new game"""
    data = {"map_name": "test_map", "seed": 12345}
    response = session.post(f"{BASE_URL}/api/plugin/new_game", json=data)
    result = response.json()
    print("New Game:", result)
    return result.get('success', False)

def test_get_map():
    """Test getting map data"""
    response = session.get(f"{BASE_URL}/api/plugin/get_map")
    result = response.json()
    print("Get Map:", result)
    return result.get('success', False)

def test_move():
    """Test moving in a direction"""
    data = {"direction": "n"}
    response = session.post(f"{BASE_URL}/api/plugin/move", json=data)
    result = response.json()
    print("Move North:", result)
    return result.get('success', False)

def test_generate_description():
    """Test generating hex description"""
    data = {"x": 0, "y": 0}
    response = session.post(f"{BASE_URL}/api/plugin/generate_description", json=data)
    result = response.json()
    print("Generate Description:", result)
    return result.get('success', False)

def run_all_tests():
    """Run all API tests"""
    print("=== Testing Plugin API Endpoints ===")
    
    tests = [
        ("Health Check", test_health_check),
        ("New Game", test_new_game),
        ("Get Map", test_get_map),
        ("Move", test_move),
        ("Generate Description", test_generate_description)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
            status = "✅ PASS" if results[test_name] else "❌ FAIL"
            print(f"{status} - {test_name}")
        except Exception as e:
            results[test_name] = False
            print(f"❌ ERROR - {test_name}: {str(e)}")
        print()
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    print(f"\n=== SUMMARY: {passed}/{total} tests passed ===")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()