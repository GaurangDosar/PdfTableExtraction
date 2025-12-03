from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SchemaColumns = Literal["type", "article", "amount", "year"]


class NormalizedRow(BaseModel):
    type: str = Field(description="Type of the entry")
    article: str = Field(description="Article or description")
    amount: str = Field(description="Amount or value")
    year: str = Field(description="Year (4 digits)")
    source_table: str = Field(description="Source table identifier")


class ValidationSummary(BaseModel):
    total_tables: int
    rows_per_table: dict[str, int]
    total_rows: int
    column_alignment_ok: bool
    per_table_alignment: dict[str, bool] = Field(default_factory=dict, description="Column alignment status per table")
    low_confidence_rows: List[dict] = Field(default_factory=list, description="Rows with quality issues or inference uncertainty")
    discrepancies: List[str]
    llm_notes: Optional[str] = None
    prompt_log_paths: List[Path] = Field(default_factory=list)


__all__ = [
    "NormalizedRow",
    "ValidationSummary",
    "SchemaColumns",
]
