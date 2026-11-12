"""Wspólne fixture'y testów map-qa."""

from __future__ import annotations

from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
REAL_INPUT = REPO_ROOT / "course-materials" / "exercise-data" / "map-qa"
FIXTURES = APP_DIR / "tests" / "fixtures"


@pytest.fixture
def real_input() -> Path:
    if not REAL_INPUT.exists():
        pytest.skip("brak prawdziwego snapshotu map-qa")
    return REAL_INPUT


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES
