"""
Chandra OCR Service - Extract text from Job Description images/PDFs.

Uses HuggingFace's Chandra OCR model for document extraction.
Returns structured markdown/text from uploaded files.

Environment Variables:
- CHANDRA_ENDPOINT: HuggingFace inference endpoint (default: public API)
- HF_TOKEN: HuggingFace API token for authentication
"""
import os
import re
import io
import logging
import base64
from typing import Tuple, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image
import urllib3

# Disable SSL warnings (we'll handle SSL errors gracefully)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Configuration from environment
CHANDRA_ENDPOINT = os.getenv(
    "CHANDRA_ENDPOINT",
    "https://api-inference.huggingface.co/models/yifeihu/chandra-ocr"
)
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Sections to remove from JD text
REMOVE_SECTIONS = [
    r"(?i)equal\s+opportunity.*?(?=\n\n|\Z)",
    r"(?i)eeo\s+statement.*?(?=\n\n|\Z)",
    r"(?i)we\s+are\s+an\s+equal.*?(?=\n\n|\Z)",
    r"(?i)benefits.*?(?=\n\n|\Z)",
    r"(?i)compensation.*?(?=\n\n|\Z)",
    r"(?i)about\s+the\s+company.*?(?=\n\n|\Z)",
    r"(?i)about\s+us.*?(?=\n\n|\Z)",
    r"(?i)disclaimer.*?(?=\n\n|\Z)",
    r"(?i)legal\s+notice.*?(?=\n\n|\Z)",
]

# Sections to keep
KEEP_KEYWORDS = [
    "requirements",
    "required",
    "qualifications",
    "skills",
    "responsibilities",
    "duties",
    "experience",
    "must have",
    "nice to have",
    "preferred",
    "technical",
]


