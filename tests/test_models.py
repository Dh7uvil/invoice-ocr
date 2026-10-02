"""
Tests for Django models.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from ocr_app.models import (
    InvoiceProcessingJob,
    InvoiceData,
    PartyInfo,
    LineItem
)


class TestInvoiceProcessingJob(TestCase):
    """Test InvoiceProcessingJob model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_job(self):
        """Test creating a processing job."""
        job = InvoiceProcessingJob.objects.create(
            user=self.user,
            file_name='test.pdf',
            file_path='/path/to/test.pdf',
            file_size=1024,
            ocr_engine='tesseract',
            llm_provider='openai'
        )
        
        assert job.file_name == 'test.pdf'
        assert job.status == 'pending'
        assert job.progress == 0
    
    def test_job_str(self):
        """Test job string representation."""
        job = InvoiceProcessingJob.objects.create(
            user=self.user,
            file_name='test.pdf',
            file_path='/path/to/test.pdf',
            file_size=1024
        )
        
        assert str(job) == f"Job {job.id}: test.pdf (pending)"


class TestInvoiceData(TestCase):
    """Test InvoiceData model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.job = InvoiceProcessingJob.objects.create(
            user=self.user,
            file_name='test.pdf',
            file_path='/path/to/test.pdf',
            file_size=1024
        )
    
    def test_create_invoice_data(self):
        """Test creating invoice data."""
        invoice_data = InvoiceData.objects.create(
            job=self.job,
            invoice_file_name='test.pdf',
            unique_invoice_number='INV-001',
            invoice_date='2024-01-01',
            due_date='2024-01-31',
            invoice_currency_code='USD',
            total_value_excl_tax=100.00,
            total_tax_value=10.00,
            total_payable_value=110.00
        )
        
        assert invoice_data.unique_invoice_number == 'INV-001'
        assert invoice_data.total_payable_value == 110.00


class TestPartyInfo(TestCase):
    """Test PartyInfo model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.job = InvoiceProcessingJob.objects.create(
            user=self.user,
            file_name='test.pdf',
            file_path='/path/to/test.pdf',
            file_size=1024
        )
        self.invoice_data = InvoiceData.objects.create(
            job=self.job,
            invoice_file_name='test.pdf',
            unique_invoice_number='INV-001',
            invoice_date='2024-01-01',
            due_date='2024-01-31',
            invoice_currency_code='USD',
            total_value_excl_tax=100.00,
            total_tax_value=10.00,
            total_payable_value=110.00
        )
    
    def test_create_party_info(self):
        """Test creating party information."""
        party = PartyInfo.objects.create(
            invoice_data=self.invoice_data,
            party_type='supplier',
            name='Test Supplier',
            address_line1='123 Main St'
        )
        
        assert party.name == 'Test Supplier'
        assert party.party_type == 'supplier'
