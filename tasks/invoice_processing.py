"""
Celery tasks for invoice processing.
"""

import os
import json
import logging
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ocr_app.models import InvoiceProcessingJob, InvoiceData, PartyInfo, LineItem, ProcessingLog
from services.ocr_service import get_ocr_service
from services.llm_service import get_llm_service
from schemas.invoice_models import InvoiceData as InvoiceDataSchema

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_invoice_task(self, job_id):
    """Process an invoice file using OCR and LLM."""
    
    try:
        # Get the job
        job = InvoiceProcessingJob.objects.get(id=job_id)
        
        # Update job status
        job.status = 'processing'
        job.started_at = timezone.now()
        job.progress = 10
        job.save()
        
        # Log start
        ProcessingLog.objects.create(
            job=job,
            level='INFO',
            message='Starting invoice processing',
            module='tasks.invoice_processing',
            function='process_invoice_task'
        )
        
        # Step 1: OCR processing
        job.progress = 20
        job.save()
        
        ocr_service = get_ocr_service(
            engine=job.ocr_engine,
            tesseract_cmd=getattr(settings, 'TESSERACT_CMD', 'tesseract')
        )
        
        ocr_result = ocr_service.extract_text(job.file_path)
        
        # Update job with OCR results
        job.ocr_text = ocr_result.text
        job.ocr_confidence = ocr_result.confidence
        job.ocr_processing_time = ocr_result.processing_time
        job.progress = 50
        job.save()
        
        # Log OCR completion
        ProcessingLog.objects.create(
            job=job,
            level='INFO',
            message=f'OCR completed with confidence: {ocr_result.confidence:.2f}',
            module='tasks.invoice_processing',
            function='process_invoice_task'
        )
        
        # Step 2: LLM processing
        job.progress = 60
        job.save()
        
        llm_service = get_llm_service(
            provider=job.llm_provider,
            model=job.llm_model
        )
        
        invoice_data = llm_service.parse_invoice(
            ocr_result.text,
            context={"file_name": job.file_name}
        )
        
        # Step 3: Save structured data
        job.progress = 80
        job.save()
        
        # Create InvoiceData record
        invoice_data_record = InvoiceData.objects.create(
            job=job,
            invoice_file_name=invoice_data.invoice_file_name,
            unique_invoice_number=invoice_data.unique_invoice_number,
            invoice_date=invoice_data.invoice_date,
            due_date=invoice_data.due_date,
            purchase_order_number=invoice_data.purchase_order_number,
            invoice_currency_code=invoice_data.invoice_currency_code,
            total_value_excl_tax=invoice_data.total_value_excl_tax,
            total_tax_value=invoice_data.total_tax_value,
            total_payable_value=invoice_data.total_payable_value,
            raw_data=invoice_data.dict()
        )
        
        # Create PartyInfo records
        for party_type in ['supplier', 'buyer', 'ship_to']:
            party_data = getattr(invoice_data, f'{party_type}_info')
            PartyInfo.objects.create(
                invoice_data=invoice_data_record,
                party_type=party_type,
                name=party_data.name,
                address_line1=party_data.address_line1,
                address_line2=party_data.address_line2,
                postal_code=party_data.postal_code,
                country_code=party_data.country_code,
                tax_id_no=party_data.tax_id_no,
                registration_no=party_data.registration_no,
                contact_number=party_data.contact_number
            )
        
        # Create LineItem records
        for i, line_item in enumerate(invoice_data.line_items):
            LineItem.objects.create(
                invoice_data=invoice_data_record,
                classification=line_item.classification,
                product_description=line_item.product_description,
                product_number=line_item.product_number,
                quantity_shipped=line_item.quantity_shipped,
                serial_number=line_item.serial_number,
                unit_price=line_item.unit_price,
                extended_value=line_item.extended_value,
                tax_rate=line_item.tax_rate,
                tax_value=line_item.tax_value,
                total_value_incl_tax=line_item.total_value_incl_tax,
                order=i
            )
        
        # Complete the job
        job.status = 'completed'
        job.progress = 100
        job.completed_at = timezone.now()
        job.save()
        
        # Log completion
        ProcessingLog.objects.create(
            job=job,
            level='INFO',
            message='Invoice processing completed successfully',
            module='tasks.invoice_processing',
            function='process_invoice_task'
        )
        
        logger.info(f"Invoice processing completed for job {job_id}")
        
        return {
            'status': 'completed',
            'job_id': job_id,
            'invoice_number': invoice_data.unique_invoice_number
        }
        
    except InvoiceProcessingJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        # Raise to ensure Celery marks task as FAILURE instead of SUCCESS with a failed payload
        raise Exception(f"Job {job_id} not found")
        
    except Exception as e:
        logger.error(f"Error processing invoice job {job_id}: {str(e)}")
        
        # Update job status to failed
        try:
            job = InvoiceProcessingJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            
            # Log error
            ProcessingLog.objects.create(
                job=job,
                level='ERROR',
                message=f'Processing failed: {str(e)}',
                module='tasks.invoice_processing',
                function='process_invoice_task'
            )
        except:
            # If updating the job also fails, still propagate the original exception
            pass
        
        # Re-raise to let Celery record the task state as FAILURE
        raise


@shared_task
def cleanup_old_jobs():
    """Clean up old completed jobs and their files."""
    
    try:
        # Delete jobs older than 30 days
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=30)
        
        old_jobs = InvoiceProcessingJob.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed']
        )
        
        deleted_count = 0
        for job in old_jobs:
            try:
                # Delete associated file
                if os.path.exists(job.file_path):
                    os.remove(job.file_path)
                
                # Delete job (cascades to related data)
                job.delete()
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Error deleting job {job.id}: {str(e)}")
        
        logger.info(f"Cleaned up {deleted_count} old jobs")
        return {'deleted_count': deleted_count}
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        return {'error': str(e)}
