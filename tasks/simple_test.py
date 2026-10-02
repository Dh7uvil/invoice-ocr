#!/usr/bin/env python3
"""
Simple test tasks without complex OCR dependencies.
"""

import os
import django
from celery import Celery

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_ocr.settings')
django.setup()

from django.conf import settings

# Create Celery app
app = Celery('invoice_ocr')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def simple_test_task(self, message="Hello World"):
    """Simple test task."""
    print(f"Processing: {message}")
    return f"Task completed: {message}"

@app.task(bind=True)
def process_invoice_simple(self, job_id):
    """Simplified invoice processing task."""
    from ocr_app.models import InvoiceProcessingJob, InvoiceData
    
    try:
        job = InvoiceProcessingJob.objects.get(id=job_id)
        job.status = 'processing'
        job.save()
        
        # Simulate processing
        import time
        time.sleep(2)
        
        # Create sample data
        invoice_data = InvoiceData.objects.create(
            job=job,
            unique_invoice_number=f"INV-{job_id}-001",
            invoice_file_name=job.file_name,
            invoice_date="2024-01-15",
            due_date="2024-02-15",
            purchase_order_number=f"PO-{job_id}",
            invoice_currency_code="USD",
            total_value_excl_tax=1000.00,
            total_tax_value=100.00,
            total_payable_value=1100.00
        )
        
        job.status = 'completed'
        job.save()
        
        return f"Invoice processed successfully: {invoice_data.unique_invoice_number}"
        
    except Exception as e:
        job.status = 'failed'
        job.save()
        raise e
