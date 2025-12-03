from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

from .config import ExtractionConfig, PipelineConfig
from .llm_client import LLMClient
from .utils import logger
from .models import NormalizedRow
from .pdf_extractor import PDFExtractor
from .llm_services import TableNormalizer, TableValidator


def run_pipeline(pdf_path: str | Path, *, output_csv: str | Path | None = None, use_ocr: bool = False) -> dict:
    """
    Simplified pipeline:
    1. Extract tables using PyMuPDF
    2. Normalize each table with LLM
    3. Save to CSV
    4. Optional validation
    """
    pdf_path = Path(pdf_path)
    extraction = ExtractionConfig(pdf_path=pdf_path, use_ocr=use_ocr)
    config = PipelineConfig(extraction=extraction)
    if output_csv is not None:
        config.output_csv = Path(output_csv)
    
    llm_client = LLMClient(config.llm)
    
    # Step 1: Extract tables and document context using PyMuPDF
    extractor = PDFExtractor(config.extraction)
    tables, document_context = extractor.extract()
    
    if not tables:
        logger.error("No tables found in PDF!")
        return {
            "status": "failed",
            "reason": "no_tables_found",
            "total_tables": 0,
            "total_rows": 0
        }
    
    logger.info(f"Found {len(tables)} tables, proceeding to normalization...")
    logger.info(f"Document context: {document_context[:200]}...")
    
    # Step 2: Normalize each table with LLM (with document context)
    normalizer = TableNormalizer(llm_client)
    consolidated_rows: List[NormalizedRow] = []
    rows_per_table: Dict[str, int] = {}
    
    for table in tables:
        try:
            rows, notes = normalizer.normalize(table, document_context=document_context)
            table_id = table.get('table_id', 'unknown')
            logger.info(f"✓ Normalized {table_id}: {len(rows)} rows | notes: {notes[:100] if notes else 'none'}")
            consolidated_rows.extend(rows)
            rows_per_table[table_id] = len(rows)
        except Exception as e:
            logger.error(f"✗ Failed to normalize table {table.get('table_id')}: {e}")
            continue
    
    if not consolidated_rows:
        logger.error("No rows were successfully normalized!")
        return {
            "status": "failed",
            "reason": "normalization_failed",
            "total_tables": len(tables),
            "total_rows": 0
        }
    
    # Step 3: Save to CSV
    df = pd.DataFrame([row.model_dump() for row in consolidated_rows])
    # Remove source_table column from output
    df = df[['type', 'article', 'amount', 'year']]
    config.output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.output_csv, index=False)
    logger.info(f"✓ Saved {len(consolidated_rows)} rows to {config.output_csv}")
    
    # Step 4: Optional validation
    try:
        validator = TableValidator(llm_client)
        summary = validator.validate(consolidated_rows, rows_per_table)
        
        report_path = config.validation_report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        logger.info(f"✓ Validation report saved to {report_path}")
        
        return {
            "status": "success",
            "total_tables": len(tables),
            "total_rows": len(consolidated_rows),
            "rows_per_table": rows_per_table,
            "validation": summary.model_dump()
        }
    except Exception as e:
        logger.warning(f"Validation failed (non-critical): {e}")
        return {
            "status": "success",
            "total_tables": len(tables),
            "total_rows": len(consolidated_rows),
            "rows_per_table": rows_per_table,
            "validation": "skipped"
        }


__all__ = ["run_pipeline"]
