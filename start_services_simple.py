#!/usr/bin/env python
"""
Simplified service startup script.
"""
import subprocess
import time
import sys
import os

PYTHON = sys.executable

def start_django():
    """Start Django server."""
    print("Starting Django server...")
    cmd = [PYTHON, 'manage.py', 'runserver']
    return subprocess.Popen(cmd)

def start_celery():
    """Start Celery worker."""
    print("Starting Celery worker...")
    cmd = [PYTHON, '-m', 'celery',
           '-A', 'tasks.simple_test', 'worker', '--loglevel=info', '--concurrency=1']
    return subprocess.Popen(cmd)

def start_flower():
    """Start Flower monitoring."""
    print("Starting Flower monitoring...")
    cmd = [PYTHON, '-m', 'flower',
           '-A', 'tasks.simple_test', '--port=5555', '--address=0.0.0.0']
    return subprocess.Popen(cmd)

def main():
    print("=== Starting All Services ===")
    
    # Start Django
    django_proc = start_django()
    time.sleep(3)
    
    # Start Celery
    celery_proc = start_celery()
    time.sleep(3)
    
    # Start Flower
    flower_proc = start_flower()
    time.sleep(3)
    
    print("\n=== Service Status ===")
    print("Django Admin: http://localhost:8000/admin/")
    print("Flower: http://localhost:5555/")
    print("\nPress Ctrl+C to stop all services")
    
    try:
        # Wait for user interrupt
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        django_proc.terminate()
        celery_proc.terminate()
        flower_proc.terminate()
        print("All services stopped")

if __name__ == "__main__":
    main()
