"""Ewaluacja odczytów względem roboczej referencji (AC-28, ADR-003 §3.9).

Jedyny moduł, który otwiera `signs/labels.csv` (TAC-003-04), i to dopiero po rozstrzygnięciu.
Etykiety to zgodność dwóch modeli AI, nie prawda terenowa.
"""

from __future__ import annotations

import csv
from pathlib import Path

from map_qa.model import MANUAL_REASONS, SignResolution

FINAL = ("decision_model", "general_llm")


def label_value(row: dict) -> str | None:
    """Mapowanie wyłącznie po `sign_value` (nie po `negative_type`)."""
    value = (row.get("sign_value") or "").strip()
    if value.isdigit() or value in ("none", "unreadable"):
        return value
    return None


def evaluate(resolutions: list[SignResolution], labels_path: Path) -> dict:
    with Path(labels_path).open(encoding="utf-8", newline="") as f:
        labels = {r["photo_id"]: r for r in csv.DictReader(f)}
    processed = [r for r in resolutions if r.resolved_by != "not_run"]
    certain: dict[str, str] = {}
    uncertain = unparsable = 0
    for r in processed:
        row = labels.get(r.photo_id)
        if row is None:
            continue
        value = label_value(row)
        if value is None:
            unparsable += 1
        elif row.get("status") != "certain":
            uncertain += 1
        else:
            certain[r.photo_id] = value

    def score(rows) -> tuple[int, int]:
        rows = [r for r in rows if r.photo_id in certain]
        return sum(r.final_value == certain[r.photo_id] for r in rows), len(rows)

    t1 = score(r for r in processed if r.resolved_by == "decision_model")
    t2 = score(r for r in processed if r.resolved_by == "general_llm")
    all_final = score(r for r in processed if r.resolved_by in FINAL)
    raw = [r for r in processed if r.tier1 is not None and r.photo_id in certain]
    raw_t1 = (sum(r.tier1.answer == certain[r.photo_id] for r in raw), len(raw))
    manual: dict[str, int] = {}
    for r in processed:
        if r.resolved_by == "human_pending":
            manual[r.manual_reason] = manual.get(r.manual_reason, 0) + 1
    final = sum(r.resolved_by in FINAL for r in processed)
    return {
        "accuracy": [
            {"key": "tier1", "label": "Krok 1 — ostateczne", "correct": t1[0], "evaluated": t1[1]},
            {"key": "tier2", "label": "Krok 2 — ostateczne", "correct": t2[0], "evaluated": t2[1]},
            {
                "key": "all",
                "label": "Wszystkie ostateczne AI",
                "correct": all_final[0],
                "evaluated": all_final[1],
            },
        ],
        "raw_tier1": raw_t1,
        "coverage": (final, len(processed)),
        "manual_by_reason": {k: manual[k] for k in MANUAL_REASONS if k in manual},
        "uncertain_labels": uncertain,
        "label_unparsable": unparsable,
    }
