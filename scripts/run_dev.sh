#!/bin/bash

# Development server startup script

echo "Starting Invoice OCR development environment..."

# Start Redis (if not running)
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
fi

# Start Celery worker in background
echo "Starting Celery worker..."
python -m celery -A invoice_ocr worker --loglevel=info &
CELERY_PID=$!

# Start Celery beat in background
echo "Starting Celery beat..."
python -m celery -A invoice_ocr beat --loglevel=info &
BEAT_PID=$!

# Start Django development server
echo "Starting Django development server..."
python manage.py runserver

# Cleanup function
cleanup() {
    echo "Shutting down services..."
    kill $CELERY_PID $BEAT_PID 2>/dev/null || true
    exit
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Wait for processes
wait
