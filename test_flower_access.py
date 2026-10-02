#!/usr/bin/env python
"""
Script to test Flower access.
"""
import requests
import time

def test_flower():
    """Test Flower access."""
    urls = [
        'http://localhost:5555/',
        'http://localhost:5555/flower',
        'http://localhost:5555/tasks',
        'http://localhost:5555/workers'
    ]
    
    auth_options = [
        None,  # No auth
        ('admin', 'admin123'),  # Basic auth
        ('admin', '123456'),  # Alternate password
    ]
    
    print("=== Testing Flower Access ===")
    
    for url in urls:
        print(f"\nTesting URL: {url}")
        
        for auth in auth_options:
            try:
                if auth:
                    response = requests.get(url, auth=auth, timeout=5)
                    print(f"  Auth {auth}: status code {response.status_code}")
                    if response.status_code == 200:
                        print(f"  Success! Content length: {len(response.text)}")
                        if 'Flower' in response.text or 'Celery' in response.text:
                            print(f"  Found Flower content!")
                            return True
                else:
                    response = requests.get(url, timeout=5)
                    print(f"  No auth: status code {response.status_code}")
                    if response.status_code == 200:
                        print(f"  Success! Content length: {len(response.text)}")
                        if 'Flower' in response.text or 'Celery' in response.text:
                            print(f"  Found Flower content!")
                            return True
            except Exception as e:
                print(f"  Auth {auth}: error - {e}")
    
    print("\nAll access methods failed")
    return False

if __name__ == "__main__":
    test_flower()
