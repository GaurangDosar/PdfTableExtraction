from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from .config import LOG_DIR, PROMPT_LOG_DIR

# Configure logger
LOG_FILE = LOG_DIR / "pipeline.log"
logger.remove()
logger.add(LOG_FILE, rotation="1 MB", retention=5, level="INFO")
logger.add(lambda msg: print(msg, end=""), level="INFO")


class PromptLogger:
    """Log LLM prompts and responses for debugging and analysis."""
    
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or PROMPT_LOG_DIR
        self.directory.mkdir(parents=True, exist_ok=True)

    def log(self, *, prompt: str, response: str, metadata: Dict[str, Any] | None = None) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        log_path = self.directory / f"prompt-{timestamp}.json"
        payload = {
            "timestamp": timestamp,
            "prompt": prompt,
            "response": response,
            "metadata": metadata or {},
        }
        log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return log_path


__all__ = ["logger", "LOG_FILE", "PromptLogger"]
