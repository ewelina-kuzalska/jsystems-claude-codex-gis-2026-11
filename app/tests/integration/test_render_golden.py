"""Golden raportów i miniatury na fixture'ach (ADR-004 §8)."""

from shapely.geometry import Point

from map_qa.model import Candidate
from map_qa.render import ReportInput, build_context, prepare_images, render_html, render_markdown
from map_qa.tasks import build_tasks

SNAP = {
    "osm_extract_date": "2026-11-01T21:21:36Z",
    "overture_release": "2026-10-21.0",
    "created_at": "2026-11-02T23:52:58.440512+00:00",
    "rows": {"osm_roads": 131, "overture_segments": 11, "photos": 10, "photo_road_links": 10},
}
OFFLINE = "panoramax_334a574d-18cb-4c2e-be3f-f99307e080d9"
NO_THUMB = "panoramax_5c501d68-11d1-4948-9cde-1cc00fb19184"


def _tasks():
    return build_tasks(
        [
            Candidate(
                check="C1",
                reason_code="missing_lit",
                osm_id=346304716,
                photo_id=OFFLINE,
                photo_ids=(OFFLINE,),
                photo_url="https://api.panoramax.xyz/x",
                photo_author="czecko",
                photo_license="CC-BY-SA-4.0",
                description_pl="Droga OSM 346304716 nie ma informacji o oświetleniu.",
                geometry=Point(20.12, 50.01),
            ),
            Candidate(
                check="C3",
                reason_code="uncertain_link",
                osm_id=1212676722,
                photo_id=NO_THUMB,
                photo_ids=(NO_THUMB,),
                photo_url="https://api.panoramax.xyz/y",
                photo_author="autor",
                photo_license="CC-BY-SA-4.0",
                file_flags=("missing_heading",),
                uncertain_link=True,
                distance_m=4.2,
                geometry=Point(20.0, 50.0),
            ),
        ]
    )


def test_prepare_images_copies_relative(fixtures_dir, tmp_path):
    images = prepare_images(_tasks(), fixtures_dir / "map_qa", tmp_path, {})
    assert images[OFFLINE].rel_path == f"images/{OFFLINE}.jpg"
    assert (tmp_path / "images" / f"{OFFLINE}.jpg").is_file()
    assert images[NO_THUMB].rel_path is None


def test_golden_reports(fixtures_dir, tmp_path, snapshot):
    tasks = _tasks()
    images = prepare_images(tasks, fixtures_dir / "map_qa", tmp_path, {})
    ctx = build_context(
        ReportInput(
            snapshot=SNAP,
            run_started_at="2026-11-12T10:00:00Z",
            threshold=0.7,
            tasks=tasks,
            images=images,
            rows_checked={"C1": 131, "C2": 4, "C3": 10, "C4": 0, "C4-manual": 0},
            c3={
                "file_flags": {"missing_heading": 1},
                "own_flags": {"link_recheck_mismatch": 0},
                "photos_with_flag": 1,
                "photos_total": 10,
            },
            surface_mapping=[("osm", "asphalt", "paved")],
        )
    )
    render_html(ctx, tmp_path / "report.html")
    render_markdown(ctx, tmp_path / "report.md")
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert f'src="images/{OFFLINE}.jpg"' in html
    assert md == snapshot(name="report.md")
    assert html == snapshot(name="report.html")
