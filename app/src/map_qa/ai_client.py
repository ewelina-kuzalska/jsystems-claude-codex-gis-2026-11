"""Klient OpenRouter dla C4: budowa żądań, budżet, termin 40 s, zero ponowień.

ADR-003 §3.3–3.6, D-05; ADR-006 D-601–D-603. Model dostaje wyłącznie obraz wycinka i stałe
pytanie (AC-21). Klucz API czytamy tylko tu, w chwili budowy nagłówka, i nigdy go nie logujemy.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from PIL import Image

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
JEV_MODEL = "typesafe/jev-1.14"
TIER2_MODEL = "openai/gpt-6-luna"
DEADLINE_S = 40.0
TIMEOUT = httpx.Timeout(connect=5.0, read=DEADLINE_S, write=5.0, pool=5.0)

# Dopóki parser nie przeszedł testów na zapisach T00b, C4 nie wysyła żądań (ADR-003 §3.6).
RESPONSE_CONTRACT_VERIFIED = False

STATE_TEXT_V1 = "An image crop from a street-level photograph."
QUESTION_V1 = (
    "Is there a round Polish B-33 maximum speed limit sign (red ring, black number) in this "
    "image? If yes, which number does it show?"
)
SPEED_OPTIONS = tuple(str(v) for v in range(10, 150, 10))
CRITERIA_V1 = {
    **dict.fromkeys(SPEED_OPTIONS, "a B-33 sign showing this number"),
    "other": "a B-33 sign whose number is not in this list",
    "none": "no B-33 sign; includes zone signs and end-of-limit signs",
    "unreadable": "a sign is present but its number cannot be read",
}
TIER1_OPTIONS = frozenset(CRITERIA_V1)
TIER2_ANSWERS = (*SPEED_OPTIONS, "other_value", "none", "unreadable")
SCHEMA_V1 = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "value_kmh", "confidence"],
    "properties": {
        "answer": {"type": "string", "enum": list(TIER2_ANSWERS)},
        "value_kmh": {"type": ["integer", "null"], "minimum": 5, "maximum": 140},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

# Limity obrazu Jev wg docs.typesafe.ai/images (ADR-006 D-603, potwierdzone w T00b).
JEV_MIN_SIDE, JEV_MAX_SIDE = 280, 1568
JEV_MIN_PIXELS, JEV_MAX_PIXELS = 78_400, 2_458_624
ALLOWED_HEADERS = ("content-type", "date", "x-request-id", "x-generation-id")


class ModelUnavailable(Exception):
    """Błąd żądania (status ≠ 2xx, timeout, sieć, niepoprawna odpowiedź). Bez ponowień."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


class BudgetExhausted(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass
class RequestBudget:
    """Wspólny licznik obu kroków, zwiększany przed wysłaniem (AC-23, ADR-003 §4)."""

    limit: int
    cost_limit_usd: float
    used: int = 0
    used_per_tier: dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0})
    cost_used_usd: float = 0.0
    max_cost_seen_per_tier: dict[int, float] = field(default_factory=lambda: {1: 0.0, 2: 0.0})
    cost_unknown: bool = False
    stopped_reason: str = "none"
    stopped_at_photo_id: str = ""

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 25:
            raise ValueError("limit żądań musi być w zakresie 1–25")

    def stop(self, reason: str, photo_id: str = "") -> None:
        if self.stopped_reason == "none":
            self.stopped_reason = reason
            self.stopped_at_photo_id = photo_id

    def reserve(self, tier: int) -> None:
        if self.stopped_reason != "none":
            raise BudgetExhausted(self.stopped_reason)
        if self.used >= self.limit:
            raise BudgetExhausted("budget_exhausted")
        if self.cost_used_usd + self.max_cost_seen_per_tier[tier] > self.cost_limit_usd:
            raise BudgetExhausted("cost_limit")
        self.used += 1
        self.used_per_tier[tier] += 1
        assert self.used <= self.limit, "przekroczony limit żądań"  # TAC-003-02

    def record_cost(self, tier: int, cost: float | None) -> None:
        if cost is None:
            self.cost_unknown = True
            return
        self.cost_used_usd += cost
        self.max_cost_seen_per_tier[tier] = max(self.max_cost_seen_per_tier[tier], cost)


