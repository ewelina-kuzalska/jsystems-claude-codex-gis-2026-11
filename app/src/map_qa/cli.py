"""Punkt wejścia CLI `map-qa` (ADR-000 §6.1, D-08, ADR-005).

Kody wyjścia: 0 sukces, 2 błąd wejść lub opcji, 3 błąd zapisu wyników, 4 niezgodne liczniki.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from map_qa.config import ConfigError, RunConfig
from map_qa.model import InputError

app = typer.Typer(
    help="Map QA: raport kandydatów do sprawdzenia atrybutów dróg Krakowa.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Map QA: raport kandydatów do sprawdzenia atrybutów dróg Krakowa."""


def _fail(message: str, code: int) -> None:
    typer.echo(f"Błąd: {message}", err=True)
    raise typer.Exit(code)


def _ask(plan) -> bool:
    """Potwierdzenie C4: tylko jawne „t”/„tak” uruchamia płatne żądania (AC-20, D-08)."""
    answer = typer.prompt("Uruchomić odczyt znaków? (tak/nie)", default="nie")
    return answer.strip().lower() in ("t", "tak")


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
    tier1_model: Annotated[
        str, typer.Option("--tier1-model", help="Model kroku 1: jev albo luna-decisions.")
    ] = "jev",
    max_requests: Annotated[
        int, typer.Option("--max-requests", help="Limit żądań AI na uruchomienie (1–25).")
    ] = 25,
    threshold: Annotated[
        float, typer.Option("--threshold", help="Próg pewności dla obu kroków (0–1).")
    ] = 0.7,
    max_cost_usd: Annotated[
        float, typer.Option("--max-cost-usd", help="Limit kosztu żądań AI w USD.")
    ] = 0.50,
    sign_sample: Annotated[
        int | None,
        typer.Option("--sign-sample", help="Liczba nowych wycinków (domyślnie floor(limit/2))."),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", help="Potwierdź C4 bez pytania.")] = False,
) -> None:
    """Uruchom kontrole C1–C4 i zapisz raporty oraz eksporty."""
    from map_qa.pipeline import CountMismatch, RunDirError
    from map_qa.pipeline import run as run_pipeline

    try:
        cfg = RunConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            with_signs=with_signs,
            max_requests=max_requests,
            threshold=threshold,
            max_cost_usd=max_cost_usd,
            sign_sample=sign_sample,
            tier1_model=tier1_model,
            yes=yes,
        )
    except ConfigError as exc:
        _fail(str(exc), 2)
    try:
        run_pipeline(cfg, echo=typer.echo, confirm=(lambda plan: True) if yes else _ask)
    except InputError as exc:
        _fail(f"wejście niepoprawne — {exc}. Nie zapisano żadnych wyników.", 2)
    except RunDirError as exc:
        _fail(str(exc), 3)
    except CountMismatch as exc:
        partial = getattr(exc, "partial", "")
        _fail(f"{exc}. Wyniki pozostały w {partial}", 4)


def _ensure_utf8_streams() -> None:
    """Polskie znaki na Windows przy przekierowaniu wyjścia (cp1250, AC-38)."""
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if enc != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    _ensure_utf8_streams()
    app()


if __name__ == "__main__":
    main()
