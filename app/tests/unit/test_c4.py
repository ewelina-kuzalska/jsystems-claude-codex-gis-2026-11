"""AC-27, AC-28a, AC-29; ADR-003 §3.8; ADR-004 §3.4, §3.6, §3.8."""

import pandas as pd

from map_qa.checks.c4 import compare_signs
from map_qa.model import SignReading, SignResolution, SignRoadContext

SIGNS = pd.DataFrame(
    [
        {
            "photo_id": p,
            "longitude": "19.9",
            "latitude": "50.0",
            "source_url": f"https://www.mapillary.com/app/?pKey={p}",
            "creator": "autor",
            "license": "CC-BY-SA-4.0",
            "mapillary_value": "regulatory--maximum-speed-limit-50--g1",
        }
        for p in ("a", "b", "c", "d", "e", "f", "g")
    ]
)
NEAREST = pd.DataFrame([{"photo_id": p, "distance_m": "3.04"} for p in "abcdefg"])


def rd(pid, tier, answer, p):
    return SignReading(
        pid,
        "s",
        tier,
        "typesafe/jev-1.14" if tier == 1 else "openai/gpt-6-luna",
        answer,
        p,
        None,
        "ok",
    )


def ctx(pid, status="ok", value=50.0, flags=()):
    return SignRoadContext(
        pid,
        7,
        {"maxspeed": "50", "maxspeed:conditional": "110 @ (x)"},
        "both" if status == "ok" else "unknown",
        value,
        status,
        10.0,
        tuple(flags),
    )


def test_compare_and_manual_queue():
    resolutions = [
        SignResolution("a", "decision_model", "70", None, "", rd("a", 1, "70", 0.9)),
        SignResolution(
            "b", "general_llm", "50", None, "", rd("b", 1, "unreadable", 0.8), rd("b", 2, "50", 0.9)
        ),
        SignResolution("c", "decision_model", "70", None, "", rd("c", 1, "70", 0.9)),
        SignResolution("d", "decision_model", "none", None, "", rd("d", 1, "none", 0.9)),
        SignResolution(
            "e",
            "human_pending",
            None,
            "below_threshold",
            "",
            rd("e", 1, "50", 0.3),
            rd("e", 2, "40", 0.4),
        ),
        SignResolution("f", "decision_model", "60", None, "", rd("f", 1, "60", 0.9)),
        SignResolution("g", "not_run"),
    ]
    contexts = {
        "a": ctx("a", flags=("outside_standard_25m",)),
        "b": ctx("b"),
        "c": ctx("c", status="outside_snapshot", value=None),
        "d": ctx("d"),
        "e": ctx("e"),
        "f": ctx("f", status="missing", value=None),
        "g": ctx("g"),
    }
    cands, nc = compare_signs(resolutions, contexts, SIGNS, NEAREST)
    by = {c.photo_id: c for c in cands}
    a = by["a"]
    assert (a.check, a.reason_code, a.resolved_by, a.osm_id) == (
        "C4",
        "sign_mismatch",
        "decision_model",
        7,
    )
    assert a.tier1_answer == "70" and a.tier1_probability == 0.9 and a.tier1_model
    assert a.mapillary_value.startswith("regulatory--maximum-speed-limit-50")
    assert "maxspeed:conditional" in a.extra["osm_speed_tags"]  # surowe tagi (AC-27)
    assert a.uncertain_link and a.file_flags == ("outside_standard_25m",)
    assert a.distance_m == 3.0
    assert "Kierunek aparatu nie jest kierunkiem jazdy" in a.description_pl
    assert "b" not in by  # 50 == 50
    assert [(n.photo_id, n.reason_code, n.check) for n in nc] == [("c", "outside_snapshot", "C4")]
    assert "d" not in by  # none nie tworzy kandydata
    m = by["e"]
    assert (m.check, m.reason_code, m.resolved_by) == (
        "C4-manual",
        "below_threshold",
        "human_pending",
    )
    assert m.tier2_answer == "40" and m.tier2_confidence == 0.4
    assert "etykiet" not in m.description_pl.lower()  # bez etykiety referencyjnej (AC-28a)
    assert (by["f"].check, by["f"].reason_code) == ("C4", "osm_missing_speed")
    assert "g" not in by


def test_escalation_note_kept():
    res = [
        SignResolution(
            "b", "general_llm", "70", None, "", rd("b", 1, "unreadable", 0.8), rd("b", 2, "70", 0.9)
        )
    ]
    (c,), _ = compare_signs(res, {"b": ctx("b")}, SIGNS, NEAREST)
    assert c.tier1_answer == "unreadable" and "eskalowano do ogólnego LLM" in c.description_pl


def test_direction_unknown_not_comparable():
    res = [SignResolution("a", "decision_model", "70", None, "", rd("a", 1, "70", 0.9))]
    cands, nc = compare_signs(
        res, {"a": ctx("a", status="direction_unknown", value=None)}, SIGNS, NEAREST
    )
    assert cands == [] and nc[0].reason_code == "direction_unknown"


def test_full_osm_tags_exported_for_snapshot_way():  # AC-04, przegląd T27
    res = [SignResolution("a", "decision_model", "70", None, "", rd("a", 1, "70", 0.9))]
    full = '{"highway":"primary","maxspeed":"50","surface":"asphalt"}'
    (c,), _ = compare_signs(res, {"a": ctx("a")}, SIGNS, NEAREST, osm_tags_raw={7: full})
    assert c.osm_raw == full
    assert "maxspeed=50" in c.extra["osm_speed_tags"]
