"""Parametry uruchomienia i walidacja zakresów (ADR-000 §6.1, ADR-005, ADR-006 D-601)."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

TIER1_MODELS = {
    "jev": "typesafe/jev-1.14",
    "luna-decisions": "openai/gpt-6-luna-decisions",
}
TIER2_MODEL = "openai/gpt-6-luna"
MAX_REQUESTS_LIMIT = 25


class ConfigError(ValueError):
    """Niepoprawny parametr uruchomienia (kod wyjścia 2)."""


@dataclass(frozen=True)
class RunConfig:
    input_dir: Path
    output_dir: Path
    with_signs: bool = False
    max_requests: int = MAX_REQUESTS_LIMIT
    threshold: float = 0.7
    max_cost_usd: float = 0.50
    sign_sample: int | None = None
    tier1_model: str = "jev"
    yes: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.max_requests <= MAX_REQUESTS_LIMIT:
            raise ConfigError(f"--max-requests musi być w zakresie 1–{MAX_REQUESTS_LIMIT}")
        if not 0.0 <= self.threshold <= 1.0:
            raise ConfigError("--threshold musi być w zakresie 0–1")
        if not math.isfinite(self.max_cost_usd) or self.max_cost_usd < 0:
            raise ConfigError("--max-cost-usd musi być skończoną liczbą nieujemną")
        if self.sign_sample is not None and self.sign_sample < 0:
            raise ConfigError("--sign-sample nie może być ujemny")
        if self.tier1_model not in TIER1_MODELS:
            raise ConfigError(f"--tier1-model musi być jednym z: {', '.join(TIER1_MODELS)}")

    @property
    def tier1_model_id(self) -> str:
        return TIER1_MODELS[self.tier1_model]

    @property
    def tier2_model_id(self) -> str:
        return TIER2_MODEL

    @property
    def new_crop_budget(self) -> int:
        """Liczba nowych wycinków: floor(max_requests / 2), zmniejszana przez --sign-sample."""
        cap = self.max_requests // 2
        return cap if self.sign_sample is None else min(cap, self.sign_sample)

    @property
    def cache_dir(self) -> Path:
        env = os.environ.get("MAP_QA_CACHE_DIR")
        return Path(env) if env else self.input_dir / "data" / "cache" / "ai"
