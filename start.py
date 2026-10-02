#!/usr/bin/env python3
"""
Quick start script for Invoice OCR project.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def main():
    """Main startup function."""
    print("🚀 Starting Invoice OCR Project Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("manage.py").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Check Python version
    if sys.version_info < (3, 12):
        print("❌ Python 3.12+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing dependencies"):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create necessary directories
    directories = ["media/invoices", "logs", "staticfiles"]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Copy environment file if it doesn't exist
    if not Path(".env").exists():
        if Path("env.example").exists():
            run_command("cp env.example .env", "Copying environment configuration")
            print("⚠️  Please edit .env file with your configuration")
        else:
            print("⚠️  No environment file found, please create .env manually")
    
    # Run migrations
    if not run_command(f"{sys.executable} manage.py migrate", "Running database migrations"):
        print("❌ Failed to run migrations")
        sys.exit(1)
    
    # Collect static files
    run_command(f"{sys.executable} manage.py collectstatic --noinput", "Collecting static files")
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Create a superuser: python manage.py createsuperuser")
    print("3. Start the development server: python manage.py runserver")
    print("4. Start Celery worker: python -m celery -A invoice_ocr worker --loglevel=info")
    print("\n📚 Documentation: docs/")
    print("🔧 API Documentation: docs/API.md")
    print("🚀 Deployment Guide: docs/DEPLOYMENT.md")

if __name__ == "__main__":
    main()
