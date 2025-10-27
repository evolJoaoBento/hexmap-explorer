#!/usr/bin/env python3
import requests
import json

def test_endpoint():
    try:
        response = requests.get('http://localhost:5000/api/list_sessions')
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        try:
            print(f"Response: {response.json()}")
        except:
            print(f"Response text: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_endpoint()