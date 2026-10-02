# Invoice OCR Usage Guide

## Correct Workflow

### What Not To Do
Do not manually add data in `InvoiceData`. That data should be generated automatically through OCR parsing.

### Correct Steps

#### 1. Create a Processing Job
- Visit: http://localhost:8000/admin/ocr_app/invoiceprocessingjob/
- Click "Add" to create a new processing job
- Upload a PDF invoice file
- Select an OCR engine and LLM provider
- Save the job

#### 2. Automatic Processing
The system will automatically:
1. **OCR text recognition**: Extract text from the PDF
2. **AI structured parsing**: Use an LLM to extract structured data
3. **Save results**: Automatically create `InvoiceData` records

#### 3. View Parsed Results
- Visit: http://localhost:8000/admin/ocr_app/invoicedata/
- View the auto-generated invoice data
- All fields are populated automatically via OCR and AI

## Data Flow

```
PDF Upload → InvoiceProcessingJob → OCR Processing → LLM Parsing → InvoiceData
     ↓              ↓                    ↓               ↓            ↓
  File Storage   Job Record          Text Extraction  Structured   Final Result
```

## Configuration Options

### OCR Engine Selection
- **Tesseract**: Free, suitable for simple documents
- **PaddleOCR**: High accuracy, suitable for complex layouts
- **Google Document AI**: Cloud service, highest accuracy
- **AWS Textract**: Cloud service, enterprise-grade

### LLM Provider Selection
- **OpenAI**: GPT-4/GPT-3.5, general-purpose
- **Google**: Gemini Pro, multi-language support
- **AWS**: Bedrock, enterprise-grade service

## Parsed Result Fields

The system automatically extracts the following information:

### Basic Information
- Invoice number (`unique_invoice_number`)
- Invoice date (`invoice_date`)
- Due date (`due_date`)
- Purchase order number (`purchase_order_number`)

### Party Information
- Supplier info (`supplier_info`)
- Buyer info (`buyer_info`)
- Ship-to info (`ship_to_info`)

### Financial Information
- Currency (`invoice_currency_code`)
- Total excluding tax (`total_value_excl_tax`)
- Tax amount (`total_tax_value`)
- Total payable (`total_payable_value`)

### Line Items
- Product description (`product_description`)
- Quantity (`quantity_shipped`)
- Unit price (`unit_price`)
- Tax value (`tax_value`)

## Quick Start

1. **Start the server**: `python manage.py runserver`
2. **Open admin**: http://localhost:8000/admin/
3. **Log in**: admin / admin123
4. **Create a job**: Invoice Processing Jobs → Add
5. **Upload a PDF**: Drag and drop or select a file
6. **Wait for completion**: Watch the status change
7. **View results**: Invoice Data → View parsed results

## Notes

- `InvoiceData` is read-only and cannot be edited manually
- All data is generated automatically via OCR and AI
- Processing time depends on file size and selected engine
- Ensure API keys are configured correctly
