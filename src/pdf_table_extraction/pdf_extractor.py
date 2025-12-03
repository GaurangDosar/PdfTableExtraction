from __future__ import annotations

import io
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
from PIL import Image

try:  # Optional dependency
    import pytesseract
except ImportError:  # pragma: no cover - optional
    pytesseract = None

from .config import ExtractionConfig
from .utils import logger


class PDFExtractor:
    """Extract tables from PDF using PyMuPDF's built-in table detection."""
    
    def __init__(self, config: ExtractionConfig) -> None:
        self.config = config
        self.pdf_path = Path(config.pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {self.pdf_path}")

    def extract(self) -> tuple[List[Dict[str, Any]], str]:
        """
        Extract all tables from PDF and document context.
        Returns tuple of (tables, document_context) where tables is list of dicts:
        {
            'table_id': 'page-1-table-1',
            'page_number': 1,
            'headers': [...],
            'rows': [[...], [...], ...]
        }
        and document_context is extracted text/metadata for year inference.
        """
        logger.info(f"Starting PyMuPDF table extraction for {self.pdf_path}")
        tables = []
        
        with fitz.open(self.pdf_path) as doc:
            # Extract document context (title, metadata, first page text)
            document_context = self._extract_document_context(doc)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_tables = self._extract_tables_from_page(page, page_num + 1)
                tables.extend(page_tables)
                
                # Fallback to OCR if requested and no tables found
                if not page_tables and self.config.use_ocr:
                    logger.info(f"No tables on page {page_num + 1}, trying OCR...")
                    ocr_tables = self._extract_with_ocr(page, page_num + 1)
                    tables.extend(ocr_tables)
        
        logger.info(f"Extracted {len(tables)} tables from PDF")
        return tables, document_context

    def _extract_tables_from_page(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """Extract tables from a single page using PyMuPDF."""
        tables = []
        
        try:
            # Extract full page text for table title detection
            page_text = page.get_text()
            
            # Find all tables on the page
            table_finder = page.find_tables()
            
            if not table_finder.tables:
                logger.debug(f"No tables detected on page {page_number}")
                return tables
            
            for idx, table in enumerate(table_finder.tables, start=1):
                table_data = table.extract()
                
                if not table_data or len(table_data) < 2:  # Need at least header + 1 row
                    logger.debug(f"Skipping empty/invalid table on page {page_number}")
                    continue
                
                # Separate headers and rows
                headers = [str(cell).strip() if cell else "" for cell in table_data[0]]
                rows = [
                    [str(cell).strip() if cell else "" for cell in row]
                    for row in table_data[1:]
                ]
                
                # Try to extract table title from text above the table
                table_title = self._extract_table_title(page_text, table, idx)
                
                table_id = f"page-{page_number}-table-{idx}"
                tables.append({
                    'table_id': table_id,
                    'page_number': page_number,
                    'table_title': table_title,  # Add table title
                    'headers': headers,
                    'rows': rows,
                })
                logger.info(f"Extracted {table_id}: {len(headers)} cols, {len(rows)} rows | title: {table_title or 'none'}")
                
        except Exception as e:
            logger.error(f"Error extracting tables from page {page_number}: {e}")
        
        return tables

    def _extract_document_context(self, doc: fitz.Document) -> str:
        """Extract document context for year inference (title, metadata, first page header)."""
        context_parts = []
        
        # Extract metadata
        metadata = doc.metadata
        if metadata:
            title = metadata.get('title', '').strip()
            subject = metadata.get('subject', '').strip()
            if title:
                context_parts.append(f"Title: {title}")
            if subject:
                context_parts.append(f"Subject: {subject}")
        
        # Extract first page text (increased to 1000 chars for better year detection)
        if len(doc) > 0:
            first_page = doc[0]
            text = first_page.get_text().strip()[:1000]
            if text:
                context_parts.append(f"First page text: {text}")
                
                # Extract years from text for explicit year hints
                import re
                years_found = re.findall(r'\b(20[2-3][0-9])\b', text)
                if years_found:
                    unique_years = sorted(set(years_found))
                    context_parts.append(f"Years mentioned: {', '.join(unique_years)}")
        
        return " | ".join(context_parts) if context_parts else "No document context available"

    def _extract_table_title(self, page_text: str, table: Any, table_index: int) -> str:
        """
        Extract table title from text above the table.
        Looks for patterns like "Table N:", "Table N -", or nearby text.
        """
        import re
        
        # Look for "Table N:" or "Table N -" patterns
        patterns = [
            rf"Table\s+{table_index}\s*[:\-]\s*([^\n]+)",  # "Table 1: Title"
            rf"Table\s+{table_index}[^\n]*\n([^\n]+)",     # "Table 1\nTitle"
            r"Table\s+\d+\s*[:\-]\s*([^\n]+)",             # Any "Table N: Title"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up common suffixes and extra info
                title = re.sub(r'\s*\(\d{4}[–—-]\d{4}\)', '', title)  # Remove year ranges like "(2023-2025)"
                title = title.split('\n')[0]  # Take only first line
                if len(title) > 5 and len(title) < 100:  # Reasonable title length
                    return title
        
        return None

    def _extract_with_ocr(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """Fallback: OCR the page and attempt to find table structure."""
        if pytesseract is None:
            logger.warning("pytesseract not installed; skipping OCR")
            return []
        
        try:
            # Render page to image
            pix = page.get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            
            # OCR the image
            text = pytesseract.image_to_string(image, lang=self.config.language)
            
            # Simple heuristic: split by lines and look for table-like patterns
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if not lines:
                return []
            
            # Treat first line as headers, rest as rows
            headers = lines[0].split()
            rows = [line.split() for line in lines[1:]]
            
            table_id = f"page-{page_number}-table-ocr"
            logger.info(f"OCR extracted {table_id}: {len(rows)} rows")
            
            return [{
                'table_id': table_id,
                'page_number': page_number,
                'table_title': None,  # OCR doesn't extract titles separately
                'headers': headers,
                'rows': rows,
            }]
            
        except Exception as e:
            logger.error(f"OCR failed on page {page_number}: {e}")
            return []


__all__ = ["PDFExtractor"]
