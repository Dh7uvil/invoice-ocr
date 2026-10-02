# Case Study: Automated Invoice Data Extraction

## Overview

This project is an end-to-end invoice parsing system that turns unstructured PDF and image invoices into structured, queryable data. It combines OCR for text extraction with large language models (LLMs) for semantic parsing, wrapped in a Django application with asynchronous job processing.

## The Problem

Finance and operations teams routinely receive invoices in PDF or scanned image formats. Manually keying in invoice numbers, dates, line items, tax totals, and supplier details is slow, error-prone, and does not scale.

Typical pain points:

- Inconsistent invoice layouts across vendors
- Mixed document quality (scans, photos, multi-page PDFs)
- Need for structured output that integrates with accounting or ERP workflows
- Manual review bottlenecks when volume spikes

## The Solution

Invoice OCR Parser automates the full pipeline:

1. **Upload** — Users submit invoices via the Django admin UI or REST API
2. **OCR** — Text is extracted using a configurable engine (Tesseract, PaddleOCR, Google Document AI, or AWS Textract)
3. **LLM parsing** — An LLM maps raw text into a strict Pydantic schema (parties, line items, totals)
4. **Storage** — Parsed results are saved as `InvoiceData` records with related party and line-item entities
5. **Export** — Data can be exported to CSV for downstream systems

Processing runs asynchronously via Celery, so uploads return immediately while jobs progress in the background.

## Architecture

```
PDF/Image Upload
       │
       ▼
InvoiceProcessingJob (Celery task)
       │
       ├── OCR Service ──► raw text + confidence
       │
       └── LLM Service ──► structured JSON (Pydantic-validated)
                │
                ▼
         InvoiceData + PartyInfo + LineItem
                │
                ▼
         Admin UI / REST API / CSV Export
```

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| Pluggable OCR engines | Lets teams trade off cost, accuracy, and on-prem vs cloud requirements |
| Pluggable LLM providers | Avoids vendor lock-in; supports OpenAI, Google Gemini, and AWS Bedrock |
| Pydantic schema enforcement | Guarantees consistent output shape regardless of LLM or invoice format |
| Async Celery workers | Keeps the API responsive for large or batch uploads |
| Read-only parsed records | Prevents manual edits that would diverge from source documents |

## Data Extracted

For each invoice, the system extracts:

- **Header fields** — Invoice number, date, due date, PO number, currency
- **Parties** — Supplier, buyer, and ship-to addresses with tax IDs
- **Line items** — Description, quantity, unit price, tax rate, line totals
- **Financial summary** — Subtotal, tax, and amount payable

## Workflow Example

1. An operator uploads `vendor-invoice-2025.pdf` through the admin panel
2. They select PaddleOCR for OCR and OpenAI GPT for structured parsing
3. A Celery worker picks up the job, extracts text, and sends it to the LLM with a schema-aware prompt
4. The LLM returns JSON; the service validates it against the Pydantic model and fills missing defaults
5. The operator reviews the completed job and exports selected invoices to CSV

Job status, progress, and processing logs are visible in the admin UI. Flower can be used to monitor Celery workers in production.

## Results

After deployment, teams can:

- Reduce manual data entry for standard invoice fields
- Process invoices in parallel via background workers
- Switch OCR/LLM providers per document type or cost constraints
- Integrate parsed data through the REST API or CSV export

Exact accuracy depends on document quality and the OCR/LLM combination chosen. Cloud OCR engines (Google Document AI, AWS Textract) generally perform best on complex layouts; Tesseract and PaddleOCR work well for simpler documents at lower cost.

## Technology Stack

- **Backend:** Django 5, Django REST Framework
- **Task queue:** Celery + Redis
- **OCR:** Tesseract, PaddleOCR, Google Document AI, AWS Textract
- **LLM:** LangChain integrations for OpenAI, Google Gemini, AWS Bedrock
- **Validation:** Pydantic models
- **Database:** SQLite (development) or PostgreSQL (production)

## Lessons Learned

1. **OCR quality drives LLM quality** — Garbage text in leads to poor structured output; choosing the right OCR engine matters more than tuning prompts alone.
2. **Schema-first parsing beats free-form extraction** — Enforcing a Pydantic schema with default-fill logic makes downstream storage reliable even when the LLM omits fields.
3. **Async processing is essential** — OCR and LLM calls are slow; Celery keeps the user experience responsive.
4. **Provider flexibility reduces risk** — Supporting multiple OCR and LLM backends lets teams adapt as pricing, accuracy, or compliance requirements change.

## Next Steps

- Batch upload via API for high-volume ingestion
- Confidence thresholds to flag invoices for human review
- Webhook notifications when jobs complete
- Custom field mappings for specific ERP integrations
