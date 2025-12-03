from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from .pipeline import run_pipeline

app = typer.Typer(add_completion=False)


@app.command()
def process(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="PDF file to process"),
    output_csv: Path = typer.Option(None, help="Optional output CSV path"),
    use_ocr: bool = typer.Option(False, help="Enable OCR fallback for complex tables"),
):
    """Run the LLM-driven extraction pipeline."""
    summary = run_pipeline(pdf, output_csv=output_csv, use_ocr=use_ocr)
    print("[bold green]Pipeline finished[/bold green]")
    print(summary)


if __name__ == "__main__":
    app()
