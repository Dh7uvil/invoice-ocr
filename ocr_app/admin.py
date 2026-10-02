"""
Django admin configuration for OCR app.
"""

import os
from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from services.csv_export_service import CSVExportService
from .models import (
    InvoiceProcessingJob,
    InvoiceData,
    PartyInfo,
    LineItem,
    ProcessingLog
)


class InvoiceProcessingJobForm(forms.ModelForm):
    """Custom form for InvoiceProcessingJob with file upload support."""
    
    file_upload = forms.FileField(
        label="Upload invoice file",
        help_text="Supports PDF, JPG, PNG, TIFF, BMP formats, max 10MB",
        required=False,
        widget=forms.FileInput(attrs={
            'accept': '.pdf,.jpg,.jpeg,.png,.tiff,.bmp',
            'class': 'file-input'
        })
    )
    
    class Meta:
        model = InvoiceProcessingJob
        fields = [
            'user', 'file_upload', 'file_name', 'file_path', 'file_size',
            'ocr_engine', 'llm_provider', 'llm_model', 'status'
        ]
        widgets = {
            'file_name': forms.TextInput(attrs={'readonly': True}),
            'file_path': forms.TextInput(attrs={'readonly': True}),
            'file_size': forms.NumberInput(attrs={'readonly': True}),
        }

    OCR_ENGINE_CHOICES = [
        ('tesseract', 'Tesseract'),
        ('paddleocr', 'PaddleOCR'),
        ('google_document_ai', 'Google Document AI'),
        ('aws_textract', 'AWS Textract'),
    ]

    ocr_engine = forms.ChoiceField(
        choices=OCR_ENGINE_CHOICES,
        label='OCR Engine',
        help_text='Select the OCR engine to use'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide read-only fields when creating a new record
        if not self.instance.pk:
            self.fields['file_name'].widget.attrs['style'] = 'display:none'
            self.fields['file_path'].widget.attrs['style'] = 'display:none'
            self.fields['file_size'].widget.attrs['style'] = 'display:none'
    
    def clean_file_upload(self):
        """Validate uploaded file."""
        file = self.cleaned_data.get('file_upload')
        if file:
            # Check file size (10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size cannot exceed 10MB")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
                )
        return file
    
    def save(self, commit=True):
        """Handle file upload on save."""
        instance = super().save(commit=False)
        
        # Process file upload
        uploaded_file = self.cleaned_data.get('file_upload')
        if uploaded_file:
            # Create upload directory
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, 'wb') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Auto-fill fields
            instance.file_name = uploaded_file.name
            instance.file_path = file_path
            instance.file_size = uploaded_file.size
        
        if commit:
            instance.save()
        return instance


@admin.register(InvoiceProcessingJob)
class InvoiceProcessingJobAdmin(admin.ModelAdmin):
    form = InvoiceProcessingJobForm
    list_display = [
        'id', 'file_name', 'status', 'ocr_engine', 'llm_provider',
        'progress', 'created_at', 'completed_at'
    ]
    list_filter = ['status', 'ocr_engine', 'llm_provider', 'created_at']
    search_fields = ['file_name', 'file_path']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
    actions = ['export_selected_invoices_csv']
    
    fieldsets = (
        ('File Upload', {
            'fields': ('user', 'file_upload'),
            'description': 'Select the invoice file to process. The system will auto-fill file name, path, and size.'
        }),
        ('File Information', {
            'fields': ('file_name', 'file_path', 'file_size'),
            'classes': ('collapse',)
        }),
        ('Processing Configuration', {
            'fields': ('ocr_engine', 'llm_provider', 'llm_model')
        }),
        ('Status', {
            'fields': ('status', 'progress', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('OCR Results', {
            'fields': ('ocr_text', 'ocr_confidence', 'ocr_processing_time'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Adjust form based on whether this is a new object."""
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # New object
            # Hide file info fields; they are auto-filled on upload
            form.base_fields['file_name'].widget.attrs['style'] = 'display:none'
            form.base_fields['file_path'].widget.attrs['style'] = 'display:none'
            form.base_fields['file_size'].widget.attrs['style'] = 'display:none'
        return form
    
    def save_model(self, request, obj, form, change):
        """Start processing task when saving a new job."""
        super().save_model(request, obj, form, change)
        
        # If newly created and status is pending, start the real processing task
        if not change and obj.status == 'pending':
            from tasks.invoice_processing import process_invoice_task
            process_invoice_task.delay(obj.id)
            self.message_user(request, f"Invoice processing started (Job ID: {obj.id}). Running OCR and LLM parsing.")

    def export_selected_invoices_csv(self, request, queryset):
        """Admin action: export selected jobs as CSV (with line items and parties)."""
        service = CSVExportService()
        return service.export_invoices(
            jobs=queryset,
            include_line_items=True,
            include_parties=True,
            include_processing_info=True
        )
    export_selected_invoices_csv.short_description = 'Export selected as CSV (with line items and parties)'
    
    class Media:
        js = ('admin/js/invoice_admin.js',)
        css = {
            'all': ('admin/css/invoice_admin.css',)
        }


@admin.register(InvoiceData)
class InvoiceDataAdmin(admin.ModelAdmin):
    list_display = [
        'unique_invoice_number', 'invoice_file_name', 'invoice_date',
        'total_payable_value', 'invoice_currency_code', 'created_at'
    ]
    list_filter = ['invoice_currency_code', 'created_at']
    search_fields = ['unique_invoice_number', 'invoice_file_name']
    readonly_fields = ['created_at', 'updated_at', 'job']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('job')
    
    def has_add_permission(self, request):
        """Prevent manual InvoiceData creation; only created via processing jobs."""
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """All fields are read-only since this is parsed output."""
        if obj:  # Editing existing object
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


@admin.register(PartyInfo)
class PartyInfoAdmin(admin.ModelAdmin):
    list_display = ['party_type', 'name', 'country_code', 'tax_id_no']
    list_filter = ['party_type', 'country_code']
    search_fields = ['name', 'tax_id_no', 'registration_no']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invoice_data')

    def get_readonly_fields(self, request, obj=None):
        """Show party type as read-only when editing; selectable when creating."""
        if obj:
            return ['party_type']
        return []


@admin.register(LineItem)
class LineItemAdmin(admin.ModelAdmin):
    list_display = [
        'product_description', 'quantity_shipped', 'unit_price',
        'total_value_incl_tax', 'order'
    ]
    list_filter = ['classification', 'tax_rate']
    search_fields = ['product_description', 'product_number', 'serial_number']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invoice_data')


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ['level', 'message_short', 'timestamp', 'job_id']
    list_filter = ['level', 'timestamp']
    search_fields = ['message', 'module', 'function']
    readonly_fields = ['timestamp']
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'
    
    def job_id(self, obj):
        return obj.job.id
    job_id.short_description = 'Job ID'
