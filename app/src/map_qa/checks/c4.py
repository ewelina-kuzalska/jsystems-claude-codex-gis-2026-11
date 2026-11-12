"""C4: porównanie odczytu znaku z mapą i kolejka ręczna (AC-27, AC-28a, ADR-003 §3.8)."""

from __future__ import annotations

import json

import pandas as pd
from shapely.geometry import Point

from map_qa.model import Candidate, NotComparable, SignResolution, SignRoadContext

HEADING_NOTE = (
    "Kierunek aparatu nie jest kierunkiem jazdy. Najbliższa droga nie dowodzi, że znak jej "
    "dotyczy. Odczyt modelu nie jest prawdą terenową."
)
MANUAL_LABELS = {
    "below_threshold": "odpowiedzi AI poniżej progu pewności",
    "unreadable": "AI uznało znak za nieczytelny",
    "model_unavailable": "model niedostępny albo wycinek odrzucony przed wysłaniem",
    "budget_exhausted": "wyczerpany limit żądań lub kosztu",
}


def _fmt(v: float | None) -> str:
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def _base(
    res: SignResolution, ctx: SignRoadContext | None, sign, nearest, tags_raw=None
) -> Candidate:
    t1, t2 = res.tier1, res.tier2
    dist = (nearest or {}).get("distance_m", "")
    flags = ctx.flags if ctx else ()
    return Candidate(
        check="C4",
        reason_code="",
        osm_id=ctx.osm_way_id if ctx else None,
        photo_id=res.photo_id,
        photo_ids=(res.photo_id,),
        photo_url=str(sign.get("source_url", "")),
        photo_author=str(sign.get("creator", "")),
        photo_license=str(sign.get("license", "")),
        # Pełne tagi drogi ze snapshotu (AC-04); dla way spoza snapshotu tylko tagi prędkości.
        osm_raw=tags_raw or (json.dumps(ctx.osm_speed_raw, ensure_ascii=False) if ctx else ""),
        osm_normalized=_fmt(ctx.osm_value_kmh) if ctx else "",
        distance_m=round(float(dist), 1) if dist not in ("", None) else None,
        uncertain_link=bool(flags),
        file_flags=tuple(flags),
        resolved_by=res.resolved_by,
        tier1_model=t1.model_id if t1 else "",
        tier1_answer=(t1.answer or "") if t1 else "",
        tier1_probability=t1.probability if t1 else None,
        tier2_answer=(t2.answer or "") if t2 else "",
        tier2_confidence=t2.probability if t2 else None,
        mapillary_value=str(sign.get("mapillary_value", "")),
        geometry=Point(float(sign["longitude"]), float(sign["latitude"])),
        extra={
            "osm_speed_tags": ", ".join(
                f"{k}={v}" for k, v in (ctx.osm_speed_raw if ctx else {}).items()
            ),
        },
    )


def compare_signs(
    resolutions: list[SignResolution],
    contexts: dict[str, SignRoadContext],
    signs: pd.DataFrame,
    nearest: pd.DataFrame,
    osm_tags_raw: dict[int, str] | None = None,
) -> tuple[list[Candidate], list[NotComparable]]:
    osm_tags_raw = osm_tags_raw or {}
    sign_by = {r["photo_id"]: r for r in signs.to_dict("records")}
    near_by = {r["photo_id"]: r for r in nearest.to_dict("records")}
    candidates: list[Candidate] = []
    not_comparable: list[NotComparable] = []
    for res in resolutions:
        ctx = contexts.get(res.photo_id)
        sign = sign_by[res.photo_id]
        if res.resolved_by == "human_pending":
            cand = _base(
                res,
                ctx,
                sign,
                near_by.get(res.photo_id),
                osm_tags_raw.get(ctx.osm_way_id) if ctx else None,
            )
            cand.check = "C4-manual"
            cand.reason_code = res.manual_reason or "model_unavailable"
            detail = f" ({res.detail})" if res.detail else ""
            cand.description_pl = (
                f"Znak wymaga ręcznej kontroli: {MANUAL_LABELS.get(cand.reason_code, '')}"
                f"{detail}. Odpowiedzi AI (jeśli są) to tylko podpowiedzi. {HEADING_NOTE}"
            )
            candidates.append(cand)
            continue
        if res.resolved_by not in ("decision_model", "general_llm"):
            continue
        if res.final_value is None or not res.final_value.isdigit():
            continue  # `none` nie tworzy kandydata
        value = float(res.final_value)
        if ctx is None or ctx.status in ("outside_snapshot", "direction_unknown", "not_numeric"):
            reason = ctx.status if ctx else "outside_snapshot"
            not_comparable.append(
                NotComparable(
                    check="C4",
                    reason_code=reason,
                    osm_id=ctx.osm_way_id if ctx else None,
                    attribute="sign",
                    direction=ctx.chosen_direction if ctx else "",
                    osm_raw=json.dumps(ctx.osm_speed_raw, ensure_ascii=False) if ctx else "",
                    overture_raw="",
                    photo_id=res.photo_id,
                )
            )
            continue
        if ctx.status == "ok" and ctx.osm_value_kmh == value:
            continue
        cand = _base(
            res,
            ctx,
            sign,
            near_by.get(res.photo_id),
            osm_tags_raw.get(ctx.osm_way_id) if ctx else None,
        )
        tier = "model decyzyjny" if res.resolved_by == "decision_model" else "ogólny LLM"
        escalated = " Odpowiedź kroku 1 eskalowano do ogólnego LLM." if res.tier2 else ""
        if ctx.status == "missing":
            cand.reason_code = "osm_missing_speed"
            text = (
                f"Odczyt znaku ({tier}): {_fmt(value)} km/h; najbliższa droga OSM "
                f"{ctx.osm_way_id} nie ma maxspeed. Wymaga sprawdzenia."
            )
        else:
            cand.reason_code = "sign_mismatch"
            text = (
                f"Odczyt znaku ({tier}): {_fmt(value)} km/h; OSM ({ctx.chosen_direction}) "
                f"{_fmt(ctx.osm_value_kmh)} km/h. Kandydat wymaga sprawdzenia; różnica nie "
                "dowodzi błędu mapy."
            )
        cand.description_pl = f"{text}{escalated} {HEADING_NOTE}"
        candidates.append(cand)
    return candidates, not_comparable
