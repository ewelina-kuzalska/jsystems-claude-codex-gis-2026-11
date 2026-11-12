"""AC-29, AC-31, AC-32, AC-36, AC-38; ADR-004 §3.3–3.5, §3.8, D-07, TAC-004-01."""

import re
from importlib.resources import files

import pytest
from jinja2 import UndefinedError
from shapely.geometry import Point

from map_qa.model import Candidate
from map_qa.render import (
    MANDATORY_TEXTS,
    ImageRef,
    ReportInput,
    build_context,
    md_escape,
    render_html,
    render_markdown,
)
from map_qa.tasks import build_tasks

SNAP = {
    "osm_extract_date": "2026-11-01T21:21:36Z",
    "overture_release": "2026-10-21.0",
    "created_at": "2026-11-02T23:52:58Z",
    "rows": {
        "osm_roads": 99768,
        "overture_segments": 85405,
        "photos": 561,
        "photo_road_links": 561,
    },
}


def report_input(**kw):
    cands = kw.pop("cands", None) or [
        Candidate(
            check="C1",
            reason_code="missing_lit",
            osm_id=5,
            photo_id="p1",
            photo_ids=("p1",),
            photo_url="https://example.org/p1",
            photo_author="<script>alert(1)</script> & Ćma",
            photo_license="CC-BY-SA-4.0",
            description_pl="Droga | z *gwiazdką*\nnowa linia",
            geometry=Point(19.9, 50.0),
        ),
        Candidate(
            check="C3",
            reason_code="uncertain_link",
            osm_id=6,
            photo_id="p2",
            photo_ids=("p2",),
            photo_url="javascript:alert(1)",
            photo_author="Autor",
            photo_license="CC-BY-SA-4.0",
            file_flags=("service_way",),
            uncertain_link=True,
            geometry=Point(19.9, 50.0),
        ),
    ]
    base = dict(
        snapshot=SNAP,
        run_started_at="2026-11-12T10:00:00Z",
        threshold=0.7,
        tasks=build_tasks(cands),
        images={"p1": ImageRef("images/p1.jpg"), "p2": ImageRef(None)},
        rows_checked={"C1": 99768, "C2": 10, "C3": 561, "C4": 0, "C4-manual": 0},
    )
    base.update(kw)
    return ReportInput(**base)


@pytest.fixture
def out(tmp_path):
    ctx = build_context(report_input())
    render_html(ctx, tmp_path / "report.html")
    render_markdown(ctx, tmp_path / "report.md")
    return (
        (tmp_path / "report.html").read_text(encoding="utf-8"),
        (tmp_path / "report.md").read_text(encoding="utf-8"),
    )


def test_html_escapes_source_data(out):
    html, _ = out
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; Ćma" in html
    assert 'href="javascript:' not in html  # inny schemat niż https → tekst
    assert "javascript:alert(1)" in html


def test_html_offline_page(out):  # TAC-004-01, AC-31
    html, _ = out
    assert 'lang="pl"' in html and '<meta charset="utf-8">' in html
    assert "data:image" not in html
    assert not re.search(r'src="http://', html)
    assert "<script" not in html and "<link" not in html
    assert 'src="images/p1.jpg"' in html
    assert "Obraz niedostępny lokalnie" in html  # p2 bez miniatury


def test_counts_marked(out):
    html, md = out
    assert 'data-check="C1" data-count="1"' in html
    assert 'data-check="C2" data-count="0"' in html
    assert "| C1 | 1 |" in md
    assert "0 kandydatów (sprawdzono 10 wierszy)" in html


def test_mandatory_texts(out):  # AC-29, AC-36, ADR-004 §3.8
    html, md = out
    for text in MANDATORY_TEXTS:
        assert text in html
        assert md_escape(text) in md


def test_attribution_and_header(out):  # AC-03, AC-32
    html, md = out
    for doc in (html, md):
        assert "© OpenStreetMap contributors" in doc
        assert "Overture Maps Foundation" in doc
        assert "CC BY-SA 4.0" in doc
        assert "2026-10-21.0" in doc and "2026-11-01" in doc
    assert "99 768" in html and "85 405" in html and "561" in html


