# Deployment Guide

## Production Deployment

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

### Environment Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd invoice-ocr
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp env.example .env
# Edit .env with your configuration
```

### Database Setup

#### PostgreSQL (Recommended)

1. **Install PostgreSQL**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

2. **Create database**
```sql
CREATE DATABASE invoice_ocr;
CREATE USER invoice_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE invoice_ocr TO invoice_user;
```

3. **Configure Django**
```env
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://invoice_user:your_password@localhost:5432/invoice_ocr
```

#### SQLite (Development)

```env
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///db.sqlite3
```

### Redis Setup

1. **Install Redis**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# Download from https://github.com/microsoftarchive/redis/releases
```

2. **Start Redis**
```bash
redis-server
```

### OCR Engine Setup

#### Tesseract (Default)

1. **Install Tesseract**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# macOS
brew install tesseract

# Windows
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

2. **Configure**
```env
OCR_ENGINE=tesseract
TESSERACT_CMD=tesseract
```

#### PaddleOCR

1. **Install PaddleOCR**
```bash
pip install paddlepaddle paddleocr
```

2. **Configure**
```env
OCR_ENGINE=paddleocr
```

#### Google Document AI

1. **Setup Google Cloud**
```bash
# Install Google Cloud SDK
# Create service account and download JSON key
```

2. **Configure**
```env
OCR_ENGINE=google_document_ai
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_LOCATION=us
```

#### AWS Textract

1. **Setup AWS**
```bash
# Install AWS CLI
pip install boto3
```

2. **Configure**
```env
OCR_ENGINE=aws_textract
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

### LLM Provider Setup

#### OpenAI

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
```

#### Google Gemini

```env
GOOGLE_API_KEY=your-google-api-key
```

#### AWS Bedrock

```env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

### Django Configuration

1. **Run migrations**
```bash
python manage.py migrate
```

2. **Create superuser**
```bash
python manage.py createsuperuser
```

3. **Collect static files**
```bash
python manage.py collectstatic
```

### Celery Configuration

1. **Start Celery worker**
```bash
celery -A invoice_ocr worker --loglevel=info
```

2. **Start Celery beat (optional)**
```bash
celery -A invoice_ocr beat --loglevel=info
```

### Web Server

#### Development

```bash
python manage.py runserver 0.0.0.0:8000
```

#### Production with Gunicorn

```bash
gunicorn invoice_ocr.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

#### Production with Nginx

1. **Install Nginx**
```bash
sudo apt-get install nginx
```

2. **Configure Nginx**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /path/to/invoice-ocr/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/invoice-ocr/media/;
    }
}
```

### Docker Deployment

1. **Build and start services**
```bash
docker-compose up -d
```

2. **Run migrations**
```bash
docker-compose exec web python manage.py migrate
```

3. **Create superuser**
```bash
docker-compose exec web python manage.py createsuperuser
```

### Monitoring

#### Logs

```bash
# Django logs
tail -f logs/django.log

# Celery logs
celery -A invoice_ocr worker --loglevel=info

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

#### Health Checks

```bash
# Check Django
curl http://localhost:8000/admin/

# Check Celery
celery -A invoice_ocr inspect active

# Check Redis
redis-cli ping
```

### Security Considerations

1. **Environment Variables**
   - Never commit `.env` files
   - Use strong passwords
   - Rotate API keys regularly

2. **Database Security**
   - Use strong database passwords
   - Enable SSL connections
   - Restrict database access

3. **File Upload Security**
   - Validate file types
   - Limit file sizes
   - Scan uploaded files

4. **API Security**
   - Use HTTPS in production
   - Implement rate limiting
   - Use authentication tokens

### Backup Strategy

1. **Database Backup**
```bash
# PostgreSQL
pg_dump invoice_ocr > backup.sql

# SQLite
cp db.sqlite3 backup.sqlite3
```

2. **File Backup**
```bash
# Backup uploaded files
tar -czf media_backup.tar.gz media/
```

3. **Automated Backup**
```bash
# Add to crontab
0 2 * * * /path/to/backup_script.sh
```

### Scaling

1. **Horizontal Scaling**
   - Use load balancer
   - Multiple Django instances
   - Multiple Celery workers

2. **Database Scaling**
   - Read replicas
   - Connection pooling
   - Database clustering

3. **File Storage**
   - Use cloud storage (S3, GCS)
   - CDN for static files
   - File compression

### Troubleshooting

#### Common Issues

1. **OCR Engine Not Found**
   - Check Tesseract installation
   - Verify PATH environment variable

2. **Database Connection Failed**
   - Check database credentials
   - Verify database server is running

3. **Celery Worker Not Processing**
   - Check Redis connection
   - Verify Celery configuration

4. **File Upload Issues**
   - Check file permissions
   - Verify disk space
   - Check file size limits

#### Debug Mode

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

#### Performance Monitoring

```bash
# Monitor system resources
htop
iotop
nethogs

# Monitor Django
python manage.py shell
>>> from django.db import connection
>>> connection.queries
```
