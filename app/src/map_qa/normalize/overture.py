"""Normalizacja reguł i źródeł Overture (ADR-001 §3.3, D-102).

Wejściem są elementy list jako tekst JSON z DuckDB (`to_json`), więc `raw_json` to pełna
struktura elementu bez skracania.
"""

from __future__ import annotations

import json
import re

from map_qa.model import OvertureRule, OvertureSource
from map_qa.normalize.osm import MPH_TO_KMH

_RE_WAY = re.compile(r"^w(\d+)@\d+$")
CONDITION_FIELDS = ("during", "using", "recognized", "mode", "vehicle")


def _whole(between: list | None) -> tuple[bool, float | None, float | None]:
    if not between:
        return True, None, None
    start, end = float(between[0]), float(between[1])
    return (start == 0.0 and end == 1.0), start, end


def _non_empty(value: object) -> bool:
    return value not in (None, "", [], {})


def rules_for_segment(
    segment_id: str, speed_limits: list[str], road_surface: list[str]
) -> list[OvertureRule]:
    """Jedna reguła = jeden rekord, z indeksem pozycji na liście (AC-05)."""
    rules: list[OvertureRule] = []
    for idx, raw in enumerate(speed_limits or []):
        item = json.loads(raw)
        max_speed = item.get("max_speed") or {}
        value = max_speed.get("value")
        unit = max_speed.get("unit")
        value_kmh = None
        if value is not None:
            value_kmh = round(float(value) * MPH_TO_KMH, 1) if unit == "mph" else float(value)
        when = item.get("when") or {}
        when_set = {k: v for k, v in when.items() if _non_empty(v)}
        heading = when_set.get("heading")
        unconditional = not any(k in when_set for k in CONDITION_FIELDS)
        whole, start, end = _whole(item.get("between"))
        rules.append(
            OvertureRule(
                segment_id=segment_id,
                rule_kind="speed",
                rule_index=idx,
                raw_json=raw,
                value_kmh=value_kmh,
                unit_raw=unit,
                when_raw=json.dumps(when, ensure_ascii=False) if when_set else None,
                heading=heading,
                between_start=start,
                between_end=end,
                whole_segment=whole,
                unconditional=unconditional,
                is_variable=bool(item.get("is_max_speed_variable")),
            )
        )
    for idx, raw in enumerate(road_surface or []):
        item = json.loads(raw)
        whole, start, end = _whole(item.get("between"))
        rules.append(
            OvertureRule(
                segment_id=segment_id,
                rule_kind="surface",
                rule_index=idx,
                raw_json=raw,
                surface_raw=item.get("value"),
                between_start=start,
                between_end=end,
                whole_segment=whole,
                unconditional=True,  # road_surface nie ma `when` (profil M2)
            )
        )
    return rules


def osm_way_id_from_record(record_id: str | None) -> int | None:
    if not record_id:
        return None
    m = _RE_WAY.match(record_id)
    return int(m.group(1)) if m else None


def sources_for_segment(segment_id: str, sources: list[str]) -> list[OvertureSource]:
    out: list[OvertureSource] = []
    for idx, raw in enumerate(sources or []):
        item = json.loads(raw)
        whole, start, end = _whole(item.get("between"))
        out.append(
            OvertureSource(
                segment_id=segment_id,
                source_index=idx,
                dataset=item.get("dataset"),
                record_id=item.get("record_id"),
                osm_way_id=osm_way_id_from_record(item.get("record_id")),
                source_between_start=start,
                source_between_end=end,
                source_whole_segment=whole,
            )
        )
    return out