def test_never_states_map_is_wrong(out):  # AC-36
    html, md = out
    assert "mapa jest błędna" not in html.lower()
    assert "błąd mapy" not in html.replace("nie dowodzi błędu mapy", "").lower()


def test_markdown_escape():
    assert md_escape("a|b*c_d[e]<f>#g`h\\i") == r"a\|b\*c\_d\[e\]\<f\>\#g\`h\\i"
    assert md_escape("x\ny\r\nz") == "x y z"
    assert md_escape(None) == ""


def test_markdown_table_not_broken(out):
    _, md = out
    assert "Droga \\| z \\*gwiazdką\\* nowa linia" in md


def test_no_safe_filter_in_templates():
    for tpl in (files("map_qa") / "templates").iterdir():
        text = tpl.read_text(encoding="utf-8")
        assert not re.search(r"\|\s*safe\b", text), tpl.name


def test_strict_undefined(tmp_path):
    ctx = build_context(report_input())
    del ctx["meta"]
    with pytest.raises(UndefinedError):
        render_html(ctx, tmp_path / "x.html")


def test_empty_manual_queue_text(out):
    html, _ = out
    assert "Żaden znak nie wymaga ręcznej kontroli" in html


def test_c4_block_and_manual_queue(tmp_path):
    cands = [
        Candidate(
            check="C4",
            reason_code="sign_mismatch",
            osm_id=7,
            photo_id="s1",
            photo_ids=("s1",),
            photo_url="https://www.mapillary.com/app/?pKey=1",
            photo_author="autor",
            photo_license="CC-BY-SA-4.0",
            resolved_by="general_llm",
            tier1_model="typesafe/jev-1.14",
            tier1_answer="unreadable",
            tier1_probability=0.8,
            tier2_answer="50",
            tier2_confidence=0.9,
            mapillary_value="regulatory--maximum-speed-limit-50--g1",
            extra={"osm_speed_tags": "maxspeed=70"},
            geometry=Point(19.9, 50.0),
        ),
        Candidate(
            check="C4-manual",
            reason_code="below_threshold",
            photo_id="s2",
            photo_ids=("s2",),
            photo_url="https://www.mapillary.com/app/?pKey=2",
            photo_author="autor2",
            photo_license="CC-BY-SA-4.0",
            resolved_by="human_pending",
            tier1_answer="50",
            tier1_probability=0.3,
            tier2_answer="40",
            tier2_confidence=0.4,
            geometry=Point(19.9, 50.0),
        ),
    ]
    block = {
        "status": "run",
        "tier1_model": "typesafe/jev-1.14",
        "tier2_model": "openai/gpt-6-luna",
        "threshold": 0.7,
        "limit": 25,
        "requests": {"tier1": 2, "tier2": 2},
        "cached": {"tier1": 0, "tier2": 0},
        "cost_text": "0,0002",
        "processed": 2,
        "sample_total": 119,
        "resolved": {"decision_model": 0, "general_llm": 1, "human_pending": 1, "not_run": 117},
        "stop_text": "nie zatrzymano",
        "accuracy": [
            {"label": "Krok 1 — ostateczne (typesafe/jev-1.14)", "correct": 0, "evaluated": 0}
        ],
        "evaluation_note": "Mianownik: etykiety certain.",
        "manual_by_reason": {"below_threshold": 1},
    }
    ri = report_input(
        cands=cands,
        c4=block,
        images={"s1#crop": ImageRef("images/s1_crop.jpg"), "s2#crop": ImageRef(None)},
    )
    ctx = build_context(ri)
    render_html(ctx, tmp_path / "r.html")
    render_markdown(ctx, tmp_path / "r.md")
    html = (tmp_path / "r.html").read_text(encoding="utf-8")
    md = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "Zgodność z roboczą referencją" in html and "typesafe/jev-1.14" in html
    assert 'src="images/s1_crop.jpg"' in html
    assert "Żaden znak nie wymaga ręcznej kontroli" not in html
    assert "below_threshold" in html and "40 (0,40)" in html  # podpowiedzi z obu kroków
    assert 'data-check="C4-manual" data-count="1"' in html
    assert "| C4-manual | 1 |" in md and "unreadable (0,80)" in md
