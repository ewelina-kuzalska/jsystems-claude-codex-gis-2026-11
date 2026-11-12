"""Normalizacja tagów prędkości OSM (ADR-001 §3.2, D-101).

Surowe `tags` przechodzą bez zmian do eksportu (AC-04); tu tylko je czytamy.
"""

from __future__ import annotations

import json
import re

from map_qa.model import SpeedValue

MPH_TO_KMH = 1.609344
SPEED_KEYS = ("maxspeed", "maxspeed:forward", "maxspeed:backward")
CONDITIONAL_KEY = "maxspeed:conditional"
CONTEXT_KEYS = ("maxspeed:type", "source:maxspeed", "zone:maxspeed")
DIRECTION_OF = {"maxspeed": "both", "maxspeed:forward": "forward", "maxspeed:backward": "backward"}

_NUM = r"(\d+(?:\.\d+)?)"
_RE_PLAIN = re.compile(rf"^{_NUM}$")
_RE_KMH = re.compile(rf"^{_NUM}\s*(?:km/h|kmh)$")
_RE_MPH = re.compile(rf"^{_NUM}\s*mph$")
_RE_KNOTS = re.compile(rf"^{_NUM}\s*knots$")
_RE_ZONE = re.compile(r"^[A-Za-z]{2}:[A-Za-z0-9_]+$")


def parse_maxspeed(raw: str | None) -> tuple[str, float | None, str | None] | None:
    """(status, value_kmh, reason) albo None, gdy wartości brak (`missing`)."""
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return None
    if ";" in text or "|" in text:
        return ("not_numeric", None, "multi_value")
    for pattern in (_RE_PLAIN, _RE_KMH):
        m = pattern.match(text)
        if m:
            return ("numeric", float(m.group(1)), None)
    m = _RE_MPH.match(text)
    if m:
        return ("numeric", round(float(m.group(1)) * MPH_TO_KMH, 1), None)
    if _RE_KNOTS.match(text):
        return ("not_numeric", None, "unparsable")
    if _RE_ZONE.match(text):
        return ("not_numeric", None, "zone")
    if text == "none":
        return ("not_numeric", None, "none")
    if text == "signals":
        return ("not_numeric", None, "signals")
    if text == "walk":
        return ("not_numeric", None, "zone")
    return ("not_numeric", None, "unparsable")


def load_tags(tags_raw: str | None) -> dict[str, str]:
    if not tags_raw:
        return {}
    try:
        data = json.loads(tags_raw)
    except ValueError:
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def speed_values(osm_id: int, tags_raw: str | None) -> list[SpeedValue]:
    """Jeden `SpeedValue` na każdy obecny klucz prędkości, kontekstu i warunku."""
    tags = load_tags(tags_raw)
    out: list[SpeedValue] = []
    for key in SPEED_KEYS:
        parsed = parse_maxspeed(tags.get(key))
        if parsed is None:
            continue
        status, value, reason = parsed
        out.append(SpeedValue(osm_id, key, tags[key], value, status, reason, DIRECTION_OF[key]))
    if tags.get(CONDITIONAL_KEY, "").strip():
        out.append(
            SpeedValue(
                osm_id,
                CONDITIONAL_KEY,
                tags[CONDITIONAL_KEY],
                None,
                "conditional",
                "conditional",
                "both",
            )
        )
    for key in CONTEXT_KEYS:
        if tags.get(key, "").strip():
            out.append(SpeedValue(osm_id, key, tags[key], None, "not_numeric", None, "both"))
    return out


def speed_for_direction(values: list[SpeedValue], direction: str) -> SpeedValue | None:
    """Wartość dla kierunku; `forward`/`backward` dziedziczą `both` (ADR-001 §3.6)."""
    by_key = {v.tag_key: v for v in values}
    if direction == "both":
        return by_key.get("maxspeed")
    return by_key.get(f"maxspeed:{direction}") or by_key.get("maxspeed")


def has_speed(tags_raw: str | None) -> bool:
    tags = load_tags(tags_raw)
    return any(tags.get(k, "").strip() for k in SPEED_KEYS)


def speed_raw_tags(tags_raw: str | None) -> dict[str, str]:
    """Wszystkie klucze zaczynające się od `maxspeed` (do prezentacji, AC-27)."""
    tags = load_tags(tags_raw)
    return {k: v for k, v in sorted(tags.items()) if k.startswith("maxspeed")}
