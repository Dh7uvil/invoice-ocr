"""
Pydantic models for invoice data structure.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LineItem(BaseModel):
    """Detailed information for a single line item."""
    classification: Optional[str] = Field(None, description="Product classification, e.g. 'COMPUTER, SMARTPHONE'")
    product_description: str = Field(..., description="Product description, e.g. 'MBA 15 MDN/10C CPU/10C GPU/24GB/1TB/KB-US/ITP' or 'ThinkPad T16 G3'")
    product_number: Optional[str] = Field(None, description="Product number/SKU, e.g. 'Z1DH' or '21MN0065MY'")
    quantity_shipped: int = Field(..., description="Quantity shipped")
    serial_number: Optional[str] = Field(None, description="Product serial number, e.g. 'FG9216QWO7'")
    unit_price: float = Field(..., description="Unit price (Value Per Unit/Unit Price)")
    extended_value: float = Field(..., description="Line item total excluding tax (Extended Value)")
    tax_rate: float = Field(..., description="Line item tax rate, e.g. 0.00%")
    tax_value: float = Field(..., description="Line item tax amount")
    total_value_incl_tax: float = Field(..., description="Line item total including tax")


class PartyInfo(BaseModel):
    """Common structure for supplier, buyer, or recipient information."""
    name: str = Field(..., description="Name (Supplier Name / Buyer Name / Recipient Name)")
    address_line1: str = Field(..., description="Address line 1 (street/floor)")
    address_line2: Optional[str] = Field(None, description="Address line 2 (city/region)")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country_code: Optional[str] = Field(None, description="Country code, e.g. 'MY'")
    tax_id_no: Optional[str] = Field(None, description="Tax ID / TIN / SST No.")
    registration_no: Optional[str] = Field(None, description="Company registration number")
    contact_number: Optional[str] = Field(None, description="Contact phone number")


class InvoiceData(BaseModel):
    """Complete invoice data structure."""
    
    # --- Basic information ---
    invoice_file_name: str = Field(..., description="Source file name")
    unique_invoice_number: str = Field(..., description="Unique invoice number, e.g. '90N4RSST8MVC799ETMHBS17K10' or 'H121058044'")
    invoice_date: str = Field(..., description="Invoice date and time, e.g. '08/10/2025 08:00:00' or '14-Aug-2025'")
    due_date: str = Field(..., description="Invoice due date")
    purchase_order_number: Optional[str] = Field(None, description="Purchase order number (PO No), e.g. 'R7422213857268'")
    
    # --- Party information ---
    supplier_info: PartyInfo = Field(..., description="Supplier information")
    buyer_info: PartyInfo = Field(..., description="Buyer/billing information (Sold To / Invoice To)")
    ship_to_info: PartyInfo = Field(..., description="Ship-to/delivery information (Ship To)")
    
    # --- Line items ---
    invoice_currency_code: str = Field(..., description="Invoice currency code, e.g. 'MYR'")
    line_items: List[LineItem] = Field(..., description="List of all line items")
    
    # --- Financial summary ---
    total_value_excl_tax: float = Field(..., description="Total value excluding tax")
    total_tax_value: float = Field(..., description="Total tax amount")
    total_payable_value: float = Field(..., description="Total amount payable (Total Value Incl Tax / Amount Payable)")


class OCRResult(BaseModel):
    """OCR processing result."""
    text: str = Field(..., description="Extracted text content")
    confidence: float = Field(..., description="Confidence score")
    engine: str = Field(..., description="OCR engine used")
    processing_time: float = Field(..., description="Processing time in seconds")


class ProcessingStatus(BaseModel):
    """Processing status."""
    status: str = Field(..., description="Processing status: pending, processing, completed, failed")
    message: Optional[str] = Field(None, description="Status message")
    progress: int = Field(0, description="Processing progress percentage")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class InvoiceProcessingRequest(BaseModel):
    """Invoice processing request."""
    file_path: str = Field(..., description="File path")
    ocr_engine: str = Field(..., description="OCR engine")
    llm_provider: str = Field(..., description="LLM provider")
    model_name: Optional[str] = Field(None, description="Model name")
    language: str = Field(default="en", description="Language code")


class InvoiceProcessingResponse(BaseModel):
    """Invoice processing response."""
    success: bool = Field(..., description="Whether processing succeeded")
    invoice_data: Optional[InvoiceData] = Field(None, description="Parsed invoice data")
    ocr_result: Optional[OCRResult] = Field(None, description="OCR result")
    error_message: Optional[str] = Field(None, description="Error message")
    processing_time: float = Field(..., description="Total processing time in seconds")
