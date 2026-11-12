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
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
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

# Parser przeszedł testy na zapisach T00b (tests/integration/test_ai_client.py, ADR-003 §3.6).
RESPONSE_CONTRACT_VERIFIED = True

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
    last_error: str = ""

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
        self._transport = transport
        self._http = httpx.Client(timeout=TIMEOUT, transport=transport)
        self._clock = clock
        self._api_key = api_key
        self._deadline = deadline_s

    def close(self) -> None:
        self._http.close()

    def post_json(self, url: str, body: dict) -> RawResponse:
        """Jedno żądanie z twardym terminem: wątek roboczy + `result(timeout)` (AC-25).

        Po przekroczeniu terminu klient jest zamykany (przerywa blokujący odczyt) i tworzony
        od nowa; płatna pętla i tak się wtedy zatrzymuje (AC-24)."""
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(self._post, url, body)
        try:
            return future.result(timeout=self._deadline)
        except FutureTimeout as exc:
            old = self._http
            self._http = httpx.Client(timeout=TIMEOUT, transport=self._transport)
            old.close()
            raise ModelUnavailable("timeout", f"> {self._deadline:.0f} s") from exc
        finally:
            pool.shutdown(wait=False)

    def _post(self, url: str, body: dict) -> RawResponse:
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


def redact(text: str, limit: int = 300) -> str:
    """Treść błędu do raportu: bez klucza API i nagłówka Bearer, skrócona (AC-37, TAC-06)."""
    out = str(text or "")
    key = _env_key()
    if key:
        out = out.replace(key, "***")
    out = re.sub(r"(?i)bearer\s+\S+", "Bearer ***", out)
    out = re.sub(r"sk-or-[A-Za-z0-9_-]+", "sk-or-***", out)
    return out if len(out) <= limit else out[:limit] + "…"


# --- Interpretacja odpowiedzi (kontrakt z zapisów T00b, ADR-003 §3.3–3.4) ------------------


def _cost(body: dict) -> float | None:
    """`usage.cost`, a przy kluczu BYOK także `cost_details.upstream_inference_cost`."""
    usage = body.get("usage") or {}
    cost = usage.get("cost")
    upstream = (usage.get("cost_details") or {}).get("upstream_inference_cost")
    if cost is None and upstream is None:
        return None
    total = float(cost or 0.0)
    if usage.get("is_byok") and upstream is not None:
        total += float(upstream)
    return total