class ChandraOCRService:
    """
    OCR Service using Chandra model from HuggingFace.
    
    Features:
    - Image/PDF text extraction
    - JD-specific text cleaning
    - Removes legal/benefits sections
    - Keeps requirements and skills sections
    - Robust SSL error handling with fallback
    """
    
    def __init__(self):
        """Initialize OCR service with HuggingFace credentials and SSL retry logic."""
        self.endpoint = CHANDRA_ENDPOINT
        self.headers = {}
        if HF_TOKEN:
            self.headers["Authorization"] = f"Bearer {HF_TOKEN}"
        
        # Create session with retry logic and SSL configuration
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # SSL verification - try to work around SSL issues
        self.session.verify = True  # Will try with verification first
        
        logger.info(f"ChandraOCRService initialized with endpoint: {self.endpoint}")
    
    def extract_text_from_image(self, image_bytes: bytes) -> Tuple[str, dict]:
        """
        Extract text from an image using Chandra OCR.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        logger.info("Extracting text from image using Chandra OCR")
        
        try:
            # First attempt with SSL verification
            response = self._call_huggingface_api(image_bytes, verify_ssl=True)
            
            if response is None:
                # If SSL fails, try without verification
                logger.warning("Retrying HuggingFace API without SSL verification")
                response = self._call_huggingface_api(image_bytes, verify_ssl=False)
            
            if response is None:
                # Both attempts failed, use fallback
                logger.info("HuggingFace API unavailable, using fallback OCR")
                return self._fallback_ocr(image_bytes)
            
            # Parse successful response
            if response.status_code != 200:
                logger.warning(f"OCR API error: {response.status_code} - {response.text[:200]}")
                if response.status_code == 410:
                    logger.info("HuggingFace model deprecated (410), using fallback OCR")
                else:
                    logger.info(f"HuggingFace API error ({response.status_code}), using fallback OCR")
                return self._fallback_ocr(image_bytes)
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict):
                    extracted_text = result[0].get("generated_text", str(result[0]))
                else:
                    extracted_text = str(result[0])
            elif isinstance(result, dict):
                extracted_text = result.get("generated_text", result.get("text", str(result)))
            else:
                extracted_text = str(result)
            
            metadata = {
                "source": "chandra_ocr",
                "endpoint": self.endpoint,
                "raw_length": len(extracted_text)
            }
            
            logger.info(f"OCR extracted {len(extracted_text)} characters")
            return extracted_text, metadata
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}, using fallback")
            return self._fallback_ocr(image_bytes)
    
    def _call_huggingface_api(
        self, 
        image_bytes: bytes, 
        verify_ssl: bool = True,
        timeout: int = 45
    ) -> Optional[requests.Response]:
        """
        Make API call to HuggingFace with SSL error handling.
        
        Args:
            image_bytes: Raw image bytes
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
            
        Returns:
            Response object or None if failed
        """
        try:
            response = self.session.post(
                self.endpoint,
                headers=self.headers,
                data=image_bytes,
                timeout=timeout,
                verify=verify_ssl
            )
            return response
            
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL error with verify={verify_ssl}: {e}")
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout after {timeout}s")
            return None
            
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error calling HuggingFace API: {e}")
            return None
    
    def _fallback_ocr(self, image_bytes: bytes) -> Tuple[str, dict]:
        """
        Fallback OCR using EasyOCR when HuggingFace model fails.
        EasyOCR is preferred over pytesseract as it doesn't require external binaries.
        """
        logger.warning("Using fallback OCR (EasyOCR)")
        
        try:
            import easyocr
            import numpy as np
            from PIL import Image
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert PIL to numpy array for EasyOCR
            img_array = np.array(image)
            
            # Initialize EasyOCR reader (English)
            # This will download models on first run (~40MB)
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            
            # Extract text
            results = reader.readtext(img_array)
            
            # Combine all detected text
            text = ' '.join([result[1] for result in results])
            
            if not text or len(text.strip()) < 10:
                logger.warning("EasyOCR extracted minimal text")
                return "", {"source": "easyocr", "error": "No text extracted"}
            
            logger.info(f"EasyOCR extracted {len(text)} characters")
            return text, {"source": "easyocr", "raw_length": len(text), "blocks": len(results)}
            
        except ImportError:
            logger.error("EasyOCR not installed. Install with: pip install easyocr torch")
            
            # Try pytesseract as last resort
            try:
                import pytesseract
                from PIL import Image
                
                image = Image.open(io.BytesIO(image_bytes))
                text = pytesseract.image_to_string(image)
                
                if not text or len(text.strip()) < 10:
                    return "", {"source": "pytesseract", "error": "No text extracted"}
                
                logger.info(f"Pytesseract extracted {len(text)} characters")
                return text, {"source": "pytesseract", "raw_length": len(text)}
                
            except Exception as e:
                logger.error(f"All OCR fallbacks failed: {e}")
                return "", {"source": "fallback", "error": str(e)}
                
        except Exception as e:
            logger.error(f"EasyOCR fallback failed: {e}")
            return "", {"source": "easyocr", "error": str(e)}
    
    def extract_from_pdf(self, pdf_bytes: bytes) -> Tuple[str, dict]:
        """
        Extract text from PDF (first page as image).
        
        Args:
            pdf_bytes: Raw PDF bytes
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        logger.info("Extracting text from PDF")
        
        try:
            # Try to use pdf2image if available
            from pdf2image import convert_from_bytes
            
            # Convert first page to image
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
            if images:
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                text, metadata = self.extract_text_from_image(img_bytes)
                metadata["source_type"] = "pdf"
                metadata["pages_processed"] = 1
                return text, metadata
            else:
                raise ValueError("No pages extracted from PDF")
                
        except ImportError:
            logger.warning("pdf2image not available, attempting direct text extraction")
            # Fallback: try PyPDF2 for text-based PDFs
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
                text = ""
                for page in pdf_reader.pages[:3]:  # First 3 pages
                    text += page.extract_text() + "\n"
                return text, {"source": "pypdf2", "pages": len(pdf_reader.pages)}
            except Exception as e:
                logger.error(f"PDF text extraction failed: {e}")
                raise
    
    def clean_jd_text(self, raw_text: str) -> str:
        """
        Clean JD text by removing irrelevant sections.
        
        Removes:
        - EEO/legal disclaimers
        - Benefits sections
        - Company descriptions
        
        Keeps:
        - Requirements
        - Skills
        - Responsibilities
        
        Args:
            raw_text: Raw OCR output
            
        Returns:
            Cleaned text focused on job requirements
        """
        logger.info("Cleaning JD text")
        
        if not raw_text:
            return ""
        
        cleaned = raw_text
        
        # Remove unwanted sections
        for pattern in REMOVE_SECTIONS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)
        
        # Normalize whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        cleaned = cleaned.strip()
        
        logger.info(f"Cleaned text: {len(raw_text)} -> {len(cleaned)} chars")
        return cleaned
    
    async def process_upload(
        self, 
        file_content: bytes, 
        content_type: str
    ) -> Tuple[str, dict]:
        """
        Process uploaded file (image or PDF).
        
        Args:
            file_content: Raw file bytes
            content_type: MIME type of file
            
        Returns:
            Tuple of (cleaned_text, metadata)
        """
        logger.info(f"Processing upload: {content_type}")
        
        # Determine file type
        if "pdf" in content_type.lower():
            raw_text, metadata = self.extract_from_pdf(file_content)
        elif any(t in content_type.lower() for t in ["image", "png", "jpg", "jpeg"]):
            raw_text, metadata = self.extract_text_from_image(file_content)
        else:
            raise ValueError(f"Unsupported file type: {content_type}")
        
        # Clean the text
        cleaned_text = self.clean_jd_text(raw_text)
        metadata["cleaned_length"] = len(cleaned_text)
        
        return cleaned_text, metadata


# Module-level singleton
_ocr_service = None

def get_ocr_service() -> ChandraOCRService:
    """Get or create OCR service singleton."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = ChandraOCRService()
    return _ocr_service
