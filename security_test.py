#!/usr/bin/env python3
"""
Security test script for Hex Explorer
Tests the security fixes implemented after the audit
"""
import requests
import json
import time
from typing import Dict, Any

class SecurityTester:
    def __init__(self, base_url: str = 'http://localhost:5000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results: Dict[str, bool] = {}
    
    def test_unauthenticated_access(self):
        """Test that sensitive endpoints require authentication"""
        print("[LOCK] Testing authentication requirements...")
        
        sensitive_endpoints = [
            '/api/list_sessions',
            '/api/load_map_session/test',
            '/api/get_player_positions/test',
            '/api/update_player_position',
            '/api/update_hex_terrain',
            '/api/force_sync_world',
            '/api/save_map_for_game',
            '/api/generate_description'
        ]
        
        all_protected = True
        for endpoint in sensitive_endpoints:
            try:
                if endpoint in ['/api/update_player_position', '/api/update_hex_terrain', 
                              '/api/force_sync_world', '/api/save_map_for_game', '/api/generate_description']:
                    response = self.session.post(f"{self.base_url}{endpoint}")
                else:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code != 401:
                    print(f"[FAIL] {endpoint} is not properly protected (got {response.status_code})")
                    all_protected = False
                else:
                    print(f"[PASS] {endpoint} requires authentication")
            except Exception as e:
                print(f"⚠️  Error testing {endpoint}: {e}")
                all_protected = False
        
        self.test_results['authentication_protection'] = all_protected
        return all_protected
    
    def test_input_validation(self):
        """Test input validation on endpoints"""
        print("\n📝 Testing input validation...")
        
        # Test invalid JSON
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                data="invalid json",
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code in [400, 422]:
                print("✅ Invalid JSON properly rejected")
                validation_works = True
            else:
                print(f"❌ Invalid JSON not rejected (got {response.status_code})")
                validation_works = False
        except Exception as e:
            print(f"⚠️  Error testing invalid JSON: {e}")
            validation_works = False
        
        # Test malicious input
        malicious_data = {
            "username": "<script>alert('xss')</script>",
            "email": "test@test.com",
            "password": "password123",
            "role": "admin"  # Should be sanitized
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=malicious_data
            )
            # Should either reject or sanitize
            if response.status_code in [400, 422]:
                print("✅ Malicious input properly rejected")
            elif response.status_code == 201:
                # Check if input was sanitized
                data = response.json()
                if '<script>' not in str(data):
                    print("✅ Malicious input properly sanitized")
                else:
                    print("❌ XSS payload not filtered")
                    validation_works = False
        except Exception as e:
            print(f"⚠️  Error testing malicious input: {e}")
            validation_works = False
        
        self.test_results['input_validation'] = validation_works
        return validation_works
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        print("\n⏱️  Testing rate limiting...")
        
        # Test rate limiting on test endpoint
        rate_limited = False
        for i in range(10):
            try:
                response = self.session.get(f"{self.base_url}/api/test")
                if response.status_code == 429:
                    print(f"✅ Rate limiting triggered after {i+1} requests")
                    rate_limited = True
                    break
                time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                print(f"⚠️  Error testing rate limiting: {e}")
                break
        
        if not rate_limited:
            print("❌ Rate limiting not working properly")
        
        self.test_results['rate_limiting'] = rate_limited
        return rate_limited
    
    def test_error_handling(self):
        """Test that errors don't expose sensitive information"""
        print("\n🛡️  Testing error handling...")
        
        # Test 404 handling
        try:
            response = self.session.get(f"{self.base_url}/api/nonexistent")
            if response.status_code == 404:
                data = response.json()
                if 'error' in data and 'traceback' not in str(data).lower():
                    print("✅ 404 errors properly handled")
                    error_handling_secure = True
                else:
                    print("❌ 404 response may expose sensitive info")
                    error_handling_secure = False
            else:
                print(f"⚠️  Unexpected status code for 404 test: {response.status_code}")
                error_handling_secure = False
        except Exception as e:
            print(f"⚠️  Error testing error handling: {e}")
            error_handling_secure = False
        
        self.test_results['error_handling'] = error_handling_secure
        return error_handling_secure
    
    def test_cors_configuration(self):
        """Test CORS configuration"""
        print("\n🌐 Testing CORS configuration...")
        
        # Test preflight request
        try:
            response = self.session.options(
                f"{self.base_url}/api/test",
                headers={
                    'Origin': 'http://malicious-site.com',
                    'Access-Control-Request-Method': 'GET'
                }
            )
            
            # Check if CORS is properly restricted
            cors_header = response.headers.get('Access-Control-Allow-Origin')
            if cors_header == '*':
                print("❌ CORS allows all origins (security risk)")
                cors_secure = False
            elif cors_header is None or 'localhost' in cors_header:
                print("✅ CORS properly restricted")
                cors_secure = True
            else:
                print(f"⚠️  CORS configuration: {cors_header}")
                cors_secure = True
        except Exception as e:
            print(f"⚠️  Error testing CORS: {e}")
            cors_secure = False
        
        self.test_results['cors_security'] = cors_secure
        return cors_secure
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🔍 Starting Security Tests for Hex Explorer")
        print("=" * 50)
        
        tests = [
            self.test_unauthenticated_access,
            self.test_input_validation,
            self.test_rate_limiting,
            self.test_error_handling,
            self.test_cors_configuration
        ]
        
        total_tests = len(tests)
        passed_tests = 0
        
        for test in tests:
            if test():
                passed_tests += 1
        
        print("\n" + "=" * 50)
        print(f"📊 Security Test Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All security tests passed!")
            overall_score = "SECURE"
        elif passed_tests >= total_tests * 0.8:
            print("⚠️  Most security tests passed, but some issues remain")
            overall_score = "MOSTLY SECURE"
        else:
            print("❌ Multiple security issues detected")
            overall_score = "INSECURE"
        
        print(f"🏆 Overall Security Score: {overall_score}")
        
        # Detailed results
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        return self.test_results

def main():
    """Main function to run security tests"""
    print("🚀 Starting Hex Explorer Security Test Suite")
    print("Make sure the application is running on http://localhost:5000")
    
    try:
        # Quick connectivity test
        response = requests.get('http://localhost:5000/api/test', timeout=5)
        print("✅ Application is reachable\n")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to application: {e}")
        print("Please start the application with: python app.py")
        return
    
    tester = SecurityTester()
    results = tester.run_all_tests()
    
    # Return exit code based on results
    if all(results.values()):
        exit(0)  # All tests passed
    else:
        exit(1)  # Some tests failed

if __name__ == '__main__':
    main()