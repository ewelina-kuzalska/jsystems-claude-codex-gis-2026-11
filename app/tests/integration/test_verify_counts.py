"""AC-30, TAC-05; ADR-004 §3.1, §3.7."""

import json

import pytest
from shapely.geometry import Point

from map_qa.export import export_csv, export_geojson
from map_qa.model import Candidate
from map_qa.pipeline import (
    CountMismatch,
    RunDirError,
    finalize_run_dir,
    prepare_run_dir,
    verify_counts,
    write_summary,
)
from map_qa.render import ReportInput, build_context, render_html, render_markdown
from map_qa.tasks import build_tasks, count_by_check


def _write_all(run_dir):
    tasks = build_tasks(
        [
            Candidate(check="C1", reason_code="missing_lit", osm_id=1, geometry=Point(19.9, 50)),
            Candidate(check="C1", reason_code="missing_lanes", osm_id=1, geometry=Point(19.9, 50)),
            Candidate(
                check="C3", reason_code="uncertain_link", photo_id="p", geometry=Point(19.9, 50)
            ),
        ]
    )
    counts = count_by_check(tasks)
    write_summary(run_dir, {"counts": counts})
    export_geojson(tasks, {}, run_dir / "tasks.geojson")
    export_csv(tasks, run_dir / "tasks.csv")
    ctx = build_context(
        ReportInput(
            snapshot={
                "osm_extract_date": "d",
                "overture_release": "r",
                "created_at": "c",
                "rows": {
                    "osm_roads": 1,
                    "overture_segments": 1,
                    "photos": 1,
                    "photo_road_links": 1,
                },
            },
            run_started_at="t",
            threshold=0.7,
            tasks=tasks,
            images={},
            rows_checked={},
        )
    )
    render_html(ctx, run_dir / "report.html")
    render_markdown(ctx, run_dir / "report.md")
    return counts


def test_run_dir_partial_then_rename(tmp_path):
    partial = prepare_run_dir(tmp_path / "runs", "20261112T100000Z")
    assert partial.name == "20261112T100000Z.partial" and partial.is_dir()
    counts = _write_all(partial)
    verify_counts(partial, counts)
    final = finalize_run_dir(partial)
    assert final.name == "20261112T100000Z" and final.is_dir() and not partial.exists()
    assert json.loads((final / "summary.json").read_text(encoding="utf-8"))["counts"]["C1"] == 2


def test_collision_is_error_code_3(tmp_path):
    (tmp_path / "runs" / "20261112T100000Z").mkdir(parents=True)
    with pytest.raises(RunDirError) as exc:
        prepare_run_dir(tmp_path / "runs", "20261112T100000Z")
    assert exc.value.exit_code == 3


def test_removed_csv_row_gives_count_mismatch(tmp_path):
    partial = prepare_run_dir(tmp_path / "runs", "r1")
    counts = _write_all(partial)
    csv_path = partial / "tasks.csv"
    lines = csv_path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    csv_path.write_text("".join(lines[:-1]), encoding="utf-8-sig")
    with pytest.raises(CountMismatch) as exc:
        verify_counts(partial, counts)
    assert exc.value.exit_code == 4
    assert exc.value.check == "C3" and "tasks.csv" in exc.value.sources
    assert partial.exists()  # katalog zostaje jako .partial


@pytest.mark.parametrize("target", ["report.html", "report.md", "tasks.geojson"])
def test_mismatch_in_each_output(tmp_path, target):
    partial = prepare_run_dir(tmp_path / "runs", "r2")
    counts = _write_all(partial)
    path = partial / target
    text = path.read_text(encoding="utf-8")
    if target == "report.html":
        text = text.replace('data-check="C1" data-count="2"', 'data-check="C1" data-count="3"')
    elif target == "report.md":
        text = text.replace("| C1 | 2 |", "| C1 | 5 |")
    else:
        doc = json.loads(text)
        doc["features"] = doc["features"][1:]
        text = json.dumps(doc)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(CountMismatch):
        verify_counts(partial, counts)
