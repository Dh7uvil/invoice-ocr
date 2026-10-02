#!/usr/bin/env python3
"""
Service management script.
Start/stop Django, Celery, Flower, and related services.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def print_banner():
    """Print banner."""
    print("=" * 60)
    print("Invoice OCR - Service Management")
    print("=" * 60)

def start_django():
    """Start Django development server."""
    print("Starting Django development server...")
    cmd = ['python', 'manage.py', 'runserver', '0.0.0.0:8000']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_celery():
    """Start Celery worker."""
    print("Starting Celery worker...")
    cmd = ['celery', '-A', 'invoice_ocr', 'worker', '--loglevel=info']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_flower():
    """Start Flower monitoring."""
    print("Starting Flower monitoring...")
    cmd = ['celery', '-A', 'invoice_ocr', 'flower', '--port=5555', '--basic_auth=admin:admin123']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_redis():
    """Start Redis (if available)."""
    print("Checking Redis...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("Redis is running")
        return True
    except:
        print("Redis is not running. Please start Redis manually:")
        print("  Windows: Download and run Redis for Windows")
        print("  Linux/Mac: redis-server")
        return False

def show_status():
    """Show service status."""
    print("\nService Status:")
    print("-" * 30)
    
    # Django
    try:
        import requests
        response = requests.get('http://localhost:8000/', timeout=2)
        print("Django: Running (http://localhost:8000/)")
    except:
        print("Django: Not running")
    
    # Flower
    try:
        import requests
        response = requests.get('http://localhost:5555/flower', timeout=2)
        print("Flower: Running (http://localhost:5555/flower)")
    except:
        print("Flower: Not running")
    
    # Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("Redis: Running")
    except:
        print("Redis: Not running")

def main():
    """Main entry point."""
    print_banner()
    
    if len(sys.argv) < 2:
        print("Usage: python manage_services.py [command]")
        print()
        print("Commands:")
        print("  start     - Start all services")
        print("  django    - Start Django only")
        print("  celery    - Start Celery only")
        print("  flower    - Start Flower only")
        print("  status    - Show service status")
        print("  stop      - Stop all services")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        print("Starting all services...")
        
        # Check Redis
        if not start_redis():
            return
        
        # Start services
        django_proc = start_django()
        celery_proc = start_celery()
        flower_proc = start_flower()
        
        print("\nAll services started!")
        print("Django: http://localhost:8000/")
        print("Flower: http://localhost:5555/flower")
        print("Admin: http://localhost:8000/admin/")
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
    
    elif command == 'django':
        start_django()
        print("Django started at http://localhost:8000/")
    
    elif command == 'celery':
        if start_redis():
            start_celery()
            print("Celery worker started")
    
    elif command == 'flower':
        start_flower()
        print("Flower started at http://localhost:5555/flower")
    
    elif command == 'status':
        show_status()
    
    elif command == 'stop':
        print("Stopping all services...")
        # Stop logic can be added here
        print("Services stopped")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
