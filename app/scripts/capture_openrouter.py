"""Zapis prawdziwych żądań i odpowiedzi OpenRouter dla C4 (plan T00b, ADR-006 D-604).

Uruchomienie (z katalogu app/):
    PYTHONUTF8=1 uv run python scripts/capture_openrouter.py

Skrypt wysyła kilka tanich żądań (zatwierdzone w ADR-006 D-604) i zapisuje każde jako
`CapturedFixture` (ADR-003 §4) w `tests/fixtures/openrouter/`. W pliku nie ma nagłówka
`Authorization` ani obrazu (zamiast obrazu jest jego SHA-256). Kontrakt żądania odtwarza
ADR-003 §3.3–3.4; testy `ai_client` porównują z tymi zapisami ciała budowane przez aplikację.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

APP_DIR = Path(__file__).resolve().parents[1]
SIGNS = APP_DIR.parent / "course-materials" / "exercise-data" / "map-qa" / "signs"
OUT = APP_DIR / "tests" / "fixtures" / "openrouter"

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
JEV = "typesafe/jev-1.14"
LUNA_DECISIONS = "openai/gpt-6-luna-decisions"
LUNA_LLM = "openai/gpt-6-luna"

STATE_TEXT_V1 = "An image crop from a street-level photograph."
QUESTION_V1 = (
    "Is there a round Polish B-33 maximum speed limit sign (red ring, black number) in this "
    "image? If yes, which number does it show?"
)
SPEED_OPTIONS = [str(v) for v in range(10, 150, 10)]
CRITERIA_V1 = {
    **{v: "a B-33 sign showing this number" for v in SPEED_OPTIONS},
    "other": "a B-33 sign whose number is not in this list",
    "none": "no B-33 sign; includes zone signs and end-of-limit signs",
    "unreadable": "a sign is present but its number cannot be read",
}
SCHEMA_V1 = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "value_kmh", "confidence"],
    "properties": {
        "answer": {"type": "string", "enum": [*SPEED_OPTIONS, "other_value", "none", "unreadable"]},
        "value_kmh": {"type": ["integer", "null"], "minimum": 5, "maximum": 140},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}
ALLOWED_HEADERS = ("content-type", "date", "x-request-id", "x-generation-id")
TIMEOUT = httpx.Timeout(connect=5.0, read=40.0, write=5.0, pool=5.0)

# Limity obrazu Jev (docs.typesafe.ai/images „Limits”, 2026-11-12; OpenRouter podaje 256 px, ale
# T00b potwierdził odrzucenie 283x278: obowiązuje 280 px z dokumentacji TypeSafe)
JEV_MIN_SIDE, JEV_MAX_SIDE = 280, 1568
JEV_MIN_PIXELS, JEV_MAX_PIXELS = 78_400, 2_458_624


def jev_fit(data: bytes) -> bytes:
    """Deterministyczne dopasowanie wycinka do limitów Jev (JEV_RESIZE_V1)."""
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


def data_url(data: bytes) -> str:
    mime = "image/png" if data.startswith(b"\x89PNG") else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def decisions_body(model: str, image: bytes) -> dict:
    return {
        "model": model,
        "state": [STATE_TEXT_V1, {"type": "image_url", "image_url": {"url": data_url(image)}}],
        "questions": {
            "b33_value": {"type": "choice", "instructions": QUESTION_V1, "criteria": CRITERIA_V1}
        },
    }


def chat_body(model: str, image: bytes) -> dict:
    return {
        "model": model,
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


def redact_image(body: dict, image: bytes) -> dict:
    """Streszczenie żądania: obraz zastąpiony SHA-256 wysłanych bajtów."""
    text = json.dumps(body, ensure_ascii=False)
    text = text.replace(data_url(image), f"<image sha256={hashlib.sha256(image).hexdigest()}>")
    return json.loads(text)


def capture(name: str, url: str, body: dict, image: bytes, *, with_key: bool, note: str) -> None:
    headers = {"Content-Type": "application/json"}
    if with_key:
        headers["Authorization"] = f"Bearer {os.environ['OPENROUTER_API_KEY']}"
    started = time.monotonic()
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(url, json=body, headers=headers)
    elapsed = round(time.monotonic() - started, 3)
    fixture = {
        "captured_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "endpoint": url,
        "model": body["model"],
        "contract_versions": {
            "STATE_TEXT": "V1",
            "QUESTION": "V1",
            "SCHEMA": "V1",
            "IMAGE": "JEV_RESIZE_V1" if body["model"] == JEV else "ORIGINAL",
        },
        "httpx_version": httpx.__version__,
        "note": note,
        "sent_image_sha256": hashlib.sha256(image).hexdigest(),
        "sent_image_size": list(Image.open(io.BytesIO(image)).size),
        "elapsed_s": elapsed,
        "request_summary": redact_image(body, image),
        "status": resp.status_code,
        "headers": {k: v for k, v in resp.headers.items() if k.lower() in ALLOWED_HEADERS},
        "body": resp.text,
    }
    text = json.dumps(fixture, ensure_ascii=False, indent=2) + "\n"
    assert "Authorization" not in text and "Bearer" not in text
    (OUT / f"{name}.json").write_text(text, encoding="utf-8", newline="\n")
    print(f"{name}: HTTP {resp.status_code} in {elapsed}s -> {resp.text[:300]}")


def crop(photo_id: str) -> bytes:
    return (SIGNS / "crops" / f"{photo_id}.jpg").read_bytes()


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Brak OPENROUTER_API_KEY", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    readable = crop("mapillary_1237130608489136")  # etykieta 50, 175x172 px
    hard = crop("mapillary_137982605041578")  # etykieta unreadable (rozmycie)
    only = sys.argv[1:]

    jobs = [
        (
            "jev-small-original",
            DECISIONS_URL,
            decisions_body(JEV, readable),
            readable,
            True,
            "Jev z oryginalnym wycinkiem < 256 px (sprawdzenie limitu ADR-006 D-603)",
        ),
        (
            "tier1-jev-readable",
            DECISIONS_URL,
            decisions_body(JEV, jev_fit(readable)),
            jev_fit(readable),
            True,
            "Jev, wycinek czytelny (etykieta 50), JEV_RESIZE_V1",
        ),
        (
            "tier1-jev-hard",
            DECISIONS_URL,
            decisions_body(JEV, jev_fit(hard)),
            jev_fit(hard),
            True,
            "Jev, wycinek trudny (etykieta unreadable), JEV_RESIZE_V1",
        ),
        (
            "tier1-luna-readable",
            DECISIONS_URL,
            decisions_body(LUNA_DECISIONS, readable),
            readable,
            True,
            "Luna Decisions, wycinek czytelny (etykieta 50), oryginalne bajty",
        ),
        (
            "tier1-luna-hard",
            DECISIONS_URL,
            decisions_body(LUNA_DECISIONS, hard),
            hard,
            True,
            "Luna Decisions, wycinek trudny (etykieta unreadable)",
        ),
        (
            "tier2-luna-readable",
            CHAT_URL,
            chat_body(LUNA_LLM, readable),
            readable,
            True,
            "Luna LLM, wycinek czytelny (etykieta 50)",
        ),
        (
            "tier2-luna-hard",
            CHAT_URL,
            chat_body(LUNA_LLM, hard),
            hard,
            True,
            "Luna LLM, wycinek trudny (etykieta unreadable)",
        ),
        (
            "error-401-decisions",
            DECISIONS_URL,
            decisions_body(JEV, jev_fit(readable)),
            jev_fit(readable),
            False,
            "Decisions bez klucza API w nagłówkach (bez kosztu)",
        ),
    ]
    for name, url, body, image, with_key, note in jobs:
        if only and name not in only:
            continue
        capture(name, url, body, image, with_key=with_key, note=note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
