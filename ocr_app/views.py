"""
Django REST Framework views for OCR app.
"""

import os
import csv
import logging
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import InvoiceProcessingJob, InvoiceData, PartyInfo, LineItem
from .serializers import (
    InvoiceProcessingJobSerializer,
    InvoiceUploadSerializer,
    CSVExportSerializer
)
from tasks.invoice_processing import process_invoice_task
from services.csv_export_service import CSVExportService

logger = logging.getLogger(__name__)


class InvoiceProcessingJobListView(generics.ListAPIView):
    """List all invoice processing jobs."""
    
    queryset = InvoiceProcessingJob.objects.all()
    serializer_class = InvoiceProcessingJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter jobs by user if not staff."""
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset.order_by('-created_at')


class InvoiceProcessingJobDetailView(generics.RetrieveAPIView):
    """Retrieve a specific invoice processing job."""
    
    queryset = InvoiceProcessingJob.objects.all()
    serializer_class = InvoiceProcessingJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter jobs by user if not staff."""
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_invoice(request):
    """Upload and process an invoice file."""
    
    serializer = InvoiceUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Save uploaded file
        uploaded_file = serializer.validated_data['file']
        file_name = uploaded_file.name
        file_size = uploaded_file.size
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, 'wb') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Create processing job
        job = InvoiceProcessingJob.objects.create(
            user=request.user,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            ocr_engine=serializer.validated_data['ocr_engine'],
            llm_provider=serializer.validated_data['llm_provider'],
            llm_model=serializer.validated_data.get('llm_model'),
            status='pending'
        )
        
        # Start processing task
        process_invoice_task.delay(job.id)
        
        return Response({
            'message': 'Invoice uploaded successfully',
            'job_id': job.id,
            'status': job.status
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error uploading invoice: {str(e)}")
        return Response(
            {'error': 'Failed to upload invoice'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_csv(request):
    """Export invoice data to CSV."""
    
    serializer = CSVExportSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Filter jobs based on parameters
        jobs = InvoiceProcessingJob.objects.filter(
            status='completed',
            invoice_data__isnull=False
        )
        
        # Apply filters
        if serializer.validated_data.get('start_date'):
            jobs = jobs.filter(created_at__gte=serializer.validated_data['start_date'])
        
        if serializer.validated_data.get('end_date'):
            jobs = jobs.filter(created_at__lte=serializer.validated_data['end_date'])
        
        if serializer.validated_data.get('ocr_engine'):
            jobs = jobs.filter(ocr_engine=serializer.validated_data['ocr_engine'])
        
        if serializer.validated_data.get('llm_provider'):
            jobs = jobs.filter(llm_provider=serializer.validated_data['llm_provider'])
        
        # Use central CSV export service for consistent formatting and filenames
        service = CSVExportService()
        response = service.export_invoices(
            jobs=jobs,
            include_line_items=serializer.validated_data.get('include_line_items', True),
            include_parties=serializer.validated_data.get('include_parties', True),
            include_processing_info=True
        )
        return response
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}")
        return Response(
            {'error': 'Failed to export CSV'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_parties_by_invoice(request, invoice_data_id: int):
    """Return parties for a given InvoiceData id grouped by party_type.
    Used by Admin JS to swap PartyInfo values when changing party_type.
    """
    try:
        invoice_data = get_object_or_404(InvoiceData, id=invoice_data_id)
        parties = invoice_data.parties.all()
        result = {}
        for p in parties:
            result[p.party_type] = {
                'name': p.name,
                'address_line1': p.address_line1,
                'address_line2': p.address_line2 or '',
                'country_code': p.country_code or '',
                'tax_id_no': p.tax_id_no or '',
                'registration_no': p.registration_no or '',
                'contact_number': p.contact_number or ''
            }
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching parties for invoice_data {invoice_data_id}: {e}")
        return Response({'error': 'Failed to fetch parties'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_line_items_csv(request):
    """Export detailed line items to CSV (one row per line item)."""
    serializer = CSVExportSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        jobs = InvoiceProcessingJob.objects.filter(
            status='completed',
            invoice_data__isnull=False
        )

        if serializer.validated_data.get('start_date'):
            jobs = jobs.filter(created_at__gte=serializer.validated_data['start_date'])
        if serializer.validated_data.get('end_date'):
            jobs = jobs.filter(created_at__lte=serializer.validated_data['end_date'])
        if serializer.validated_data.get('ocr_engine'):
            jobs = jobs.filter(ocr_engine=serializer.validated_data['ocr_engine'])
        if serializer.validated_data.get('llm_provider'):
            jobs = jobs.filter(llm_provider=serializer.validated_data['llm_provider'])

        service = CSVExportService()
        return service.export_line_items(jobs=jobs)
    
    except Exception as e:
        logger.error(f"Error exporting line items CSV: {str(e)}")
        return Response({'error': 'Failed to export line items CSV'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def job_status(request, job_id):
    """Get the status of a processing job."""
    
    job = get_object_or_404(InvoiceProcessingJob, id=job_id)
    
    # Check permissions
    if not request.user.is_staff and job.user != request.user:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = InvoiceProcessingJobSerializer(job)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_job(request, job_id):
    """Delete a processing job and its associated data."""
    
    job = get_object_or_404(InvoiceProcessingJob, id=job_id)
    
    # Check permissions
    if not request.user.is_staff and job.user != request.user:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Delete associated file
        if os.path.exists(job.file_path):
            os.remove(job.file_path)
        
        # Delete job (this will cascade to related data)
        job.delete()
        
        return Response(
            {'message': 'Job deleted successfully'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        return Response(
            {'error': 'Failed to delete job'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
