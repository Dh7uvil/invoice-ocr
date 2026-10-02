# Invoice OCR Parser

A comprehensive invoice parsing system using Python, LangChain, and various LLM providers to extract structured data from PDF invoices.

**Case Study:** [Automated Invoice Data Extraction](docs/CASE_STUDY.md)

## Features

- **Multiple OCR Engines**: Support for Tesseract, PaddleOCR, Google Document AI, and AWS Textract
- **Flexible LLM Integration**: OpenAI GPT, Google Gemini, and other LLM providers
- **Structured Output**: Uses Pydantic models for consistent data extraction
- **Database Support**: SQLite and PostgreSQL with environment-based configuration
- **CSV Export**: Export parsed invoice data to CSV format
- **Modern Stack**: Django 5.1.7, LangChain, LangGraph, and Langfuse for tracking

## Quick Start

### Prerequisites

- Python 3.12+
- pip
- Redis (for Celery)
- Tesseract (for OCR)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd invoice-ocr
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment configuration:
```bash
cp env.example .env
```

4. Configure your environment variables in `.env`

5. Run database migrations:
```bash
python manage.py migrate
```

6. Start the development server:
```bash
python manage.py runserver
```

7. Start Celery worker (in another terminal):
```bash
python -m celery -A invoice_ocr worker --loglevel=info -P solo -E

# python -m celery -A tasks.simple_test worker --loglevel=info -P solo -E
```

8. Start Flower monitoring (optional) (Flower 2.x CLI):
```bash
python -m celery --broker=redis://localhost:6379/0 --result-backend=redis://localhost:6379/0 -A invoice_ocr flower --port=5555

# python -m flower \
#   --app=tasks.simple_test \
#   --broker=redis://localhost:6379/0 \
#   --result-backend=redis://localhost:6379/0 \
#   --url-prefix=/flower \
#   --port=5555 \
#   --basic-auth=admin:admin123
```

9. Access the services:
- Django Admin: http://localhost:8000/admin/
- Flower Monitoring: http://localhost:5555/flower (admin/admin123)

## Configuration

### OCR Engines

The system supports multiple OCR engines:

- **Tesseract**: Free, open-source OCR engine
- **PaddleOCR**: Advanced OCR with better accuracy
- **Google Document AI**: Cloud-based document understanding
- **AWS Textract**: Amazon's document analysis service

### LLM Providers

- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Google**: Gemini Pro
- **AWS**: Bedrock models

### Database

Configure your database in the `.env` file:

```env
# SQLite (default)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///db.sqlite3

# PostgreSQL
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:password@localhost:5432/invoice_ocr
```

## API Usage

### Upload and Parse Invoice

```bash
curl -X POST http://localhost:8000/api/invoices/upload/ \
  -F "file=@invoice.pdf" \
  -F "ocr_engine=tesseract" \
  -F "llm_provider=openai"
```

### Export to CSV

```bash
curl -X GET http://localhost:8000/api/invoices/export/csv/
```

## Project Structure

```
invoice-ocr/
├── invoice_ocr/           # Django project
├── ocr_app/              # Main application
├── prompts/              # LLM prompt templates
├── schemas/              # Pydantic models
├── services/             # Business logic
├── tasks/               # Celery tasks
└── tests/               # Test files
```

## Development

### Code Quality

```bash
# Format code
black .
isort .

# Lint code
flake8
mypy

# Run tests
pytest
```

### Pre-commit Hooks

```bash
pre-commit install
```