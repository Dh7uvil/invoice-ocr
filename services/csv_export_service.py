"""
CSV export service for invoice data.
"""

import os
import csv
import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from django.http import HttpResponse
from django.db.models import QuerySet
from decimal import Decimal, InvalidOperation

from ocr_app.models import InvoiceProcessingJob, InvoiceData, PartyInfo, LineItem

logger = logging.getLogger(__name__)


class CSVExportService:
    """Service for exporting invoice data to CSV format."""
    
    def __init__(self):
        self.logger = logger
    
    def export_invoices(
        self,
        jobs: QuerySet[InvoiceProcessingJob],
        include_line_items: bool = True,
        include_parties: bool = True,
        include_processing_info: bool = True
    ) -> HttpResponse:
        """Export invoice data to CSV format."""
        
        try:
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            export_filename = self._build_export_filename(jobs)
            response['Content-Disposition'] = f'attachment; filename="{export_filename}"'
            
            writer = csv.writer(response)
            
            # Write header
            header = self._get_csv_header(
                include_line_items=include_line_items,
                include_parties=include_parties,
                include_processing_info=include_processing_info
            )
            writer.writerow(header)
            
            # Write data rows
            for job in jobs:
                if hasattr(job, 'invoice_data') and job.invoice_data:
                    row = self._create_data_row(
                        job=job,
                        include_line_items=include_line_items,
                        include_parties=include_parties,
                        include_processing_info=include_processing_info
                    )
                    writer.writerow(row)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error exporting CSV: {str(e)}")
            raise
    
    # -------------------------
    # Formatting helpers
    # -------------------------
    def _currency_prefix(self, currency_code: Optional[str]) -> str:
        mapping = {
            'MYR': 'RM',
            'USD': '$',
            'EUR': '€',
            'CNY': '¥',
            'JPY': '¥',
            'GBP': '£',
            'INR': '₹',
            'SGD': 'S$',
            'AUD': 'A$',
            'CAD': 'C$',
            'HKD': 'HK$',
        }
        if not currency_code:
            return ''
        code = str(currency_code).upper()
        return mapping.get(code, code)

    def _format_money(self, value: Any, currency_code: Optional[str]) -> str:
        prefix = self._currency_prefix(currency_code)
        # Coerce to Decimal for stable formatting
        try:
            if isinstance(value, Decimal):
                amt = value
            else:
                amt = Decimal(str(value))
            amount_str = format(amt, '.2f')
        except (InvalidOperation, TypeError, ValueError):
            # Fallback to raw string
            return f"{prefix} {value}".strip()
        return f"{prefix} {amount_str}".strip()
    
    def _get_csv_header(
        self,
        include_line_items: bool = True,
        include_parties: bool = True,
        include_processing_info: bool = True
    ) -> List[str]:
        """Get CSV header based on options."""
        
        header = [
            'Job ID',
            'Invoice Number',
            'Invoice Date',
            'Due Date',
            'PO Number',
            'Currency',
            'Total Excl Tax',
            'Total Tax',
            'Total Payable',
            'File Name'
        ]
        
        if include_processing_info:
            header.extend([
                'OCR Engine',
                'LLM Provider',
                'Processing Time',
                'Status',
                'Created At'
            ])
        
        if include_parties:
            header.extend([
                'Supplier Name',
                'Supplier Address',
                'Supplier Country',
                'Supplier Tax ID',
                'Buyer Name',
                'Buyer Address',
                'Buyer Country',
                'Buyer Tax ID',
                'Ship To Name',
                'Ship To Address',
                'Ship To Country'
            ])
        
        if include_line_items:
            header.extend([
                'Line Item Count',
                'Product Descriptions',
                'Product Numbers',
                'Serial Numbers',
                'Total Quantities',
                'Average Unit Price'
            ])
        
        return header
    
    def _create_data_row(
        self,
        job: InvoiceProcessingJob,
        include_line_items: bool = True,
        include_parties: bool = True,
        include_processing_info: bool = True
    ) -> List[str]:
        """Create a data row for the CSV."""
        
        invoice_data = job.invoice_data
        
        # Basic invoice information
        row = [
            job.id,
            invoice_data.unique_invoice_number,
            invoice_data.invoice_date,
            invoice_data.due_date,
            invoice_data.purchase_order_number or '',
            invoice_data.invoice_currency_code,
            self._format_money(invoice_data.total_value_excl_tax, invoice_data.invoice_currency_code),
            self._format_money(invoice_data.total_tax_value, invoice_data.invoice_currency_code),
            self._format_money(invoice_data.total_payable_value, invoice_data.invoice_currency_code),
            job.file_name
        ]
        
        if include_processing_info:
            row.extend([
                job.ocr_engine,
                job.llm_provider,
                str(job.ocr_processing_time or 0),
                job.status,
                job.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        if include_parties:
            # Get party information
            supplier = invoice_data.parties.filter(party_type='supplier').first()
            buyer = invoice_data.parties.filter(party_type='buyer').first()
            ship_to = invoice_data.parties.filter(party_type='ship_to').first()
            
            row.extend([
                supplier.name if supplier else '',
                f"{supplier.address_line1}, {supplier.address_line2 or ''}".strip(', ') if supplier else '',
                supplier.country_code if supplier else '',
                supplier.tax_id_no if supplier else '',
                buyer.name if buyer else '',
                f"{buyer.address_line1}, {buyer.address_line2 or ''}".strip(', ') if buyer else '',
                buyer.country_code if buyer else '',
                buyer.tax_id_no if buyer else '',
                ship_to.name if ship_to else '',
                f"{ship_to.address_line1}, {ship_to.address_line2 or ''}".strip(', ') if ship_to else '',
                ship_to.country_code if ship_to else ''
            ])
        
        if include_line_items:
            line_items = invoice_data.line_items.all()
            if line_items:
                avg_unit_price = (sum(item.unit_price for item in line_items) / len(line_items)) if len(line_items) else Decimal('0')
                row.extend([
                    len(line_items),
                    '; '.join([item.product_description for item in line_items]),
                    '; '.join([(item.product_number or '') for item in line_items]),
                    '; '.join([(item.serial_number or '') for item in line_items]),
                    sum(item.quantity_shipped for item in line_items),
                    self._format_money(avg_unit_price, invoice_data.invoice_currency_code)
                ])
            else:
                row.extend(['0', '', '', '', '0', '0'])
        
        return row

    # -------------------------
    # Filename helpers
    # -------------------------
    def _sanitize_filename_component(self, value: Optional[str]) -> str:
        s = (value or '').strip()
        # Replace spaces and disallowed characters
        allowed = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        s = ''.join(ch if ch in allowed else '_' for ch in s)
        s = s.replace(' ', '_')
        # Collapse consecutive underscores
        while '__' in s:
            s = s.replace('__', '_')
        return s or 'unnamed'

    def _build_export_filename(self, jobs: QuerySet[InvoiceProcessingJob]) -> str:
        try:
            jobs_list = list(jobs)
        except Exception:
            jobs_list = []

        # Fallback timestamped name if empty
        if not jobs_list:
            return f"invoice_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        if len(jobs_list) == 1:
            j = jobs_list[0]
            base = os.path.splitext(j.file_name)[0]
            name = f"{self._sanitize_filename_component(base)}_{self._sanitize_filename_component(j.ocr_engine)}_{self._sanitize_filename_component(j.llm_provider)}.csv"
            return name

        # Multiple jobs: summarize engines and llms
        engines = sorted({getattr(j, 'ocr_engine', '') or '' for j in jobs_list})
        llms = sorted({getattr(j, 'llm_provider', '') or '' for j in jobs_list})
        eng_part = engines[0] if len(engines) == 1 else 'mixed'
        llm_part = llms[0] if len(llms) == 1 else 'mixed'
        name = f"batch_{self._sanitize_filename_component(eng_part)}_{self._sanitize_filename_component(llm_part)}.csv"
        return name
    
    def export_line_items(
        self,
        jobs: QuerySet[InvoiceProcessingJob]
    ) -> HttpResponse:
        """Export line items to separate CSV."""
        
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="line_items_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            writer = csv.writer(response)
            
            # Write header
            header = [
                'Job ID',
                'Invoice Number',
                'Line Order',
                'Classification',
                'Product Description',
                'Product Number',
                'Serial Number',
                'Quantity',
                'Unit Price',
                'Extended Value',
                'Tax Rate',
                'Tax Value',
                'Total Value'
            ]
            writer.writerow(header)
            
            # Write line items
            for job in jobs:
                if hasattr(job, 'invoice_data') and job.invoice_data:
                    for line_item in job.invoice_data.line_items.all():
                        row = [
                            job.id,
                            job.invoice_data.unique_invoice_number,
                            line_item.order,
                            line_item.classification or '',
                            line_item.product_description,
                            line_item.product_number or '',
                            line_item.serial_number or '',
                            line_item.quantity_shipped,
                            self._format_money(line_item.unit_price, job.invoice_data.invoice_currency_code),
                            self._format_money(line_item.extended_value, job.invoice_data.invoice_currency_code),
                            str(line_item.tax_rate),
                            self._format_money(line_item.tax_value, job.invoice_data.invoice_currency_code),
                            self._format_money(line_item.total_value_incl_tax, job.invoice_data.invoice_currency_code)
                        ]
                        writer.writerow(row)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error exporting line items CSV: {str(e)}")
            raise
    
    def export_parties(
        self,
        jobs: QuerySet[InvoiceProcessingJob]
    ) -> HttpResponse:
        """Export party information to separate CSV."""
        
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="parties_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            writer = csv.writer(response)
            
            # Write header
            header = [
                'Job ID',
                'Invoice Number',
                'Party Type',
                'Name',
                'Address Line 1',
                'Address Line 2',
                'Postal Code',
                'Country Code',
                'Tax ID',
                'Registration No',
                'Contact Number'
            ]
            writer.writerow(header)
            
            # Write party information
            for job in jobs:
                if hasattr(job, 'invoice_data') and job.invoice_data:
                    for party in job.invoice_data.parties.all():
                        row = [
                            job.id,
                            job.invoice_data.unique_invoice_number,
                            party.party_type,
                            party.name,
                            party.address_line1,
                            party.address_line2 or '',
                            party.postal_code or '',
                            party.country_code or '',
                            party.tax_id_no or '',
                            party.registration_no or '',
                            party.contact_number or ''
                        ]
                        writer.writerow(row)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error exporting parties CSV: {str(e)}")
            raise
