"""E2E bez mocków: prawdziwe CLI na pełnym snapshocie (TAC-04, AC-02, AC-03, AC-30, AC-35).

`cwd` = korzeń repo (ADR-005 D-503), wyniki w `tmp_path`. Ścieżkę wejść można nadpisać
zmienną `MAP_QA_REAL_INPUT` (np. wierna kopia snapshotu z gita, gdy checkout ma CRLF).
"""

import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from map_qa.inputs import load_overture_raw, verify_snapshot
from map_qa.normalize.overture import rules_for_segment, sources_for_segment
from tests.conftest import REAL_INPUT, REPO_ROOT

pytestmark = pytest.mark.slow


def _hashes(root: Path) -> dict[str, str]:
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "data" not in path.relative_to(root).parts[:1]:
            out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _run(output: Path) -> tuple[subprocess.CompletedProcess, float]:
    env = {**os.environ, "PYTHONUTF8": "1"}
    env.pop("OPENROUTER_API_KEY", None)
    started = time.monotonic()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "map_qa.cli",
            "run",
            "--input",
            str(REAL_INPUT),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=300,
    )
    return proc, time.monotonic() - started


@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    if not REAL_INPUT.exists():
        pytest.skip("brak snapshotu map-qa")
    before = _hashes(REAL_INPUT)
    out = tmp_path_factory.mktemp("runs")
    first, elapsed = _run(out / "a")
    time.sleep(1.1)  # inny run_id
    second, _ = _run(out / "b")
    after = _hashes(REAL_INPUT)
    return {
        "first": first,
        "second": second,
        "elapsed": elapsed,
        "before": before,
        "after": after,
        "out": out,
    }


def _run_dir(base: Path) -> Path:
    (run_dir,) = [p for p in base.iterdir() if p.is_dir()]
    return run_dir


def test_exit_code_and_time(two_runs):  # TAC-04
    assert two_runs["first"].returncode == 0, two_runs["first"].stderr
    assert two_runs["second"].returncode == 0, two_runs["second"].stderr
    assert "Wyniki:" in two_runs["first"].stdout  # CLI naprawdę coś uruchomiło
    assert two_runs["elapsed"] < 120


def test_inputs_unchanged(two_runs):  # AC-02
    assert two_runs["before"] == two_runs["after"]


def test_header_counts(two_runs):  # AC-03
    html = (_run_dir(two_runs["out"] / "a") / "report.html").read_text(encoding="utf-8")
    for text in ("99 768", "85 405", "561", "2026-10-21.0", "2026-11-01T21:21:36Z"):
        assert text in html
    assert "Wiersze: drogi OSM 99768" in two_runs["first"].stdout


def test_counts_consistent(two_runs):  # AC-30, TAC-004-03
    run_dir = _run_dir(two_runs["out"] / "a")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    feats = json.loads((run_dir / "tasks.geojson").read_text(encoding="utf-8"))["features"]
    rows = list(csv.DictReader(io.StringIO((run_dir / "tasks.csv").read_text("utf-8-sig"))))
    assert len(rows) == len(feats) == sum(summary["counts"].values())
    assert summary["counts"]["C3"] == summary["c3"]["photos_with_flag"]  # TAC-002-04
    assert summary["c4"]["status"] == "not_run"


def test_repeatable_exports(two_runs):  # AC-35, TAC-004-04
    a, b = _run_dir(two_runs["out"] / "a"), _run_dir(two_runs["out"] / "b")
    for name in ("tasks.geojson", "tasks.csv"):
        assert (
            hashlib.sha256((a / name).read_bytes()).hexdigest()
            == hashlib.sha256((b / name).read_bytes()).hexdigest()
        )


def test_overture_rule_counts_and_c2_references(two_runs):  # TAC-001-02, TAC-001-04
    snap = verify_snapshot(REAL_INPUT)
    seg = load_overture_raw(snap)
    refs = set()
    for row in seg.itertuples(index=False):
        rules = rules_for_segment(row.id, row.speed_limits, row.road_surface)
        assert sum(r.rule_kind == "speed" for r in rules) == len(row.speed_limits)
        refs |= {(s.segment_id, s.osm_way_id) for s in sources_for_segment(row.id, row.sources)}
    feats = json.loads(
        (_run_dir(two_runs["out"] / "a") / "tasks.geojson").read_text(encoding="utf-8")
    )["features"]
    c2 = [f["properties"] for f in feats if f["properties"]["check"] == "C2"]
    assert c2, "oczekiwano kandydatów C2"
    for p in c2:
        assert (p["segment_id"], p["osm_id"]) in refs


def test_geojson_in_krakow(two_runs):
    feats = json.loads(
        (_run_dir(two_runs["out"] / "a") / "tasks.geojson").read_text(encoding="utf-8")
    )["features"]
    for f in feats:
        coords = f["geometry"]["coordinates"]
        pts = [coords] if f["geometry"]["type"] == "Point" else coords
        for lon, lat in pts:
            assert 19.5 < lon < 20.5 and 49.8 < lat < 50.3  # drogi przecinające bbox
