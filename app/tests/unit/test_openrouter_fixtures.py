"""TAC-003-03: zapisy OpenRouter mają metadane i nie zawierają sekretów."""

import json

import pytest

from tests.conftest import FIXTURES

FILES = sorted((FIXTURES / "openrouter").glob("*.json"))


def test_captures_exist():
    names = {f.stem for f in FILES}
    assert {"tier1-jev-readable", "tier1-luna-readable", "tier2-luna-readable"} <= names
    assert "error-401-decisions" in names


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_capture_has_metadata_and_no_secret(path):
    text = path.read_text(encoding="utf-8")
    assert "Authorization" not in text
    assert "Bearer" not in text
    assert "base64," not in text
    data = json.loads(text)
    for key in ("captured_at", "endpoint", "model", "status", "body", "request_summary"):
        assert key in data
