"""Wspólne fixture'y testów map-qa."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
REAL_INPUT = Path(
    os.environ.get("MAP_QA_REAL_INPUT")
    or REPO_ROOT / "course-materials" / "exercise-data" / "map-qa"
)
FIXTURES = APP_DIR / "tests" / "fixtures"


def pytest_addoption(parser):
    """`-p no:recording` (testy live_api, ADR-006 D-604) wyłącza wtyczkę, która definiuje
    `--block-network` z `addopts`; wtedy rejestrujemy opcję jako nieaktywną, żeby polecenie
    `uv run pytest -m live_api -p no:recording` działało i miało dostęp do sieci."""
    try:
        parser.addoption("--block-network", action="store_true", default=False)
    except ValueError:
        pass  # wtyczka pytest-recording aktywna: blokada sieci działa (TAC-03)


@pytest.fixture
def real_input() -> Path:
    if not REAL_INPUT.exists():
        pytest.skip("brak prawdziwego snapshotu map-qa")
    return REAL_INPUT


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="module")
def fixtures_dir_module() -> Path:
    return FIXTURES
