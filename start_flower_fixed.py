#!/usr/bin/env python
"""
Fixed Flower startup script.
"""
import subprocess
import sys
import os
import time

PYTHON = sys.executable

def start_flower():
    """Start Flower monitoring with correct parameters."""
    print("Starting Flower monitoring...")
    
    # Method 1: start flower via celery command
    try:
        cmd = [
            PYTHON, '-m', 'celery',
            '-A', 'tasks.simple_test', 'flower',
            '--port=5555',
            '--address=0.0.0.0',
            '--basic_auth=admin:admin123'
        ]
        print(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        return process
    except Exception as e:
        print(f"Method 1 failed: {e}")
        
        # Method 2: use flower command directly
        try:
            cmd = [
                PYTHON, '-m', 'flower',
                '-A', 'tasks.simple_test',
                '--port=5555',
                '--address=0.0.0.0'
            ]
            print(f"Running command: {' '.join(cmd)}")
            process = subprocess.Popen(cmd)
            return process
        except Exception as e2:
            print(f"Method 2 also failed: {e2}")
            return None

def main():
    print("=== Starting Flower Monitoring ===")
    
    # Start Flower
    flower_proc = start_flower()
    
    if flower_proc:
        print("\nFlower monitoring started!")
        print("URL: http://localhost:5555/")
        print("Username: admin, Password: admin123")
        print("\nPress Ctrl+C to stop")
        
        try:
            # Wait for user interrupt
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Flower...")
            flower_proc.terminate()
            print("Flower stopped")
    else:
        print("Failed to start Flower!")

if __name__ == "__main__":
    main()
