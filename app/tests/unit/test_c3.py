"""AC-16, AC-19; ADR-002 §3.3, TAC-002-04."""

import pandas as pd

from map_qa.checks.c3 import check_uncertain, label_uncertain
from map_qa.model import Candidate


def rechecked(rows):
    return pd.DataFrame(
        [
            {
                "photo_id": p,
                "osm_way_id": "1",
                "overture_id": "s",
                "distance_m": "3.0",
                "recheck_distance_m": 3.04,
                "file_flags": tuple(ff),
                "own_flags": tuple(of),
                "uncertain": bool(ff or of),
            }
            for p, ff, of in rows
        ]
    )


PHOTOS = pd.DataFrame(
    [
        {
            "photo_id": p,
            "longitude": 19.9,
            "latitude": 50.0,
            "source_url": f"https://x/{p}",
            "author": "a",
            "license": "CC-BY-SA-4.0",
        }
        for p in ("p1", "p2", "p3")
    ]
)


def test_summary_and_candidates():
    links = rechecked(
        [
            ("p1", ["service_way", "ambiguous_candidates"], []),
            ("p2", [], ["restricted_access"]),
            ("p3", [], []),
        ]
    )
    summary, cands = check_uncertain(links, PHOTOS)
    assert summary["file_flags"]["service_way"] == 1
    assert summary["own_flags"]["restricted_access"] == 1
    assert summary["own_flags"]["grade_separated_nearby"] == 0
    assert summary["photos_with_flag"] == 2
    assert [c.photo_id for c in cands] == ["p1", "p2"]  # TAC-002-04
    assert cands[0].file_flags == ("ambiguous_candidates", "service_way")
    assert cands[0].distance_m == 3.0  # 0,1 m (AC-17)
    assert cands[0].photo_url == "https://x/p1"


def test_label_uncertain_for_other_checks():
    links = rechecked([("p1", ["service_way"], ["link_recheck_mismatch"]), ("p3", [], [])])
    c1 = Candidate(
        check="C1", reason_code="missing_lit", osm_id=1, photo_id="p1", photo_ids=("p1", "p3")
    )
    c2 = Candidate(
        check="C2", reason_code="speed_mismatch", osm_id=1, photo_id="p3", photo_ids=("p3",)
    )
    label_uncertain([c1, c2], links)
    assert c1.uncertain_link and c1.file_flags == ("service_way",)
    assert c1.own_flags == ("link_recheck_mismatch",)
    assert "niepewn" in c1.description_pl.lower()
    assert not c2.uncertain_link
