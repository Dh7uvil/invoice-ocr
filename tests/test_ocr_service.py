"""
Tests for OCR service.
"""

import pytest
from unittest.mock import Mock, patch
from services.ocr_service import (
    TesseractOCRService,
    PaddleOCRService,
    GoogleDocumentAIService,
    AWSTextractService,
    OCRServiceFactory
)


class TestTesseractOCRService:
    """Test Tesseract OCR service."""
    
    def test_init(self):
        """Test service initialization."""
        service = TesseractOCRService()
        assert service.tesseract_cmd == 'tesseract'
        
        service = TesseractOCRService(tesseract_cmd='/usr/bin/tesseract')
        assert service.tesseract_cmd == '/usr/bin/tesseract'
    
    @patch('pytesseract.image_to_string')
    @patch('PIL.Image.open')
    def test_extract_text_image(self, mock_image_open, mock_ocr):
        """Test text extraction from image."""
        mock_ocr.return_value = "Sample text"
        service = TesseractOCRService()
        
        result = service.extract_text("test.jpg")
        
        assert result.text == "Sample text"
        assert result.engine == "tesseract"
        assert result.confidence == 0.8


class TestOCRServiceFactory:
    """Test OCR service factory."""
    
    def test_create_tesseract_service(self):
        """Test creating Tesseract service."""
        service = OCRServiceFactory.create_service('tesseract')
        assert isinstance(service, TesseractOCRService)
    
    def test_create_unsupported_service(self):
        """Test creating unsupported service."""
        with pytest.raises(ValueError):
            OCRServiceFactory.create_service('unsupported')
