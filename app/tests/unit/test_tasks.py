"""AC-33, AC-35; ADR-004 §3.2."""

import hashlib

from map_qa.model import Candidate
from map_qa.tasks import build_tasks, task_id


def test_task_id_formula():
    c = Candidate(
        check="C2",
        reason_code="speed_mismatch",
        osm_id=5,
        segment_id="s",
        rule_index=0,
        direction="both",
        photo_id="p",
    )
    expected = hashlib.sha256(b"C2|speed_mismatch|5|s|0|both|p").hexdigest()[:16]
    assert task_id(c) == expected


def test_empty_fields_as_empty_text():
    c = Candidate(check="C1", reason_code="missing_lit", osm_id=5)
    assert task_id(c) == hashlib.sha256(b"C1|missing_lit|5||||").hexdigest()[:16]


def test_same_candidate_same_id_and_dedup():
    a = Candidate(check="C1", reason_code="missing_lit", osm_id=5, photo_id="p")
    b = Candidate(check="C1", reason_code="missing_lit", osm_id=5, photo_id="p")
    tasks = build_tasks([a, b])
    assert len(tasks) == 1 and tasks[0].task_id == task_id(a)


def test_deterministic_order():
    cands = [
        Candidate(check="C4-manual", reason_code="unreadable", photo_id="x"),
        Candidate(check="C3", reason_code="uncertain_link", osm_id=2, photo_id="b"),
        Candidate(check="C1", reason_code="missing_surface", osm_id=1),
        Candidate(check="C1", reason_code="missing_lit", osm_id=9),
        Candidate(check="C1", reason_code="missing_lit", osm_id=None),
        Candidate(check="C2", reason_code="speed_mismatch", osm_id=1, segment_id="z"),
        Candidate(check="C3", reason_code="uncertain_link", osm_id=2, photo_id="a"),
    ]
    order = [
        (t.candidate.check, t.candidate.reason_code, t.candidate.osm_id, t.candidate.photo_id)
        for t in build_tasks(cands)
    ]
    assert order == [
        ("C1", "missing_lit", None, ""),
        ("C1", "missing_lit", 9, ""),
        ("C1", "missing_surface", 1, ""),
        ("C2", "speed_mismatch", 1, ""),
        ("C3", "uncertain_link", 2, "a"),
        ("C3", "uncertain_link", 2, "b"),
        ("C4-manual", "unreadable", None, "x"),
    ]
    assert build_tasks(list(reversed(cands))) == build_tasks(cands)
