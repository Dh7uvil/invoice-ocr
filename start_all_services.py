#!/usr/bin/env python
"""
Full service startup script.
"""
import subprocess
import time
import sys
import os
import signal

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

def start_flower_simple():
    """Start Flower (simplified)."""
    print("Starting Flower monitoring...")
    cmd = [PYTHON, '-m', 'flower',
           '-A', 'tasks.simple_test', '--port=5555']
    return subprocess.Popen(cmd)

def check_services():
    """Check service status."""
    print("\n=== Service Status ===")
    
    # Check Django
    try:
        import requests
        response = requests.get('http://localhost:8000/admin/', timeout=3)
        print(f"Django: Running (status code: {response.status_code})")
    except:
        print("Django: Not running")
    
    # Check Flower
    try:
        import requests
        response = requests.get('http://localhost:5555/', timeout=3)
        print(f"Flower: Running (status code: {response.status_code})")
    except:
        print("Flower: Not running")
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("Redis: Running")
    except:
        print("Redis: Not running")

def main():
    print("=== Starting All Services ===")
    
    processes = []
    
    try:
        # Start Django
        django_proc = start_django()
        processes.append(('Django', django_proc))
        time.sleep(3)
        
        # Start Celery
        celery_proc = start_celery()
        processes.append(('Celery', celery_proc))
        time.sleep(3)
        
        # Start Flower
        flower_proc = start_flower_simple()
        processes.append(('Flower', flower_proc))
        time.sleep(5)
        
        # Check service status
        check_services()
        
        print("\n=== Service URLs ===")
        print("Django Admin: http://localhost:8000/admin/")
        print("Flower: http://localhost:5555/")
        print("\nPress Ctrl+C to stop all services")
        
        # Wait for user interrupt
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for name, proc in processes:
            try:
                proc.terminate()
                print(f"{name} stopped")
            except:
                pass
        print("All services stopped")

if __name__ == "__main__":
    main()
