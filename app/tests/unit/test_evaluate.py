"""AC-28; ADR-003 §3.9 (mapowanie po sign_value, tylko `certain`, decyzja 3A)."""

import csv

from map_qa.model import SignReading, SignResolution
from map_qa.signs.evaluate import evaluate, label_value

HEADER = ["photo_id", "sign_value", "status", "method", "reviewers", "note", "negative_type"]


def labels(tmp_path, rows):
    path = tmp_path / "labels.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)
    return path


def rd(pid, tier, answer, p=0.9):
    return SignReading(pid, "s", tier, f"m{tier}", answer, p, None, "ok")


def res(pid, by, value=None, reason=None, t1=None, t2=None):
    return SignResolution(pid, by, value, reason, "", t1, t2)


def test_label_mapping_by_sign_value():
    assert label_value({"sign_value": "50", "negative_type": ""}) == "50"
    assert label_value({"sign_value": "none", "negative_type": "no_entry"}) == "none"
    assert label_value({"sign_value": "unreadable", "negative_type": "unreadable"}) == "unreadable"
    assert label_value({"sign_value": "??", "negative_type": ""}) is None


def test_metrics(tmp_path):
    path = labels(
        tmp_path,
        [
            ["a", "50", "certain", "", "", "", ""],
            ["b", "none", "certain", "", "", "", "no_entry"],
            ["c", "unreadable", "certain", "", "", "", "unreadable"],
            ["d", "40", "certain", "", "", "", ""],
            ["e", "none", "uncertain", "", "", "", "zone"],
            ["f", "x?", "certain", "", "", "", ""],
            ["g", "70", "certain", "", "", "", ""],
        ],
    )
    resolutions = [
        res("a", "decision_model", "50", t1=rd("a", 1, "50")),
        res("b", "general_llm", "none", t1=rd("b", 1, "50", 0.2), t2=rd("b", 2, "none")),
        res("c", "decision_model", "50", t1=rd("c", 1, "50")),  # unreadable + final = błąd (3A)
        res(
            "d",
            "human_pending",
            reason="below_threshold",
            t1=rd("d", 1, "40", 0.3),
            t2=rd("d", 2, "40", 0.3),
        ),
        res("e", "decision_model", "none", t1=rd("e", 1, "none")),
        res("f", "decision_model", "50", t1=rd("f", 1, "50")),
        res("g", "not_run"),
    ]
    m = evaluate(resolutions, path)
    acc = {a["key"]: (a["correct"], a["evaluated"]) for a in m["accuracy"]}
    assert acc["tier1"] == (1, 2)  # a ok, c błąd; e uncertain i f unparsable poza mianownikiem
    assert acc["tier2"] == (1, 1)
    assert acc["all"] == (2, 3)
    assert m["raw_tier1"] == (2, 4)  # a, d trafne; b, c chybione (wszystkie odpowiedzi kroku 1)
    assert m["coverage"] == (5, 6)  # ostateczne / przetworzone (bez not_run)
    assert m["manual_by_reason"] == {"below_threshold": 1}
    assert m["uncertain_labels"] == 1 and m["label_unparsable"] == 1
