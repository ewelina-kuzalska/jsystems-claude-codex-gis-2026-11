"""C1 i C2 na prawdziwych danych (ADR-001 §8: C1 udziały, TAC-001-04, TAC-001-05)."""

import json

import pytest

from map_qa.checks.c1 import check_missing
from map_qa.checks.c2 import check_discrepancy
from map_qa.inputs import load_links, load_osm, load_overture_raw, load_photos, verify_snapshot
from map_qa.normalize.overture import sources_for_segment


def _load(input_dir):
    snap = verify_snapshot(input_dir)
    return snap, load_osm(snap), load_overture_raw(snap), load_links(snap), load_photos(snap)


def _assert_c2_invariants(osm, ov, res):
    s = res.stats
    assert s["candidates"] + s["not_comparable"] + s["equal"] == s["comparisons"]  # TAC-001-05
    referenced = {
        (src.segment_id, src.osm_way_id)
        for seg in ov.itertuples(index=False)
        for src in sources_for_segment(seg.id, seg.sources)
    }
    for c in res.candidates:  # TAC-001-04
        assert (c.segment_id, c.osm_id) in referenced
        assert c.osm_raw and json.loads(c.osm_raw)  # pełne tagi OSM (AC-04)


def test_fixture_c1_and_c2(fixtures_dir):
    snap, osm, ov, links, photos = _load(fixtures_dir / "map_qa")
    summary, cands = check_missing(osm, ov, links, photos)
    assert sum(r["total"] for r in summary["osm"]) == len(osm)
    linked = {int(w) for w in links["osm_way_id"] if w}
    assert {c.osm_id for c in cands} <= linked
    assert all(c.photo_author and c.photo_url.startswith("https://") for c in cands)
    res = check_discrepancy(osm, ov, links, snap.osm_extract_date, snap.overture_release, photos)
    _assert_c2_invariants(osm, ov, res)
    nc = {(n.segment_id, n.reason_code) for n in res.not_comparable}
    # 009debd5 zbudowany z dwóch way (sources.between) → partial_source
    assert ("009debd5-c2b6-4f7c-9742-b798fd175449", "partial_source") in nc


@pytest.mark.slow
def test_full_snapshot_c1_c2(real_input):
    snap, osm, ov, links, photos = _load(real_input)
    summary, cands = check_missing(osm, ov, links, photos)
    assert sum(r["total"] for r in summary["osm"]) == 99768
    assert sum(r["total"] for r in summary["overture"]) == 85405
    assert 0 < len(cands) < 4 * 558
    res = check_discrepancy(osm, ov, links, snap.osm_extract_date, snap.overture_release, photos)
    _assert_c2_invariants(osm, ov, res)
    assert res.stats["pairs"] == 105809  # profil M2
    assert [x["photo_id"] for x in res.spatial_only] == ["mapillary_1127617272466620"]
