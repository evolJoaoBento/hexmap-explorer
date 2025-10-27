"""
Test script for the Simple Dice Chat System
Tests the new simplified interface and chat functionality
"""

import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:5000"
CHAT_API = f"{BASE_URL}/api/chat"
DICE_API = f"{BASE_URL}/api/dice"

# Test room
TEST_ROOM = "test-room-001"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_test(name, success, details=""):
    """Print test result with color"""
    status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"    {details}")

def test_server_health():
    """Test if server is running and healthy"""
    try:
        response = requests.get(f"{BASE_URL}/")
        success = response.status_code == 200
        print_test("Server Health Check", success, f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test("Server Health Check", False, str(e))
        return False

def test_dice_api():
    """Test basic dice rolling functionality"""
    try:
        # Test simple roll
        response = requests.post(f"{DICE_API}/roll", json={
            "expression": "2d6+3",
            "description": "Test roll"
        })

        success = response.status_code == 200
        if success:
            data = response.json()
            details = f"Rolled {data['total']}: {data['breakdown']}"
        else:
            details = f"Error: {response.status_code}"

        print_test("Basic Dice Roll", success, details)
        return success
    except Exception as e:
        print_test("Basic Dice Roll", False, str(e))
        return False

def test_chat_api():
    """Test chat functionality"""
    try:
        # Join room
        response = requests.post(f"{CHAT_API}/rooms/{TEST_ROOM}/join", json={
            "username": "TestUser",
            "user_role": "player"
        })

        join_success = response.status_code == 200
        print_test("Join Chat Room", join_success)

        if not join_success:
            return False

        # Send message
        response = requests.post(f"{CHAT_API}/rooms/{TEST_ROOM}/messages", json={
            "content": "Test message from API",
            "username": "TestUser",
            "user_role": "player"
        })

        send_success = response.status_code == 201
        print_test("Send Chat Message", send_success)

        # Get messages
        response = requests.get(f"{CHAT_API}/rooms/{TEST_ROOM}/messages?limit=10")
        get_success = response.status_code == 200

        if get_success:
            data = response.json()
            message_count = data.get('count', 0)
            details = f"Retrieved {message_count} messages"
        else:
            details = f"Error: {response.status_code}"

        print_test("Get Chat Messages", get_success, details)

        return join_success and send_success and get_success

    except Exception as e:
        print_test("Chat API Tests", False, str(e))
        return False

def test_dice_expressions():
    """Test various dice expressions"""
    expressions = [
        "d4",
        "2d6",
        "3d8+2",
        "1d20-1",
        "2d4+1d6+3",
        "4d6"  # Ability score roll
    ]

    all_success = True

    for expr in expressions:
        try:
            response = requests.post(f"{DICE_API}/roll", json={
                "expression": expr,
                "description": f"Test {expr}"
            })

            success = response.status_code == 200
            if success:
                data = response.json()
                details = f"{expr} → {data['total']}"
            else:
                details = f"Error: {response.status_code}"

            print_test(f"Dice Expression: {expr}", success, details)
            all_success = all_success and success

            time.sleep(0.1)  # Small delay

        except Exception as e:
            print_test(f"Dice Expression: {expr}", False, str(e))
            all_success = False

    return all_success

def test_static_files():
    """Test if static files are being served"""
    static_files = [
        '/dice-chat',  # Main demo page
        '/dice-chat/simple-dice-chat.css',
        '/dice-chat/simple-dice-chat.js'
    ]

    all_success = True

    for file_path in static_files:
        try:
            response = requests.get(f"{BASE_URL}{file_path}")
            success = response.status_code == 200

            if success:
                size = len(response.content)
                details = f"Served {size} bytes"
            else:
                details = f"Status: {response.status_code}"

            print_test(f"Static File: {file_path}", success, details)
            all_success = all_success and success

        except Exception as e:
            print_test(f"Static File: {file_path}", False, str(e))
            all_success = False

    return all_success

def test_dice_parse_validation():
    """Test dice expression parsing"""
    test_expressions = [
        ("d20", True),
        ("3d6+2", True),
        ("invalid", False),
        ("", False),
        ("999d999", False),  # Should be too large
        ("2d4+1d6+1d8+1d10+1d12+1d20", True)  # Complex but valid
    ]

    all_success = True

    for expr, should_be_valid in test_expressions:
        try:
            response = requests.post(f"{DICE_API}/parse", json={
                "expression": expr
            })

            success = response.status_code == 200
            if success:
                data = response.json()
                is_valid = data.get('is_valid', False)
                test_passed = is_valid == should_be_valid
                details = f"Valid: {is_valid} (expected {should_be_valid})"
            else:
                test_passed = False
                details = f"Error: {response.status_code}"

            print_test(f"Parse '{expr}'", test_passed, details)
            all_success = all_success and test_passed

        except Exception as e:
            print_test(f"Parse '{expr}'", False, str(e))
            all_success = False

    return all_success

def simulate_dm_player_interaction():
    """Simulate a DM-Player dice interaction"""
    try:
        print(f"\n{BLUE}Simulating DM-Player Interaction...{RESET}")

        # DM joins room
        dm_join = requests.post(f"{CHAT_API}/rooms/{TEST_ROOM}/join", json={
            "username": "GameMaster",
            "user_role": "dm"
        })
        print_test("DM joins room", dm_join.status_code == 200)

        # Player joins room
        player_join = requests.post(f"{CHAT_API}/rooms/{TEST_ROOM}/join", json={
            "username": "Aragorn",
            "user_role": "player"
        })
        print_test("Player joins room", player_join.status_code == 200)

        # DM sends context message
        dm_message = requests.post(f"{CHAT_API}/rooms/{TEST_ROOM}/messages", json={
            "content": "🗡️ An orc attacks! Roll for initiative!",
            "username": "GameMaster",
            "user_role": "dm"
        })
        print_test("DM sends context", dm_message.status_code == 201)

        time.sleep(0.2)

        # DM requests dice roll (simulated as message)
        dice_request = requests.post(f"{CHAT_API}/rooms/{TEST_ROOM}/messages", json={
            "content": "🎲 **Dice Request**: Roll 1d20 for initiative",
            "username": "GameMaster",
            "user_role": "dm"
        })
        print_test("DM requests dice roll", dice_request.status_code == 201)

        time.sleep(0.2)

        # Player rolls dice
        roll_response = requests.post(f"{DICE_API}/roll", json={
            "expression": "1d20+2",
            "description": "Initiative roll"
        })

        if roll_response.status_code == 200:
            roll_data = roll_response.json()
            result_total = roll_data['total']

            # Player sends result
            player_result = requests.post(f"{CHAT_API}/rooms/{TEST_ROOM}/messages", json={
                "content": f"🎯 **Rolled {result_total}** for initiative! ({roll_data['breakdown']})",
                "username": "Aragorn",
                "user_role": "player"
            })
            print_test("Player responds with roll", player_result.status_code == 201)

            # Get conversation history
            history = requests.get(f"{CHAT_API}/rooms/{TEST_ROOM}/messages?limit=10")
            if history.status_code == 200:
                messages = history.json().get('messages', [])
                print_test("Retrieved conversation", True, f"Found {len(messages)} messages")

                # Show conversation
                print(f"\n{YELLOW}Conversation History:{RESET}")
                for msg in messages[-4:]:  # Show last 4 messages
                    timestamp = msg.get('timestamp', '')[:8] if msg.get('timestamp') else ''
                    username = msg.get('username', 'Unknown')
                    content = msg.get('content', '')
                    print(f"  [{timestamp}] {username}: {content}")

                return True

        return False

    except Exception as e:
        print_test("DM-Player Interaction", False, str(e))
        return False

def run_all_tests():
    """Run all tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Simple Dice Chat System Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Testing server at: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    tests = [
        ("Server Health", test_server_health),
        ("Basic Dice API", test_dice_api),
        ("Chat API", test_chat_api),
        ("Dice Expressions", test_dice_expressions),
        ("Static Files", test_static_files),
        ("Dice Validation", test_dice_parse_validation),
        ("DM-Player Interaction", simulate_dm_player_interaction)
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{YELLOW}Running: {name}{RESET}")
        result = test_func()
        results.append(result)
        time.sleep(0.2)

    # Summary
    passed = sum(results)
    total = len(results)

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test Results{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    if passed == total:
        print(f"{GREEN}🎉 All tests passed! ({passed}/{total}){RESET}")
        print(f"\n{GREEN}✅ Your simple dice chat system is working perfectly!{RESET}")
        print(f"\n{YELLOW}👉 Open your browser to: {BASE_URL}/dice-chat{RESET}")
        print(f"{YELLOW}   Try connecting as both DM and Player!{RESET}")
    else:
        print(f"{YELLOW}⚠️  Some tests failed: {passed}/{total} passed{RESET}")
        print(f"{RED}❌ Failed: {total - passed}/{total}{RESET}")

    return passed == total

def show_usage():
    """Show how to use the system"""
    print(f"\n{BLUE}📖 How to Use the Simple Dice Chat System:{RESET}")
    print()
    print(f"1. {YELLOW}Start the server:{RESET}")
    print(f"   python app.py")
    print()
    print(f"2. {YELLOW}Open in browser:{RESET}")
    print(f"   {BASE_URL}/dice-chat")
    print()
    print(f"3. {YELLOW}Connect clients:{RESET}")
    print(f"   - Left side: Connect as DM (GameMaster)")
    print(f"   - Right side: Connect as Player (Aragorn)")
    print()
    print(f"4. {YELLOW}Try the features:{RESET}")
    print(f"   - Send chat messages")
    print(f"   - Click '🎲 Request Dice Roll' (DM)")
    print(f"   - Click '🎲 Roll Dice' (Player)")
    print(f"   - Select dice types: d4, d6, d8, d10, d12, d20")
    print(f"   - Add modifiers (+/-)")
    print()
    print(f"5. {YELLOW}Watch the magic:{RESET}")
    print(f"   - Messages appear in real-time")
    print(f"   - Dice results show full breakdown")
    print(f"   - Both clients see the same conversation")

if __name__ == "__main__":
    success = run_all_tests()

    if success:
        show_usage()

    exit(0 if success else 1)