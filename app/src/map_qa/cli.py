"""Punkt wejścia CLI `map-qa` (ADR-000 §6.1, ADR-005)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    help="Map QA: raport kandydatów do sprawdzenia atrybutów dróg Krakowa.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Map QA: raport kandydatów do sprawdzenia atrybutów dróg Krakowa."""


@app.command("run")
def run(
    input_dir: Annotated[
        Path, typer.Option("--input", help="Katalog snapshotu wejściowego.")
    ] = Path("course-materials/exercise-data/map-qa"),
    output_dir: Annotated[
        Path, typer.Option("--output", help="Katalog na wyniki uruchomień.")
    ] = Path("reports/map-qa/runs"),
    with_signs: Annotated[
        bool, typer.Option("--with-signs", help="Włącz odczyt znaków B-33 przez AI (C4).")
    ] = False,
    max_requests: Annotated[
        int, typer.Option("--max-requests", min=1, max=25, help="Limit żądań AI (1–25).")
    ] = 25,
    threshold: Annotated[
        float, typer.Option("--threshold", min=0.0, max=1.0, help="Próg pewności (0–1).")
    ] = 0.7,
    yes: Annotated[bool, typer.Option("--yes", help="Potwierdź C4 bez pytania.")] = False,
) -> None:
    """Uruchom kontrole C1–C4 i zapisz raporty oraz eksporty."""
    typer.echo("Pipeline nie jest jeszcze podłączony.")


def _ensure_utf8_streams() -> None:
    """Polskie znaki na Windows przy przekierowaniu wyjścia (cp1250, AC-38)."""
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if enc != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    _ensure_utf8_streams()
    app()
