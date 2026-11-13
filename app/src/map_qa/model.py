"""Typy danych, kody przyczyn i enumy statusów (ADR-000 §5).

Po commicie T02 zmiany kontraktu wprowadza wyłącznie orkiestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- Kontrole i kolejność (ADR-004 §3.2) -------------------------------------------
CHECK_ORDER = ("C1", "C2", "C3", "C4", "C4-manual")

# --- Normalizacja prędkości (ADR-001 §3.2, D-101) ----------------------------------
SPEED_STATUSES = ("numeric", "not_numeric", "conditional")
SPEED_REASONS = frozenset({"zone", "none", "signals", "multi_value", "unparsable", "conditional"})
DIRECTIONS = ("both", "forward", "backward")

# --- Kody kandydatów ----------------------------------------------------------------
C1_ATTRIBUTES = ("maxspeed", "surface", "lanes", "lit")
C1_REASONS = tuple(f"missing_{a}" for a in C1_ATTRIBUTES)
C2_REASONS = ("speed_mismatch", "surface_family_mismatch")
C3_REASONS = ("uncertain_link",)
C4_REASONS = ("sign_mismatch", "osm_missing_speed")

# --- „Nieporównywalne” (ADR-001 §3.6, ADR-002 §3.4) --------------------------------
NOT_COMPARABLE_REASONS = frozenset(
    {
        "not_numeric",
        "conditional",
        "partial_segment",
        "partial_source",
        "direction_unknown",
        "variable",
        "multiple_rules",
        "unknown_family",
        "outside_snapshot",
    }
)

# --- Flagi niepewności (AC-16, ADR-002 §3.3) ----------------------------------------
FILE_FLAGS = (
    "ambiguous_candidates",
    "camera_against_way_direction",
    "panorama_heading_ambiguous",
    "poor_heading_alignment",
    "missing_heading",
    "service_way",
    "boundary_crossing",
    "overture_spatial_only",
    "no_osm_within_25m",
)
OWN_FLAGS = ("link_recheck_mismatch", "restricted_access", "grade_separated_nearby")

# --- C4 (ADR-003) -------------------------------------------------------------------
RESOLVED_BY = ("decision_model", "general_llm", "human_pending", "not_run")
MANUAL_REASONS = ("below_threshold", "unreadable", "model_unavailable", "budget_exhausted")
REQUEST_OUTCOMES = ("ok", "cached", "http_error", "timeout", "invalid_response", "not_sent")
STOP_REASONS = ("none", "budget_exhausted", "model_unavailable", "cost_limit")

# --- Błędy wejść (ADR-001 §3.1, ADR-002 §3.1) --------------------------------------
INPUT_ERROR_REASONS = (
    "missing",
    "hash_mismatch",
    "unreadable",
    "row_count_mismatch",
    "crs_mismatch",
    "input_dir_missing",
)

REASON_LABELS_PL = {
    "missing": "brak pliku",
    "hash_mismatch": "niezgodny SHA-256 z manifestem",
    "unreadable": "nie można odczytać pliku",
    "row_count_mismatch": "liczba wierszy niezgodna z manifestem",
    "crs_mismatch": "układ współrzędnych niezgodny z manifestem",
    "input_dir_missing": "brak katalogu wejść",
}


class InputError(Exception):
    """Błąd wejścia: plik i kod przyczyny (kod wyjścia 2)."""

    def __init__(self, file: str, reason: str, detail: str = "") -> None:
        self.file = file
        self.reason = reason
        self.detail = detail
        label = REASON_LABELS_PL.get(reason, reason)
        msg = f"{file}: {label} ({reason})"
        if detail:
            msg += f" — {detail}"
        super().__init__(msg)


@dataclass(frozen=True)
class Snapshot:
    input_dir: Any
    osm_extract_date: str
    overture_release: str
    created_at: str
    rows: dict[str, int]
    osm_crs: str
    overture_crs: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpeedValue:
    osm_id: int
    tag_key: str
    raw: str
    value_kmh: float | None
    status: str
    reason: str | None
    direction: str


@dataclass(frozen=True)
class OvertureRule:
    segment_id: str
    rule_kind: str  # speed | surface
    rule_index: int
    raw_json: str
    value_kmh: float | None = None
    surface_raw: str | None = None
    unit_raw: str | None = None
    when_raw: str | None = None
    heading: str | None = None
    between_start: float | None = None
    between_end: float | None = None
    whole_segment: bool = True
    unconditional: bool = True
    is_variable: bool = False


@dataclass(frozen=True)
class OvertureSource:
    segment_id: str
    source_index: int
    dataset: str | None
    record_id: str | None
    osm_way_id: int | None
    source_between_start: float | None
    source_between_end: float | None
    source_whole_segment: bool


@dataclass
class Candidate:
    """Kandydat do sprawdzenia albo pozycja kolejki ręcznej (ADR-000 §5, ADR-004 §3.6)."""

    check: str
    reason_code: str
    osm_id: int | None = None
    segment_id: str = ""
    rule_index: int | None = None
    direction: str = ""
    photo_id: str = ""
    photo_ids: tuple[str, ...] = ()
    photo_url: str = ""
    photo_author: str = ""
    photo_license: str = ""
    osm_raw: str = ""
    osm_normalized: str = ""
    overture_raw: str = ""
    overture_normalized: str = ""
    distance_m: float | None = None
    uncertain_link: bool = False
    file_flags: tuple[str, ...] = ()
    own_flags: tuple[str, ...] = ()
    resolved_by: str = ""
    tier1_model: str = ""
    tier1_answer: str = ""
    tier1_probability: float | None = None
    tier2_answer: str = ""
    tier2_confidence: float | None = None
    mapillary_value: str = ""
    description_pl: str = ""
    geometry: Any = None  # shapely, EPSG:4326 lon/lat
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NotComparable:
    check: str
    reason_code: str
    osm_id: int | None = None
    segment_id: str = ""
    rule_index: int | None = None
    direction: str = ""
    attribute: str = ""
    osm_raw: str = ""
    overture_raw: str = ""
    photo_id: str = ""


@dataclass(frozen=True)
class SignReading:
    photo_id: str
    crop_sha256: str
    tier: int
    model_id: str
    answer: str | None  # "50" | "none" | "unreadable" | "other" | None (błąd)
    probability: float | None
    probabilities: dict[str, float] | None
    request_outcome: str
    cost_usd: float | None = None
    cache_key: str = ""
    sent_sha256: str = ""
    error: str = ""
    elapsed_s: float | None = None


@dataclass(frozen=True)
class SignResolution:
    photo_id: str
    resolved_by: str
    final_value: str | None = None  # "50" | "none" | None
    manual_reason: str | None = None
    detail: str = ""
    tier1: SignReading | None = None
    tier2: SignReading | None = None


@dataclass(frozen=True)
class SignRoadContext:
    photo_id: str
    osm_way_id: int | None
    osm_speed_raw: dict[str, str]
    chosen_direction: str  # both | forward | backward | unknown
    osm_value_kmh: float | None
    status: str  # ok | missing | not_numeric | direction_unknown | outside_snapshot
    directed_diff: float | None
    flags: tuple[str, ...] = ()
    oneway: str = ""


@dataclass
class Task:
    """Zadanie eksportu: kandydat ze stabilnym `task_id` (ADR-004 §3.2)."""

    task_id: str
    candidate: Candidate