def _json(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ModelUnavailable("invalid_response", "odpowiedź nie jest JSON") from exc
    if not isinstance(data, dict):
        raise ModelUnavailable("invalid_response", "odpowiedź nie jest obiektem JSON")
    return data


def _prob(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ModelUnavailable("invalid_response", f"prawdopodobieństwo poza 0–1: {value!r}")
    return float(value)


def interpret_tier1(text: str) -> dict:
    try:
        return _interpret_tier1(text)
    except ModelUnavailable:
        raise
    except (AttributeError, TypeError, KeyError, ValueError) as exc:
        raise ModelUnavailable("invalid_response", type(exc).__name__) from exc


def _interpret_tier1(text: str) -> dict:
    body = _json(text)
    answer = (body.get("answers") or {}).get("b33_value") or {}
    choice = answer.get("choice")
    probs = answer.get("probabilities")
    if choice not in TIER1_OPTIONS or not isinstance(probs, dict) or choice not in probs:
        raise ModelUnavailable("invalid_response", f"choice={choice!r}")
    probabilities = {str(k): _prob(v) for k, v in probs.items()}
    return {
        "answer": choice,
        "probability": probabilities[choice],
        "probabilities": probabilities,
        "confidence": answer.get("confidence"),
        "cost_usd": _cost(body),
        "model": body.get("model"),
    }


def interpret_tier2(text: str) -> dict:
    try:
        return _interpret_tier2(text)
    except ModelUnavailable:
        raise
    except (AttributeError, TypeError, KeyError, ValueError) as exc:
        raise ModelUnavailable("invalid_response", type(exc).__name__) from exc


def _interpret_tier2(text: str) -> dict:
    body = _json(text)
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelUnavailable("invalid_response", "brak choices[0].message.content") from exc
    data = _json(content.strip() if isinstance(content, str) else "")
    if set(data) != {"answer", "value_kmh", "confidence"}:
        raise ModelUnavailable("invalid_response", f"pola: {sorted(data)}")
    answer, value = data["answer"], data["value_kmh"]
    if answer not in TIER2_ANSWERS:
        raise ModelUnavailable("invalid_response", f"answer={answer!r}")
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or not 5 <= value <= 140
    ):
        raise ModelUnavailable("invalid_response", f"value_kmh={value!r}")
    confidence = _prob(data["confidence"])
    if answer == "other_value":
        if value is None or value % 5 != 0:
            raise ModelUnavailable("invalid_response", f"other_value z value_kmh={value!r}")
        answer = str(value)
    return {
        "answer": answer,
        "probability": confidence,
        "probabilities": None,
        "cost_usd": _cost(body),
        "model": body.get("model"),
    }


class SignReader:
    """Czytnik kroków 1 i 2: budżet → żądanie → interpretacja → `SignReading` + wpis cache."""

    def __init__(self, client: OpenRouterClient, tier1_model: str) -> None:
        self.client = client
        self.tier1_model = tier1_model

    def model_for(self, tier: int) -> str:
        return self.tier1_model if tier == 1 else TIER2_MODEL

    def prepare(self, tier: int, crop_sha256: str, crop: bytes) -> tuple[bytes, str, str]:
        """(wysyłane bajty, transformacja, klucz cache) — bez sieci."""
        import hashlib

        from map_qa.cache import cache_key

        sent, transform = prepare_image(self.model_for(tier), crop)
        key = cache_key(
            crop_sha256=crop_sha256,
            sent_sha256=hashlib.sha256(sent).hexdigest(),
            tier=tier,
            model_id=self.model_for(tier),
            image_transform=transform,
        )
        return sent, transform, key

    def read_tier1(self, photo_id: str, crop_sha256: str, crop: bytes, budget: RequestBudget):
        return self._read(1, photo_id, crop_sha256, crop, budget)

    def read_tier2(self, photo_id: str, crop_sha256: str, crop: bytes, budget: RequestBudget):
        return self._read(2, photo_id, crop_sha256, crop, budget)

    def _read(self, tier: int, photo_id: str, crop_sha256: str, crop: bytes, budget):
        import datetime as dt
        import hashlib

        from map_qa.model import SignReading

        sent, transform, key = self.prepare(tier, crop_sha256, crop)
        model = self.model_for(tier)
        body = build_tier1_body(model, sent) if tier == 1 else build_tier2_body(sent)
        url = DECISIONS_URL if tier == 1 else CHAT_URL
        budget.reserve(tier)  # licznik przed wysłaniem (AC-23)
        raw = self.client.post_json(url, body)
        if not 200 <= raw.status < 300:
            raise ModelUnavailable(f"http_{raw.status}", redact(raw.text))
        try:
            interp = interpret_tier1(raw.text) if tier == 1 else interpret_tier2(raw.text)
        except ModelUnavailable:
            try:
                budget.record_cost(tier, _cost(json.loads(raw.text)))
            except ValueError:
                budget.record_cost(tier, None)
            raise
        budget.record_cost(tier, interp["cost_usd"])
        sent_sha = hashlib.sha256(sent).hexdigest()
        reading = SignReading(
            photo_id=photo_id,
            crop_sha256=crop_sha256,
            tier=tier,
            model_id=model,
            answer=interp["answer"],
            probability=interp["probability"],
            probabilities=interp["probabilities"],
            request_outcome="ok",
            cost_usd=interp["cost_usd"],
            cache_key=key,
            sent_sha256=sent_sha,
            elapsed_s=raw.elapsed_s,
        )
        entry = {
            "date": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "endpoint": url,
            "request_summary": {
                "model": model,
                "tier": tier,
                "contract_versions": {
                    "STATE_TEXT": "V1",
                    "QUESTION": "V1",
                    "SCHEMA": "V1",
                    "IMAGE": transform,
                },
                "crop_sha256": crop_sha256,
                "sent_image_sha256": sent_sha,
            },
            "status": raw.status,
            "headers": raw.headers,
            "body": raw.text,
            "elapsed_s": raw.elapsed_s,
            "interpretation": {
                "answer": interp["answer"],
                "probability": interp["probability"],
                "probabilities": interp["probabilities"],
                "cost_usd": interp["cost_usd"],
            },
        }
        return reading, entry
