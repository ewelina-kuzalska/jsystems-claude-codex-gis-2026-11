"""Eskalacja odczytu znaku: krok 1 → krok 2 → kolejka ręczna (ADR-003 §3.1, §3.5–3.7, §3.10).

Moduł nie czyta etykiet referencyjnych (TAC-003-04). Płatna pętla staje przy pierwszym błędzie
albo wyczerpaniu budżetu; wyniki z cache są używane nadal, bo nie są płatnymi żądaniami.
"""

from __future__ import annotations

from dataclasses import dataclass

from map_qa.ai_client import (
    SPEED_OPTIONS,
    BudgetExhausted,
    ModelUnavailable,
    RequestBudget,
    redact,
)
from map_qa.cache import AiCache
from map_qa.model import SignReading, SignResolution

FINAL_TIER1 = frozenset((*SPEED_OPTIONS, "none"))


@dataclass(frozen=True)
class CropItem:
    photo_id: str
    crop_sha256: str
    data: bytes | None
    invalid_reason: str | None  # crop_invalid | unsupported_format | metadata_present


@dataclass(frozen=True)
class SignPlan:
    sample_size: int
    cached_tier1: int
    new_tier1: int
    worst_tier2: int
    not_run: int
    invalid: int
    limit: int
    threshold: float
    cost_limit: float


class _Stopped(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


def _cached_reading(entry: dict, item: CropItem, tier: int, model: str, key: str) -> SignReading:
    interp = entry["interpretation"]
    return SignReading(
        photo_id=item.photo_id,
        crop_sha256=item.crop_sha256,
        tier=tier,
        model_id=model,
        answer=interp["answer"],
        probability=interp["probability"],
        probabilities=interp.get("probabilities"),
        request_outcome="cached",
        cost_usd=interp.get("cost_usd"),
        cache_key=key,
    )


def _cache_entry(cache: AiCache, reader, tier: int, item: CropItem):
    _, _, key = reader.prepare(tier, item.crop_sha256, item.data)
    return key, cache.get(key)


def select_sample(items: list[CropItem], cache: AiCache, reader, new_crop_budget: int):
    """Najpierw wycinki z krokiem 1 w cache, potem nowe do `floor(limit/2)` (ADR-003 §3.1)."""
    ordered = sorted(items, key=lambda x: x.photo_id)
    cached, new, invalid, not_run = [], [], [], []
    for item in ordered:
        if item.invalid_reason:
            invalid.append(item)
        elif _cache_entry(cache, reader, 1, item)[1] is not None:
            cached.append(item)
        elif len(new) < new_crop_budget:
            new.append(item)
        else:
            not_run.append(item)
    return cached + new + invalid, not_run


def plan_sign_run(
    sample: list[CropItem],
    cache: AiCache,
    reader,
    *,
    threshold: float,
    limit: int,
    cost_limit: float,
    not_run: int = 0,
) -> SignPlan:
    cached = new = worst2 = invalid = 0
    for item in sample:
        if item.invalid_reason:
            invalid += 1
            continue
        key, entry = _cache_entry(cache, reader, 1, item)
        if entry is None:
            new += 1
            worst2 += 1
            continue
        cached += 1
        interp = entry["interpretation"]
        final = interp["answer"] in FINAL_TIER1 and interp["probability"] >= threshold
        if not final and _cache_entry(cache, reader, 2, item)[1] is None:
            worst2 += 1
    return SignPlan(
        len(sample), cached, new, worst2, not_run, invalid, limit, threshold, cost_limit
    )


def _is_value_or_none(answer: str | None) -> bool:
    return answer == "none" or (answer is not None and answer.isdigit())


def resolve_signs(
    sample: list[CropItem], budget: RequestBudget, cache: AiCache, reader, threshold: float
) -> list[SignResolution]:
    """Jedno `SignResolution` na każdy wycinek próbki, w dokładnie jednym stanie (AC-22e)."""
    stopped: str | None = None
    out: list[SignResolution] = []

    def get(tier: int, item: CropItem) -> SignReading:
        nonlocal stopped
        key, entry = _cache_entry(cache, reader, tier, item)
        model = reader.model_for(tier)
        if entry is not None:
            return _cached_reading(entry, item, tier, model, key)
        if stopped:
            raise _Stopped(stopped)
        try:
            read = reader.read_tier1 if tier == 1 else reader.read_tier2
            reading, new_entry = read(item.photo_id, item.crop_sha256, item.data, budget)
        except BudgetExhausted as exc:
            stopped = "budget_exhausted"
            budget.stop(exc.reason, item.photo_id)
            raise _Stopped(stopped) from exc
        except ModelUnavailable as exc:
            stopped = "model_unavailable"
            budget.stop("model_unavailable", item.photo_id)
            budget.last_error = redact(f"{exc.reason} {exc.detail}".strip())
            raise _Stopped(stopped) from exc
        cache.put(key, new_entry)
        return reading

    for item in sample:
        if item.invalid_reason:
            out.append(
                SignResolution(
                    item.photo_id, "human_pending", None, "model_unavailable", item.invalid_reason
                )
            )
            continue
        t1 = t2 = None
        try:
            t1 = get(1, item)
            if t1.answer in FINAL_TIER1 and t1.probability >= threshold:
                out.append(
                    SignResolution(item.photo_id, "decision_model", t1.answer, None, "", t1, None)
                )
                continue
            t2 = get(2, item)
        except _Stopped as stop:
            out.append(
                SignResolution(item.photo_id, "human_pending", None, stop.reason, "", t1, t2)
            )
            continue
        if _is_value_or_none(t2.answer) and t2.probability >= threshold:
            out.append(SignResolution(item.photo_id, "general_llm", t2.answer, None, "", t1, t2))
        else:
            reason = "unreadable" if t2.answer == "unreadable" else "below_threshold"
            out.append(SignResolution(item.photo_id, "human_pending", None, reason, "", t1, t2))
    return out
