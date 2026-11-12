"""Kontrola linków na prawdziwych danych (ADR-002 §8, TAC-002-03)."""

import pytest

from map_qa.crs import to_2180
from map_qa.inputs import load_links, load_osm, load_photos, verify_snapshot
from map_qa.linking import OsmIndex, recheck_links


def _recheck(input_dir):
    snap = verify_snapshot(input_dir)
    osm = load_osm(snap)
    idx = OsmIndex.build(osm, to_2180(osm, "osm_roads.parquet").geometry)
    return recheck_links(load_links(snap), load_photos(snap), idx)


def test_fixture_links(fixtures_dir):
    out = _recheck(fixtures_dir / "map_qa").set_index("photo_id")
    zero = out.loc["panoramax_646ecfdd-ab57-4a28-b411-fb112ced3c97"]
    assert zero.directed_diff is not None  # heading 0.0 to północ
    missing = out.loc["panoramax_5c501d68-11d1-4948-9cde-1cc00fb19184"]
    assert missing.undirected_diff is None and "missing_heading" in missing.file_flags
    assert out.loc["panoramax_df4d3a9c-5fb6-427f-8c54-293ed6ea354b"].recheck_status == (
        "not_checked"
    )
    service = out.loc["panoramax_30f08d1e-fe31-42d9-b042-607f5237d9ff"]
    assert "service_way" in service.file_flags and service.uncertain
    checked = out[out.recheck_status != "not_checked"]
    assert (checked.recheck_status == "ok").all()


@pytest.mark.slow
def test_full_snapshot_recheck_ok_share(real_input):  # TAC-002-03
    out = _recheck(real_input)
    checked = out[out.osm_way_id != ""]
    share = (checked.recheck_status == "ok").mean()
    assert share >= 0.95, f"ok {share:.1%}"
    missing = out.file_flags.apply(lambda f: "missing_heading" in f)
    assert int(missing.sum()) == 15
    assert out.loc[missing, "undirected_diff"].isna().all()
