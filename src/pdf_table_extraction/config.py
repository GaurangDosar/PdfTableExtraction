from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = BASE_DIR / "artifacts"
PROMPT_LOG_DIR = ARTIFACTS_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"

for directory in (ARTIFACTS_DIR, PROMPT_LOG_DIR, OUTPUT_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)


class LLMConfig(BaseModel):
    provider: str = Field(default="groq")
    groq_api_key: Optional[str] = Field(default=os.getenv("GROQ_API_KEY"))
    groq_api_key_2: Optional[str] = Field(default=os.getenv("GROQ_API_KEY_2"))
    groq_api_key_3: Optional[str] = Field(default=os.getenv("GROQ_API_KEY_3"))
    primary_model: str = Field(default=os.getenv("PRIMARY_MODEL", "llama-3.3-70b-versatile"))
    validation_model: str = Field(default=os.getenv("VALIDATION_MODEL", "llama-3.3-70b-versatile"))
    temperature: float = Field(default=float(os.getenv("LLM_TEMPERATURE", "0.1")))
    max_output_tokens: int = Field(default=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "4096")))
    
    def get_groq_api_keys(self) -> list[str]:
        """Return all configured Groq API keys"""
        keys = []
        if self.groq_api_key:
            keys.append(self.groq_api_key)
        if self.groq_api_key_2:
            keys.append(self.groq_api_key_2)
        if self.groq_api_key_3:
            keys.append(self.groq_api_key_3)
        return keys


class ExtractionConfig(BaseModel):
    pdf_path: Path
    chunk_size: int = 2048
    overlap: int = 256
    include_images: bool = True
    use_ocr: bool = False
    language: str = "eng"


class PipelineConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    extraction: ExtractionConfig
    output_csv: Path = Field(default=OUTPUT_DIR / "consolidated.csv")
    prompt_log_dir: Path = Field(default=PROMPT_LOG_DIR)
    validation_report: Path = Field(default=OUTPUT_DIR / "validation_report.json")


__all__ = [
    "LLMConfig",
    "ExtractionConfig",
    "PipelineConfig",
    "BASE_DIR",
    "OUTPUT_DIR",
    "PROMPT_LOG_DIR",
]
