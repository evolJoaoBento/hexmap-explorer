"""
Test script for Dice Roll API
Tests both integrated and standalone server functionality
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Main server
STANDALONE_URL = "http://localhost:5001"  # Standalone dice server
USE_STANDALONE = False  # Set to True to test standalone server

# Select the appropriate base URL
API_BASE = STANDALONE_URL if USE_STANDALONE else BASE_URL
DICE_API = f"{API_BASE}/api/dice"

# Test JWT token (you'll need to get this from authentication)
TEST_TOKEN = None  # Set this if you have a valid token

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name, success, details=""):
    """Print test result with color"""
    status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"    {details}")

def test_health():
    """Test health check endpoint"""
    try:
        response = requests.get(f"{DICE_API}/health")
        success = response.status_code == 200
        data = response.json()
        print_test("Health Check", success, f"Status: {data.get('status', 'unknown')}")
        return success
    except Exception as e:
        print_test("Health Check", False, str(e))
        return False

def test_simple_roll():
    """Test simple dice roll"""
    try:
        payload = {
            "expression": "3d6+2",
            "description": "Test roll"
        }
        headers = {"Content-Type": "application/json"}
        if TEST_TOKEN:
            headers["Authorization"] = f"Bearer {TEST_TOKEN}"

        response = requests.post(f"{DICE_API}/roll", json=payload, headers=headers)
        success = response.status_code == 200
        data = response.json()

        if success:
            details = f"Rolled {data['total']}: {data['breakdown']}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"

        print_test("Simple Roll (3d6+2)", success, details)
        return success
    except Exception as e:
        print_test("Simple Roll", False, str(e))
        return False

def test_advantage_roll():
    """Test advantage roll"""
    try:
        payload = {
            "expression": "d20",
            "advantage": True,
            "description": "Advantage test"
        }
        response = requests.post(f"{DICE_API}/roll", json=payload)
        success = response.status_code == 200
        data = response.json()

        if success:
            details = f"Rolled {data['total']}: {data['breakdown']}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"

        print_test("Advantage Roll", success, details)
        return success
    except Exception as e:
        print_test("Advantage Roll", False, str(e))
        return False

def test_bulk_roll():
    """Test bulk rolling"""
    try:
        payload = {
            "expression": "d20",
            "count": 5,
            "description": "Bulk roll test"
        }
        response = requests.post(f"{DICE_API}/roll/bulk", json=payload)
        success = response.status_code == 200
        data = response.json()

        if success:
            summary = data.get('summary', {})
            details = f"Avg: {summary.get('average', 0):.1f}, Min: {summary.get('min', 0)}, Max: {summary.get('max', 0)}"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"

        print_test("Bulk Roll (5xd20)", success, details)
        return success
    except Exception as e:
        print_test("Bulk Roll", False, str(e))
        return False

def test_complex_expression():
    """Test complex dice expression"""
    try:
        expressions = [
            "4d6kh3",  # Keep highest 3
            "2d20kl1",  # Keep lowest 1 (disadvantage)
            "3d6!",    # Exploding dice
            "4d6r1",   # Reroll 1s
            "2d8+1d6+5"  # Multiple dice types
        ]

        all_success = True
        for expr in expressions:
            response = requests.post(f"{DICE_API}/roll", json={"expression": expr})
            if response.status_code == 200:
                data = response.json()
                print_test(f"Complex: {expr}", True, f"Result: {data['total']}")
            else:
                print_test(f"Complex: {expr}", False, response.text)
                all_success = False

        return all_success
    except Exception as e:
        print_test("Complex Expressions", False, str(e))
        return False

def test_parse_expression():
    """Test expression parsing without rolling"""
    try:
        payload = {"expression": "3d6+2d8+5"}
        response = requests.post(f"{DICE_API}/parse", json=payload)
        success = response.status_code == 200
        data = response.json()

        if success and data.get('is_valid'):
            dice_count = len(data.get('dice', []))
            mod_count = len(data.get('modifiers', []))
            details = f"Parsed: {dice_count} dice types, {mod_count} modifiers"
        else:
            details = "Invalid expression"

        print_test("Parse Expression", success, details)
        return success
    except Exception as e:
        print_test("Parse Expression", False, str(e))
        return False

def test_invalid_expression():
    """Test that invalid expressions are rejected"""
    try:
        invalid_expressions = [
            "",           # Empty
            "invalid",    # No dice
            "0d6",        # Zero dice
            "3dd6",       # Double 'd'
            "d0",         # Zero sides
            "999999d999999"  # Too large
        ]

        all_handled = True
        for expr in invalid_expressions:
            response = requests.post(f"{DICE_API}/roll", json={"expression": expr})
            # Should return 400 for invalid expressions
            if response.status_code == 400:
                print(f"    {GREEN}✓{RESET} Correctly rejected: '{expr}'")
            else:
                print(f"    {RED}✗{RESET} Failed to reject: '{expr}' (status: {response.status_code})")
                all_handled = False

        print_test("Invalid Expression Handling", all_handled)
        return all_handled
    except Exception as e:
        print_test("Invalid Expression Handling", False, str(e))
        return False

def test_history():
    """Test roll history endpoint"""
    try:
        params = {"limit": 5}
        headers = {}
        if TEST_TOKEN:
            headers["Authorization"] = f"Bearer {TEST_TOKEN}"

        response = requests.get(f"{DICE_API}/history", params=params, headers=headers)
        success = response.status_code == 200
        data = response.json()

        if success:
            count = data.get('count', 0)
            details = f"Retrieved {count} rolls"
        else:
            details = f"Error: {data.get('error', 'Unknown error')}"

        print_test("Roll History", success, details)
        return success
    except Exception as e:
        print_test("Roll History", False, str(e))
        return False

def test_templates():
    """Test template endpoints (requires authentication)"""
    if not TEST_TOKEN:
        print_test("Templates", False, "Skipped - No authentication token")
        return True  # Don't count as failure

    try:
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

        # Get templates
        response = requests.get(f"{DICE_API}/templates", headers=headers)
        success = response.status_code == 200

        if success:
            data = response.json()
            count = len(data.get('templates', []))
            details = f"Found {count} templates"
        else:
            details = f"Error: {response.status_code}"

        print_test("Get Templates", success, details)
        return success
    except Exception as e:
        print_test("Templates", False, str(e))
        return False

def test_rate_limiting():
    """Test that rate limiting is working"""
    try:
        print(f"\n{BLUE}Testing rate limiting (may take a moment)...{RESET}")

        # Make rapid requests
        request_count = 0
        rate_limited = False

        for i in range(150):  # Try to exceed rate limit
            response = requests.post(f"{DICE_API}/roll", json={"expression": "d20"})
            request_count += 1

            if response.status_code == 429:
                rate_limited = True
                break

            if i % 25 == 0:
                print(f"    Made {i+1} requests...")

        if rate_limited:
            print_test("Rate Limiting", True, f"Rate limited after {request_count} requests")
        else:
            print_test("Rate Limiting", False, f"No rate limit hit after {request_count} requests")

        return rate_limited
    except Exception as e:
        print_test("Rate Limiting", False, str(e))
        return False

def run_all_tests():
    """Run all tests"""
    print(f"\n{BLUE}{'='*50}{RESET}")
    print(f"{BLUE}Dice Roll API Test Suite{RESET}")
    print(f"{BLUE}{'='*50}{RESET}")
    print(f"Testing: {API_BASE}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    tests = [
        ("Health Check", test_health),
        ("Simple Roll", test_simple_roll),
        ("Advantage Roll", test_advantage_roll),
        ("Bulk Roll", test_bulk_roll),
        ("Complex Expressions", test_complex_expression),
        ("Parse Expression", test_parse_expression),
        ("Invalid Expressions", test_invalid_expression),
        ("Roll History", test_history),
        ("Templates", test_templates),
        # ("Rate Limiting", test_rate_limiting),  # Commented out by default (slow)
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{YELLOW}Testing: {name}{RESET}")
        result = test_func()
        results.append(result)
        time.sleep(0.1)  # Small delay between tests

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{BLUE}{'='*50}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*50}{RESET}")

    if passed == total:
        print(f"{GREEN}All tests passed! ({passed}/{total}){RESET}")
    else:
        print(f"{YELLOW}Passed: {passed}/{total}{RESET}")
        print(f"{RED}Failed: {total - passed}/{total}{RESET}")

    return passed == total

def interactive_test():
    """Interactive dice rolling session"""
    print(f"\n{BLUE}Interactive Dice Roll Test{RESET}")
    print("Enter dice expressions to roll (or 'quit' to exit)")
    print("Examples: d20, 3d6+2, 4d6kh3, 2d20kh1 (advantage)\n")

    while True:
        try:
            expr = input(f"{YELLOW}Roll > {RESET}").strip()

            if expr.lower() in ['quit', 'exit', 'q']:
                break

            if not expr:
                continue

            response = requests.post(f"{DICE_API}/roll", json={"expression": expr})

            if response.status_code == 200:
                data = response.json()
                print(f"{GREEN}Result: {data['total']}{RESET}")
                print(f"Breakdown: {data['breakdown']}")
                if data.get('is_critical'):
                    print(f"{GREEN}CRITICAL HIT!{RESET}")
                if data.get('is_fumble'):
                    print(f"{RED}FUMBLE!{RESET}")
            else:
                error_data = response.json()
                print(f"{RED}Error: {error_data.get('error', 'Unknown error')}{RESET}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")

    print(f"\n{BLUE}Thanks for testing!{RESET}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--standalone":
            USE_STANDALONE = True
            print(f"{YELLOW}Testing standalone server at {STANDALONE_URL}{RESET}")
        elif sys.argv[1] == "--interactive":
            interactive_test()
            sys.exit(0)
        elif sys.argv[1] == "--help":
            print("Usage: python test_dice_api.py [options]")
            print("Options:")
            print("  --standalone    Test standalone dice server (port 5001)")
            print("  --interactive   Interactive dice rolling session")
            print("  --help         Show this help message")
            sys.exit(0)

    success = run_all_tests()
    sys.exit(0 if success else 1)