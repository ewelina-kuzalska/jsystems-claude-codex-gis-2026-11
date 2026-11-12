"""E2E C4 na prawdziwych endpointach (ADR-006 D-604, AC-22e, AC-23, AC-26).

Uruchomienie: uv run pytest -m live_api -p no:recording tests/e2e/test_cli_c4_live.py
Pierwsza runda na świeżym cache w `tmp_path` wysyła prawdziwe żądania (w limicie 25),
druga runda na tym samym cache i tych samych wycinkach (`--sign-sample 0`) wysyła zero żądań.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.conftest import REAL_INPUT, REPO_ROOT

pytestmark = pytest.mark.live_api


def _run(out: Path, cache: Path, *extra: str) -> tuple[subprocess.CompletedProcess, dict]:
    env = {**os.environ, "PYTHONUTF8": "1", "MAP_QA_CACHE_DIR": str(cache)}
    proc = subprocess.run(
        [sys.executable, "-m", "map_qa.cli", "run", "--input", str(REAL_INPUT), "--output",
         str(out), "--with-signs", "--yes", *extra],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", env=env, timeout=900,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    run_dir = sorted(p for p in out.iterdir() if p.is_dir())[-1]
    return proc, json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("model", ["jev", "luna-decisions"])
def test_live_c4_then_cached_rerun(model, tmp_path):
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        pytest.skip("brak OPENROUTER_API_KEY")
    if not REAL_INPUT.exists():
        pytest.skip("brak snapshotu map-qa")
    cache = tmp_path / "cache"
    first, s1 = _run(tmp_path / "a", cache, "--tier1-model", model)
    c4 = s1["c4"]
    assert c4["status"] == "run", c4
    assert 0 < c4["requests"]["total"] <= 25
    assert c4["processed"] == 12 and sum(c4["resolved"].values()) == 119
    assert c4["stop_reason"] == "none", c4["stop_text"]
    assert os.environ["OPENROUTER_API_KEY"][-12:] not in first.stdout

    time.sleep(1.1)
    _, s2 = _run(tmp_path / "b", cache, "--tier1-model", model, "--sign-sample", "0")
    assert s2["c4"]["requests"]["total"] == 0  # AC-26
    assert s2["c4"]["cached"]["tier1"] == 12
    assert s2["c4"]["resolved"] == c4["resolved"]
    assert s2["counts"] == s1["counts"]
