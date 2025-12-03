from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .llm_client import LLMClient
from .utils import logger
from .models import NormalizedRow, ValidationSummary

NORMALIZATION_PROMPT_PATH = Path(__file__).with_name("prompts") / "normalization_prompt_compact.txt"
VALIDATION_PROMPT_PATH = Path(__file__).with_name("prompts") / "validation_prompt_compact.txt"


class TableNormalizer:
    """Normalize extracted tables to canonical schema using LLM."""
    
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.prompt = NORMALIZATION_PROMPT_PATH.read_text(encoding="utf-8")

    def normalize(self, table: Dict, document_context: str = None) -> Tuple[List[NormalizedRow], List[str]]:
        """
        Normalize a table dict (from PDFExtractor) to canonical schema.
        
        Args:
            table: Dict with keys: table_id, page_number, headers, rows
            document_context: Optional context from PDF (title, metadata, first page) for year inference
            
        Returns:
            Tuple of (normalized_rows, notes_list)
        """
        table_id = table.get("table_id", "unknown-table")
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        
        if not rows:
            logger.warning(f"Table {table_id} has no rows to normalize")
            return [], ["No rows in table"]
        
        # Build prompt with table data and context
        table_data = {
            "table_id": table_id,
            "headers": headers,
            "rows": rows
        }
        
        # Add document context to system prompt if available
        system_prompt = self.prompt
        if document_context:
            system_prompt += f"\n\n# DOCUMENT CONTEXT\nThe following context was extracted from the PDF document for year inference:\n{document_context}\n\n**Use this context to infer missing years when tables lack explicit year columns or temporal references.**"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(table_data, ensure_ascii=False)},
        ]
        
        response = self.llm.chat(messages, metadata={"stage": "normalization", "table_id": table_id})
        
        # Extract JSON from response (handle markdown code blocks or surrounding text)
        json_str = response.strip()
        
        # Try to find JSON array/object in response
        if "```json" in json_str:
            json_start = json_str.index("```json") + 7
            json_end = json_str.index("```", json_start)
            json_str = json_str[json_start:json_end].strip()
        elif "[" in json_str and "]" in json_str:
            # Extract just the JSON array
            json_start = json_str.index("[")
            json_end = json_str.rindex("]") + 1
            json_str = json_str[json_start:json_end]
        
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.error(f"Normalization LLM returned invalid JSON for {table_id}: {exc}")
            logger.error(f"Response snippet: {response[:500]}")
            raise ValueError(f"Could not parse LLM response for {table_id}")
        
        # Handle both list format and dict format
        rows_data = parsed if isinstance(parsed, list) else parsed.get("rows", [])
        notes = parsed.get("notes", []) if isinstance(parsed, dict) else []
        
        normalized_rows = []
        for row in rows_data:
            try:
                # Convert numeric types to strings if needed
                row_fixed = {
                    "type": str(row.get("type", "")),
                    "article": str(row.get("article", "")),
                    "amount": str(row.get("amount", "")),
                    "year": str(row.get("year", "")),
                }
                normalized_rows.append(
                    NormalizedRow(**row_fixed, source_table=table_id)
                )
            except Exception as e:
                logger.warning(f"Skipping invalid row in {table_id}: {e}")
                notes.append(f"Skipped row due to validation error: {str(e)}")
        
        return normalized_rows, notes


class TableValidator:
    """Validate normalized table data using LLM."""
    
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.prompt = VALIDATION_PROMPT_PATH.read_text(encoding="utf-8")

    def validate(self, rows: List[NormalizedRow], rows_per_table: Dict[str, int]) -> ValidationSummary:
        summary_payload = {
            "total_tables": len(rows_per_table),
            "rows_per_table": rows_per_table,
            "consolidated_rows": [row.model_dump() for row in rows],
        }
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": json.dumps(summary_payload, ensure_ascii=False)},
        ]
        response = self.llm.chat(messages, model=self.llm.config.validation_model, metadata={"stage": "validation"})
        
        # Extract JSON from response (handle markdown code blocks or surrounding text)
        json_str = response.strip()
        
        if "```json" in json_str:
            json_start = json_str.index("```json") + 7
            json_end = json_str.index("```", json_start)
            json_str = json_str[json_start:json_end].strip()
        elif "{" in json_str and "}" in json_str:
            # Extract just the JSON object
            json_start = json_str.index("{")
            json_end = json_str.rindex("}") + 1
            json_str = json_str[json_start:json_end]
        
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Validation response not valid JSON; using default")
            logger.debug(f"Response snippet: {response[:300]}")
            parsed = {
                "column_alignment_ok": True,
                "discrepancies": ["Validation parsing failed - review manually"],
                "llm_notes": "LLM response could not be parsed as JSON",
            }
        summary = ValidationSummary(
            total_tables=summary_payload["total_tables"],
            rows_per_table=rows_per_table,
            total_rows=len(rows),
            column_alignment_ok=parsed.get("column_alignment_ok", False),
            per_table_alignment=parsed.get("per_table_alignment", {}),
            low_confidence_rows=parsed.get("low_confidence_rows", []),
            discrepancies=parsed.get("discrepancies", []),
            llm_notes=parsed.get("llm_notes"),
        )
        return summary


__all__ = ["TableNormalizer", "TableValidator"]
