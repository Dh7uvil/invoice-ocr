"""
OCR service for extracting text from PDF documents using various engines.
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import numpy as np

# PyMuPDF - lazy import to avoid memory issues
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# PaddleOCR
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

# Google Document AI
try:
    from google.cloud import documentai
    GOOGLE_DOCUMENT_AI_AVAILABLE = True
except ImportError:
    GOOGLE_DOCUMENT_AI_AVAILABLE = False

# AWS Textract
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_TEXTRACT_AVAILABLE = True
except ImportError:
    AWS_TEXTRACT_AVAILABLE = False

from schemas.invoice_models import OCRResult

logger = logging.getLogger(__name__)


class BaseOCRService(ABC):
    """Base OCR service interface."""
    
    @abstractmethod
    def extract_text(self, file_path: str, **kwargs) -> OCRResult:
        """Extract text from document."""
        pass


class TesseractOCRService(BaseOCRService):
    """Tesseract OCR service."""
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd or os.getenv('TESSERACT_CMD', 'tesseract')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def extract_text(self, file_path: str, **kwargs) -> OCRResult:
        """Extract text using Tesseract OCR."""
        start_time = time.time()
        
        try:
            # Convert PDF to images if needed
            if file_path.lower().endswith('.pdf'):
                images = self._pdf_to_images(file_path)
                text_parts = []
                
                for image in images:
                    text = pytesseract.image_to_string(image, lang=kwargs.get('language', 'eng'))
                    text_parts.append(text)
                
                extracted_text = '\n'.join(text_parts)
            else:
                # Handle image files
                image = Image.open(file_path)
                extracted_text = pytesseract.image_to_string(image, lang=kwargs.get('language', 'eng'))
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=extracted_text.strip(),
                confidence=0.8,  # Tesseract doesn't provide confidence by default
                engine='tesseract',
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {str(e)}")
            raise
    
    def _pdf_to_images(self, pdf_path: str) -> list:
        """Convert PDF to images."""
        try:
            # First try pdf2image
            images = convert_from_path(pdf_path, dpi=300)
            return images
        except Exception as e:
            logger.warning(f"pdf2image failed: {str(e)}, trying PyMuPDF...")
            if PYMUPDF_AVAILABLE:
                try:
                    # Fallback: use PyMuPDF
                    doc = fitz.open(pdf_path)
                    images = []
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                        img_data = pix.tobytes("png")
                        from PIL import Image
                        import io
                        img = Image.open(io.BytesIO(img_data))
                        images.append(img)
                    doc.close()
                    return images
                except Exception as e2:
                    logger.error(f"PyMuPDF failed: {str(e2)}")
                    raise
            else:
                logger.error("PyMuPDF not available and pdf2image failed")
                raise Exception("No PDF processing library available")


class PaddleOCRService(BaseOCRService):
    """PaddleOCR service."""
    
    def __init__(self):
        if not PADDLEOCR_AVAILABLE:
            raise ImportError("PaddleOCR is not installed")
        
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
    
    def extract_text(self, file_path: str, **kwargs) -> OCRResult:
        """Extract text using PaddleOCR."""
        start_time = time.time()
        
        try:
            if file_path.lower().endswith('.pdf'):
                images = self._pdf_to_images(file_path)
                text_parts = []
                
                for image in images:
                    result = self.ocr.ocr(image, use_textline_orientation=True)
                    page_text = self._extract_text_lines_from_paddle_result(result)
                    if page_text:
                        text_parts.append('\n'.join(page_text))
                
                extracted_text = '\n'.join(text_parts)
            else:
                result = self.ocr.ocr(file_path, use_textline_orientation=True)
                text_lines = self._extract_text_lines_from_paddle_result(result)
                extracted_text = '\n'.join(text_lines) if text_lines else ""
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=extracted_text.strip(),
                confidence=0.9,  # PaddleOCR generally has good accuracy
                engine='paddleocr',
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"PaddleOCR failed: {str(e)}")
            raise
    
    def _extract_text_lines_from_paddle_result(self, result) -> list:
        """Support both PaddleOCR <=2.x (list-of-lines) and 3.x (OCRResult object) outputs.
        Returns a list of recognized text lines.
        """
        if not result:
            return []
        first = result[0]
        # New API (3.x): first is OCRResult-like (dict-like) with 'rec_texts'
        try:
            if isinstance(first, dict) or hasattr(first, 'keys'):
                texts = first.get('rec_texts') if isinstance(first, dict) else getattr(first, '__getitem__', None)
                if texts is None and hasattr(first, 'get'):
                    texts = first.get('rec_texts')
                if texts is None:
                    # try attribute access via mapping
                    try:
                        texts = first['rec_texts']  # type: ignore[index]
                    except Exception:
                        texts = None
                if texts and isinstance(texts, list):
                    return [str(t[0] if isinstance(t, tuple) else t) for t in texts]
        except Exception:
            pass
        # Legacy API (2.x): result[0] is a list of lines: [ [box, (text, score)], ... ]
        if isinstance(first, (list, tuple)):
            lines = []
            for item in first:
                try:
                    if item and len(item) >= 2:
                        text_part = item[1]
                        if isinstance(text_part, (list, tuple)) and text_part:
                            lines.append(str(text_part[0]))
                except Exception:
                    continue
            return lines
        return []
    
    def _pdf_to_images(self, pdf_path: str) -> list:
        """Convert PDF to images with fallback to PyMuPDF, returning numpy arrays."""
        # First try pdf2image (requires Poppler). If it fails, fallback to PyMuPDF.
        try:
            pil_images = convert_from_path(pdf_path, dpi=300)
            images_np = [np.array(img.convert('RGB')) for img in pil_images]
            return images_np
        except Exception as e:
            logger.warning(f"pdf2image failed: {str(e)}, trying PyMuPDF...")
            if PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(pdf_path)
                    images_np = []
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        img_data = pix.tobytes("png")
                        from PIL import Image
                        import io
                        img = Image.open(io.BytesIO(img_data)).convert('RGB')
                        images_np.append(np.array(img))
                    doc.close()
                    return images_np
                except Exception as e2:
                    logger.error(f"PyMuPDF failed: {str(e2)}")
                    raise
            else:
                logger.error("PyMuPDF not available and pdf2image failed")
                raise Exception("No PDF processing library available")


class GoogleDocumentAIService(BaseOCRService):
    """Google Document AI service."""
    
    def __init__(self, project_id: str, location: str = 'us'):
        if not GOOGLE_DOCUMENT_AI_AVAILABLE:
            raise ImportError("Google Cloud Document AI is not installed")
        
        self.project_id = project_id
        self.location = location
        self.client = documentai.DocumentProcessorServiceClient()
    
    def extract_text(self, file_path: str, processor_id: Optional[str] = None, **kwargs) -> OCRResult:
        """Extract text using Google Document AI."""
        start_time = time.time()
        
        try:
            if not processor_id:
                raise ValueError("processor_id is required for Google Document AI")
            
            # Read the file
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            # Configure the process request
            name = f"projects/{self.project_id}/locations/{self.location}/processors/{processor_id}"
            
            document = {
                "content": file_content,
                "mime_type": "application/pdf" if file_path.lower().endswith('.pdf') else "image/jpeg"
            }
            
            request = {
                "name": name,
                "document": document
            }
            
            # Process the document
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract text
            extracted_text = document.text
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=extracted_text.strip(),
                confidence=0.95,  # Google Document AI has high accuracy
                engine='google_document_ai',
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Google Document AI failed: {str(e)}")
            raise


class AWSTextractService(BaseOCRService):
    """AWS Textract service."""
    
    def __init__(self, region_name: str = 'us-east-1'):
        if not AWS_TEXTRACT_AVAILABLE:
            raise ImportError("AWS Textract is not installed")
        
        self.client = boto3.client('textract', region_name=region_name)
    
    def extract_text(self, file_path: str, **kwargs) -> OCRResult:
        """Extract text using AWS Textract."""
        start_time = time.time()
        
        try:
            # Read the file
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            # Call Textract
            response = self.client.detect_document_text(
                Document={'Bytes': file_content}
            )
            
            # Extract text from blocks
            text_lines = []
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
            
            extracted_text = '\n'.join(text_lines)
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=extracted_text.strip(),
                confidence=0.9,  # AWS Textract has good accuracy
                engine='aws_textract',
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"AWS Textract failed: {str(e)}")
            raise


class OCRServiceFactory:
    """Factory for creating OCR services."""
    
    @staticmethod
    def create_service(engine: str, **kwargs) -> BaseOCRService:
        """Create OCR service based on engine type."""
        engine = engine.lower()
        
        if engine == 'tesseract':
            return TesseractOCRService(**kwargs)
        elif engine == 'paddleocr':
            if not PADDLEOCR_AVAILABLE:
                raise ImportError("PaddleOCR is not installed")
            return PaddleOCRService()
        elif engine == 'google_document_ai':
            if not GOOGLE_DOCUMENT_AI_AVAILABLE:
                raise ImportError("Google Cloud Document AI is not installed")
            project_id = kwargs.get('project_id') or os.getenv('GOOGLE_PROJECT_ID')
            location = kwargs.get('location') or os.getenv('GOOGLE_LOCATION', 'us')
            return GoogleDocumentAIService(project_id=project_id, location=location)
        elif engine == 'aws_textract':
            if not AWS_TEXTRACT_AVAILABLE:
                raise ImportError("AWS Textract is not installed")
            region_name = kwargs.get('region_name') or os.getenv('AWS_REGION', 'us-east-1')
            return AWSTextractService(region_name=region_name)
        else:
            raise ValueError(f"Unsupported OCR engine: {engine}")


def get_ocr_service(engine: str, **kwargs) -> BaseOCRService:
    """Get OCR service instance."""
    return OCRServiceFactory.create_service(engine, **kwargs)
