#!/bin/bash

# Setup script for Invoice OCR project

set -e

echo "Setting up Invoice OCR project..."

# Check if Python 3.12 is installed
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12 is required but not installed."
    echo "Please install Python 3.12 and try again."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
python3.12 -m pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p media/invoices
mkdir -p logs
mkdir -p staticfiles

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Copying environment configuration..."
    cp env.example .env
    echo "Please edit .env file with your configuration."
fi

# Run database migrations
echo "Running database migrations..."
python3.12 manage.py migrate

# Create superuser (optional)
echo "Creating superuser..."
python3.12 manage.py createsuperuser --noinput || echo "Superuser already exists or creation failed"

# Collect static files
echo "Collecting static files..."
python3.12 manage.py collectstatic --noinput

echo "Setup completed!"
echo ""
echo "To start the development server:"
echo "  python manage.py runserver"
echo ""
echo "To start Celery worker:"
echo "  python -m celery -A invoice_ocr worker --loglevel=info"
echo ""
echo "To start Celery beat:"
echo "  python -m celery -A invoice_ocr beat --loglevel=info"
