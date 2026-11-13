"""PRD 4.1, 4.4, §9.1; AC-01, AC-20, AC-30, AC-37; ADR-000 §6.1; ADR-005."""

import json
import shutil
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from map_qa.cli import app
from map_qa.config import RunConfig
from map_qa.pipeline import read_counts, run

STARTED = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def snap(fixtures_dir, tmp_path):
    dest = tmp_path / "in"
    shutil.copytree(fixtures_dir / "map_qa", dest)
    return dest


def test_pipeline_writes_four_consistent_outputs(snap, tmp_path):
    cfg = RunConfig(input_dir=snap, output_dir=tmp_path / "out")
    lines = []
    result = run(cfg, started=STARTED, echo=lines.append)
    run_dir = tmp_path / "out" / "20261112T100000Z"
    assert result.run_dir == run_dir
    for name in (
        "report.md",
        "report.html",
        "tasks.geojson",
        "tasks.csv",
        "summary.json",
        "not_comparable.csv",
    ):
        assert (run_dir / name).is_file(), name
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    for source, counts in read_counts(run_dir).items():
        assert counts == summary["counts"], source
    assert summary["counts"]["C3"] == summary["c3"]["photos_with_flag"]  # TAC-002-04
    assert summary["c4"]["status"] == "not_run"
    text = "\n".join(lines)
    assert "2026-11-01T21:21:36Z" in text and "2026-10-21.0" in text  # daty snapshotu
    assert "C1" in text and "C4: nie uruchomiono" in text
    assert str(run_dir) in text


def test_with_signs_declined_is_not_run(snap, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-a-real-key-123")
    cfg = RunConfig(input_dir=snap, output_dir=tmp_path / "out", with_signs=True)
    result = run(cfg, started=STARTED, echo=lambda s: None, confirm=lambda plan: False)
    assert result.summary["c4"]["status"] == "not_run"
    assert result.summary["counts"]["C4"] == 0


def test_invalid_input_writes_nothing(snap, tmp_path):
    (snap / "photos.csv").write_text("zmienione", encoding="utf-8")
    res = CliRunner().invoke(app, ["run", "--input", str(snap), "--output", str(tmp_path / "o")])
    assert res.exit_code == 2
    assert "photos.csv" in res.output and "SHA-256" in res.output
    assert not (tmp_path / "o").exists()


def test_cli_run_ok(snap, tmp_path):
    res = CliRunner().invoke(app, ["run", "--input", str(snap), "--output", str(tmp_path / "o")])
    assert res.exit_code == 0, res.output
    assert "report.html" in res.output and "Kandydaci" in res.output


def test_cli_rejects_out_of_range_options_in_polish(snap, tmp_path):
    args = ["run", "--input", str(snap), "--output", str(tmp_path / "o")]
    res = CliRunner().invoke(app, [*args, "--max-requests", "30"])
    assert res.exit_code == 2 and "--max-requests musi być w zakresie 1–25" in res.output
    res = CliRunner().invoke(app, [*args, "--threshold", "1.5"])
    assert res.exit_code == 2 and "--threshold musi być w zakresie 0–1" in res.output


def test_default_input_missing_hint(tmp_path, monkeypatch):  # ADR-005 D-501
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(app, ["run"])
    assert res.exit_code == 2
    assert "uruchom z korzenia repozytorium albo podaj --input" in res.output
    assert not (tmp_path / "reports").exists()


def test_every_task_with_osm_id_exports_full_tags(snap, tmp_path):  # AC-04
    import pyarrow.parquet as pq

    t = pq.read_table(snap / "osm_roads.parquet", columns=["osm_id", "tags"])
    tags = dict(zip(t["osm_id"].to_pylist(), t["tags"].to_pylist(), strict=True))
    result = run(
        RunConfig(input_dir=snap, output_dir=tmp_path / "o"), started=STARTED, echo=lambda s: None
    )
    feats = json.loads((result.run_dir / "tasks.geojson").read_text(encoding="utf-8"))["features"]
    with_osm = [f["properties"] for f in feats if f["properties"]["osm_id"] in tags]
    assert with_osm and any(p["check"] == "C3" for p in with_osm)
    for p in with_osm:
        assert p["osm_raw"] == tags[p["osm_id"]], (p["check"], p["task_id"])
