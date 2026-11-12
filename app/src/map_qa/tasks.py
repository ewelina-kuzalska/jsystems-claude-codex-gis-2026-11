"""Budowa zadań ze stabilnym `task_id` i deterministyczną kolejnością (ADR-004 §3.2)."""

from __future__ import annotations

import hashlib

from map_qa.model import CHECK_ORDER, Candidate, Task


def _text(value: object) -> str:
    return "" if value is None else str(value)


def task_id(c: Candidate) -> str:
    key = "|".join(
        _text(v)
        for v in (
            c.check,
            c.reason_code,
            c.osm_id,
            c.segment_id,
            c.rule_index,
            c.direction,
            c.photo_id,
        )
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _sort_key(t: Task) -> tuple:
    c = t.candidate
    return (
        CHECK_ORDER.index(c.check),
        c.reason_code,
        c.osm_id is not None,
        c.osm_id or 0,
        c.segment_id,
        c.photo_id,
        t.task_id,
    )


def build_tasks(candidates: list[Candidate]) -> list[Task]:
    """Zadania posortowane; duplikaty tego samego `task_id` są łączone (TAC-004-02)."""
    seen: dict[str, Task] = {}
    for c in candidates:
        tid = task_id(c)
        seen.setdefault(tid, Task(task_id=tid, candidate=c))
    return sorted(seen.values(), key=_sort_key)


def count_by_check(tasks: list[Task]) -> dict[str, int]:
    """Liczba zadań per kontrola, zawsze ze wszystkimi kluczami (AC-30, ADR-004 §3.7)."""
    counts = dict.fromkeys(CHECK_ORDER, 0)
    for t in tasks:
        counts[t.candidate.check] += 1
    return counts


def count_by_reason(tasks: list[Task]) -> list[tuple[str, str, int]]:
    out: dict[tuple[str, str], int] = {}
    for t in tasks:
        key = (t.candidate.check, t.candidate.reason_code)
        out[key] = out.get(key, 0) + 1
    return sorted(
        ((c, r, n) for (c, r), n in out.items()), key=lambda x: (CHECK_ORDER.index(x[0]), x[1])
    )