def api_key_present() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def _env_key() -> str | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return key or None


def data_url(image: bytes) -> str:
    mime = "image/png" if image.startswith(b"\x89PNG") else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(image).decode('ascii')}"


def _jev_fit(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    lo = max(JEV_MIN_SIDE / min(w, h), math.sqrt(JEV_MIN_PIXELS / (w * h)))
    hi = min(JEV_MAX_SIDE / max(w, h), math.sqrt(JEV_MAX_PIXELS / (w * h)))
    if lo <= 1.0 <= hi:
        return data
    scale = lo if lo > 1.0 else hi
    rnd = math.ceil if scale > 1.0 else math.floor
    size = (rnd(w * scale), rnd(h * scale))
    buf = io.BytesIO()
    img.convert("RGB").resize(size, Image.Resampling.LANCZOS).save(buf, format="PNG")
    return buf.getvalue()


def prepare_image(model_id: str, crop: bytes) -> tuple[bytes, str]:
    """(wysyłane bajty, wersja transformacji). Skalujemy tylko dla Jev (ADR-006 D-603)."""
    if model_id == JEV_MODEL:
        sent = _jev_fit(crop)
        return sent, "JEV_RESIZE_V1"
    return crop, "ORIGINAL"


def build_tier1_body(model_id: str, image: bytes) -> dict:
    return {
        "model": model_id,
        "state": [STATE_TEXT_V1, {"type": "image_url", "image_url": {"url": data_url(image)}}],
        "questions": {
            "b33_value": {"type": "choice", "instructions": QUESTION_V1, "criteria": CRITERIA_V1}
        },
    }


def build_tier2_body(image: bytes) -> dict:
    """Ten sam obraz i pytanie; bez odpowiedzi kroku 1 i bez kontekstu mapy (D-302)."""
    return {
        "model": TIER2_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": QUESTION_V1 + " Answer with JSON only."},
                    {"type": "image_url", "image_url": {"url": data_url(image)}},
                ],
            }
        ],
        "reasoning": {"effort": "medium"},
        "max_tokens": 4000,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "b33_reading", "strict": True, "schema": SCHEMA_V1},
        },
        "provider": {"require_parameters": True},
    }


@dataclass(frozen=True)
class RawResponse:
    status: int
    headers: dict[str, str]
    text: str
    elapsed_s: float


class OpenRouterClient:
    """Jeden `httpx.Client` z domyślnym transportem (0 ponowień) i terminem 40 s."""

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        api_key: Callable[[], str | None] = _env_key,
        deadline_s: float = DEADLINE_S,
    ) -> None:
        self._http = httpx.Client(timeout=TIMEOUT, transport=transport)
        self._clock = clock
        self._api_key = api_key
        self._deadline = deadline_s

    def close(self) -> None:
        self._http.close()

    def post_json(self, url: str, body: dict) -> RawResponse:
        headers = {"Content-Type": "application/json"}
        key = self._api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        content = json.dumps(body, ensure_ascii=False).encode("utf-8")
        start = self._clock()
        try:
            with self._http.stream("POST", url, content=content, headers=headers) as resp:
                chunks = []
                for chunk in resp.iter_bytes():
                    chunks.append(chunk)
                    if self._clock() - start > self._deadline:
                        raise ModelUnavailable("timeout", f"> {self._deadline:.0f} s")
                elapsed = self._clock() - start
                if elapsed > self._deadline:
                    raise ModelUnavailable("timeout", f"{elapsed:.1f} s")
                kept = {k: v for k, v in resp.headers.items() if k.lower() in ALLOWED_HEADERS}
                text = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
                return RawResponse(resp.status_code, kept, text, round(elapsed, 3))
        except httpx.TimeoutException as exc:
            raise ModelUnavailable("timeout", type(exc).__name__) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailable("network_error", type(exc).__name__) from exc
