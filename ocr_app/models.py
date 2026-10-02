"""
Django models for invoice OCR application.
"""

import json
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class InvoiceProcessingJob(models.Model):
    """Model for tracking invoice processing jobs."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # Basic information
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField()
    
    # Processing configuration
    ocr_engine = models.CharField(max_length=50, default='tesseract')
    llm_provider = models.CharField(max_length=50, default='openai')
    llm_model = models.CharField(max_length=100, null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Processing results
    ocr_text = models.TextField(null=True, blank=True)
    ocr_confidence = models.FloatField(null=True, blank=True)
    ocr_processing_time = models.FloatField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice Processing Job'
        verbose_name_plural = 'Invoice Processing Jobs'
    
    def __str__(self):
        return f"Job {self.id}: {self.file_name} ({self.status})"


class InvoiceData(models.Model):
    """Model for storing parsed invoice data."""
    
    # Job reference
    job = models.OneToOneField(InvoiceProcessingJob, on_delete=models.CASCADE, related_name='invoice_data')
    
    # Basic invoice information
    invoice_file_name = models.CharField(max_length=255)
    unique_invoice_number = models.CharField(max_length=100, db_index=True)
    invoice_date = models.CharField(max_length=50)
    due_date = models.CharField(max_length=50)
    purchase_order_number = models.CharField(max_length=100, null=True, blank=True)
    
    # Currency
    invoice_currency_code = models.CharField(max_length=10, default='USD')
    
    # Financial totals
    total_value_excl_tax = models.DecimalField(max_digits=15, decimal_places=2)
    total_tax_value = models.DecimalField(max_digits=15, decimal_places=2)
    total_payable_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Raw data for debugging
    raw_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice Data'
        verbose_name_plural = 'Invoice Data'
    
    def __str__(self):
        return f"Invoice {self.unique_invoice_number}"


class PartyInfo(models.Model):
    """Model for storing party information (supplier, buyer, ship_to)."""
    
    PARTY_TYPE_CHOICES = [
        ('supplier', 'Supplier'),
        ('buyer', 'Buyer'),
        ('ship_to', 'Ship To'),
    ]
    
    # Relationships
    invoice_data = models.ForeignKey(InvoiceData, on_delete=models.CASCADE, related_name='parties')
    party_type = models.CharField(max_length=20, choices=PARTY_TYPE_CHOICES)
    
    # Party information
    name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    tax_id_no = models.CharField(max_length=50, null=True, blank=True)
    registration_no = models.CharField(max_length=50, null=True, blank=True)
    contact_number = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        unique_together = ['invoice_data', 'party_type']
        verbose_name = 'Party Information'
        verbose_name_plural = 'Party Information'
    
    def __str__(self):
        return f"{self.get_party_type_display()}: {self.name}"


class LineItem(models.Model):
    """Model for storing invoice line items."""
    
    # Relationships
    invoice_data = models.ForeignKey(InvoiceData, on_delete=models.CASCADE, related_name='line_items')
    
    # Product information
    classification = models.CharField(max_length=100, null=True, blank=True)
    product_description = models.CharField(max_length=500)
    product_number = models.CharField(max_length=100, null=True, blank=True)
    serial_number = models.CharField(max_length=100, null=True, blank=True)
    
    # Quantities and pricing
    quantity_shipped = models.IntegerField()
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    extended_value = models.DecimalField(max_digits=15, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tax_value = models.DecimalField(max_digits=15, decimal_places=2)
    total_value_incl_tax = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Ordering
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Line Item'
        verbose_name_plural = 'Line Items'
    
    def __str__(self):
        return f"Line Item: {self.product_description[:50]}"


class ProcessingLog(models.Model):
    """Model for storing processing logs."""
    
    LOG_LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Relationships
    job = models.ForeignKey(InvoiceProcessingJob, on_delete=models.CASCADE, related_name='logs')
    
    # Log information
    level = models.CharField(max_length=20, choices=LOG_LEVEL_CHOICES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional context
    module = models.CharField(max_length=100, null=True, blank=True)
    function = models.CharField(max_length=100, null=True, blank=True)
    line_number = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Processing Log'
        verbose_name_plural = 'Processing Logs'
    
    def __str__(self):
        return f"{self.level}: {self.message[:100]}"
