"""
Django REST Framework serializers for OCR app.
"""

from rest_framework import serializers
from .models import (
    InvoiceProcessingJob,
    InvoiceData,
    PartyInfo,
    LineItem,
    ProcessingLog
)


class PartyInfoSerializer(serializers.ModelSerializer):
    """Serializer for PartyInfo model."""
    
    class Meta:
        model = PartyInfo
        fields = [
            'party_type', 'name', 'address_line1', 'address_line2',
            'postal_code', 'country_code', 'tax_id_no', 'registration_no',
            'contact_number'
        ]


class LineItemSerializer(serializers.ModelSerializer):
    """Serializer for LineItem model."""
    
    class Meta:
        model = LineItem
        fields = [
            'classification', 'product_description', 'product_number',
            'quantity_shipped', 'serial_number', 'unit_price', 'extended_value',
            'tax_rate', 'tax_value', 'total_value_incl_tax', 'order'
        ]


class InvoiceDataSerializer(serializers.ModelSerializer):
    """Serializer for InvoiceData model."""
    
    parties = PartyInfoSerializer(many=True, read_only=True)
    line_items = LineItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = InvoiceData
        fields = [
            'invoice_file_name', 'unique_invoice_number', 'invoice_date',
            'due_date', 'purchase_order_number', 'invoice_currency_code',
            'total_value_excl_tax', 'total_tax_value', 'total_payable_value',
            'parties', 'line_items', 'created_at', 'updated_at'
        ]


class ProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for ProcessingLog model."""
    
    class Meta:
        model = ProcessingLog
        fields = [
            'level', 'message', 'timestamp', 'module', 'function', 'line_number'
        ]


class InvoiceProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for InvoiceProcessingJob model."""
    
    invoice_data = InvoiceDataSerializer(read_only=True)
    logs = ProcessingLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = InvoiceProcessingJob
        fields = [
            'id', 'file_name', 'file_path', 'file_size', 'ocr_engine',
            'llm_provider', 'llm_model', 'status', 'progress', 'error_message',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'ocr_text', 'ocr_confidence', 'ocr_processing_time', 'metadata',
            'invoice_data', 'logs'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
            'ocr_text', 'ocr_confidence', 'ocr_processing_time', 'metadata',
            'invoice_data', 'logs'
        ]


class InvoiceUploadSerializer(serializers.Serializer):
    """Serializer for invoice upload requests."""
    
    file = serializers.FileField()
    ocr_engine = serializers.ChoiceField(
        choices=['tesseract', 'paddleocr', 'google_document_ai', 'aws_textract'],
        default='tesseract'
    )
    llm_provider = serializers.ChoiceField(
        choices=['openai', 'google', 'aws'],
        default='openai'
    )
    llm_model = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(default='en', max_length=10)
    
    def validate_file(self, value):
        """Validate uploaded file."""
        # Check file size (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Check file extension
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
        file_extension = value.name.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value


class CSVExportSerializer(serializers.Serializer):
    """Serializer for CSV export requests."""
    
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    status = serializers.ChoiceField(
        choices=['pending', 'processing', 'completed', 'failed'],
        required=False
    )
    ocr_engine = serializers.CharField(required=False)
    llm_provider = serializers.CharField(required=False)
    include_line_items = serializers.BooleanField(default=True)
    include_parties = serializers.BooleanField(default=True)
