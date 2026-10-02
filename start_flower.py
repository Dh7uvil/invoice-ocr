#!/usr/bin/env python3
"""
Flower startup script for monitoring Celery task status.
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_ocr.settings')
django.setup()

def start_flower():
    """Start Flower monitoring service."""
    print("Starting Flower monitoring service...")
    print("=" * 50)
    
    # Load configuration
    broker_url = settings.CELERY_BROKER_URL
    flower_port = settings.FLOWER_PORT
    basic_auth = settings.FLOWER_BASIC_AUTH
    
    print(f"Broker URL: {broker_url}")
    print(f"Flower Port: {flower_port}")
    print(f"Basic Auth: {basic_auth}")
    print()
    
    # Start Flower (Flower 2.x CLI)
    import subprocess
    cmd = [
        'python', '-m', 'flower',
        '--app=tasks.simple_test',
        f'--broker={broker_url}',
        f'--result-backend={broker_url}',
        f'--url-prefix=/flower',
        f'--port={flower_port}',
        f'--basic-auth={basic_auth}'
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print()
    print("Flower will be available at:")
    print(f"  http://localhost:{flower_port}/flower")
    print(f"  Username: admin")
    print(f"  Password: admin123")
    print()
    print("Press Ctrl+C to stop Flower")
    print("=" * 50)
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nFlower stopped by user")
    except Exception as e:
        print(f"Error starting Flower: {e}")

if __name__ == "__main__":
    start_flower()
