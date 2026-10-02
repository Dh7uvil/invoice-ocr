# Invoice OCR API Documentation

## Overview

The Invoice OCR API provides endpoints for uploading, processing, and exporting invoice data using various OCR engines and LLM providers.

## Base URL

```
http://localhost:8000/api/
```

## Authentication

All endpoints require authentication. Use Django's built-in authentication system.

## Endpoints

### 1. Upload Invoice

**POST** `/invoices/upload/`

Upload a PDF or image file for processing.

#### Request

- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file` (required): PDF or image file
  - `ocr_engine` (optional): OCR engine to use (`tesseract`, `paddleocr`, `google_document_ai`, `aws_textract`)
  - `llm_provider` (optional): LLM provider (`openai`, `google`, `aws`)
  - `llm_model` (optional): Specific model name
  - `language` (optional): Language code (default: `en`)

#### Response

```json
{
  "message": "Invoice uploaded successfully",
  "job_id": 123,
  "status": "pending"
}
```

### 2. Get Job Status

**GET** `/jobs/{job_id}/status/`

Get the status of a processing job.

#### Response

```json
{
  "id": 123,
  "file_name": "invoice.pdf",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": "2024-01-01T10:05:00Z",
  "invoice_data": {
    "unique_invoice_number": "INV-001",
    "invoice_date": "2024-01-01",
    "total_payable_value": 1000.00,
    "line_items": [...],
    "parties": [...]
  }
}
```

### 3. List Jobs

**GET** `/jobs/`

List all processing jobs.

#### Query Parameters

- `status`: Filter by status (`pending`, `processing`, `completed`, `failed`)
- `page`: Page number
- `page_size`: Items per page

#### Response

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/jobs/?page=2",
  "previous": null,
  "results": [...]
}
```

### 4. Export CSV

**GET** `/invoices/export/csv/`

Export processed invoice data to CSV format.

#### Query Parameters

- `start_date`: Filter by start date
- `end_date`: Filter by end date
- `status`: Filter by status
- `ocr_engine`: Filter by OCR engine
- `llm_provider`: Filter by LLM provider
- `include_line_items`: Include line items (default: true)
- `include_parties`: Include party information (default: true)

#### Response

Returns a CSV file with invoice data.

### 5. Delete Job

**DELETE** `/jobs/{job_id}/delete/`

Delete a processing job and its associated data.

#### Response

```json
{
  "message": "Job deleted successfully"
}
```

## Data Models

### Invoice Data Structure

```json
{
  "invoice_file_name": "invoice.pdf",
  "unique_invoice_number": "INV-001",
  "invoice_date": "2024-01-01",
  "due_date": "2024-01-31",
  "purchase_order_number": "PO-123",
  "supplier_info": {
    "name": "Supplier Company",
    "address_line1": "123 Main St",
    "address_line2": "Suite 100",
    "postal_code": "12345",
    "country_code": "US",
    "tax_id_no": "123456789",
    "registration_no": "REG-001",
    "contact_number": "+1-555-1234"
  },
  "buyer_info": {
    "name": "Buyer Company",
    "address_line1": "456 Oak Ave",
    "address_line2": null,
    "postal_code": "67890",
    "country_code": "US",
    "tax_id_no": "987654321",
    "registration_no": null,
    "contact_number": "+1-555-5678"
  },
  "ship_to_info": {
    "name": "Shipping Address",
    "address_line1": "789 Pine St",
    "address_line2": null,
    "postal_code": "11111",
    "country_code": "US",
    "tax_id_no": null,
    "registration_no": null,
    "contact_number": null
  },
  "invoice_currency_code": "USD",
  "line_items": [
    {
      "classification": "Electronics",
      "product_description": "Laptop Computer",
      "product_number": "LAP-001",
      "quantity_shipped": 1,
      "serial_number": "SN123456",
      "unit_price": 1000.00,
      "extended_value": 1000.00,
      "tax_rate": 8.5,
      "tax_value": 85.00,
      "total_value_incl_tax": 1085.00
    }
  ],
  "total_value_excl_tax": 1000.00,
  "total_tax_value": 85.00,
  "total_payable_value": 1085.00
}
```

## Error Responses

### 400 Bad Request

```json
{
  "error": "Invalid file format",
  "details": "Only PDF and image files are supported"
}
```

### 401 Unauthorized

```json
{
  "error": "Authentication required"
}
```

### 403 Forbidden

```json
{
  "error": "Permission denied"
}
```

### 404 Not Found

```json
{
  "error": "Job not found"
}
```

### 500 Internal Server Error

```json
{
  "error": "Processing failed",
  "details": "OCR engine error"
}
```

## Rate Limits

- Upload: 10 requests per minute
- API calls: 100 requests per minute

## Examples

### Upload Invoice with cURL

```bash
curl -X POST http://localhost:8000/api/invoices/upload/ \
  -H "Authorization: Bearer your-token" \
  -F "file=@invoice.pdf" \
  -F "ocr_engine=tesseract" \
  -F "llm_provider=openai"
```

### Check Job Status

```bash
curl -X GET http://localhost:8000/api/jobs/123/status/ \
  -H "Authorization: Bearer your-token"
```

### Export CSV

```bash
curl -X GET "http://localhost:8000/api/invoices/export/csv/?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer your-token" \
  -o invoices.csv
```
