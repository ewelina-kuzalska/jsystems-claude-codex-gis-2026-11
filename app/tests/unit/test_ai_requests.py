"""AC-21, AC-22, AC-24, AC-25, AC-37; ADR-003 §3.3–3.4, §3.6, D-05, TAC-003-01; ADR-006 D-603.

Ciała żądań porównujemy z zaakceptowanymi żądaniami zapisanymi w T00b. Bez sieci.
"""

import hashlib
import io
import json
import re
from pathlib import Path

import httpx
import pytest
from PIL import Image

import map_qa
from map_qa import ai_client as ac

FIX = Path(__file__).resolve().parents[1] / "fixtures"
CROPS = FIX / "map_qa" / "signs" / "crops"
READABLE = (CROPS / "mapillary_1237130608489136.jpg").read_bytes()
HARD = (CROPS / "mapillary_137982605041578.jpg").read_bytes()


def capture(name):
    return json.loads((FIX / "openrouter" / f"{name}.json").read_text(encoding="utf-8"))


def redact(body, image):
    text = json.dumps(body, ensure_ascii=False)
    url = ac.data_url(image)
    return json.loads(text.replace(url, f"<image sha256={hashlib.sha256(image).hexdigest()}>"))


def walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_keys(v)


@pytest.mark.parametrize(
    "name,model,image",
    [
        ("tier1-luna-readable", "openai/gpt-6-luna-decisions", READABLE),
        ("tier1-luna-hard", "openai/gpt-6-luna-decisions", HARD),
    ],
)
def test_tier1_body_matches_accepted_capture(name, model, image):
    body = ac.build_tier1_body(model, image)
    assert redact(body, image) == capture(name)["request_summary"]


@pytest.mark.parametrize("name,image", [("tier1-jev-readable", READABLE), ("tier1-jev-hard", HARD)])
def test_jev_body_and_resized_image_match_capture(name, image):
    sent, transform = ac.prepare_image("typesafe/jev-1.14", image)
    cap = capture(name)
    assert transform == "JEV_RESIZE_V1"
    assert hashlib.sha256(sent).hexdigest() == cap["sent_image_sha256"]
    assert redact(ac.build_tier1_body("typesafe/jev-1.14", sent), sent) == cap["request_summary"]


@pytest.mark.parametrize(
    "name,image", [("tier2-luna-readable", READABLE), ("tier2-luna-hard", HARD)]
)
def test_tier2_body_matches_accepted_capture(name, image):
    body = ac.build_tier2_body(image)
    assert redact(body, image) == capture(name)["request_summary"]
    assert body["reasoning"] == {"effort": "medium"}
    assert body["response_format"]["json_schema"]["strict"] is True


def test_no_forbidden_fields_anywhere():  # AC-21
    forbidden = {
        "photo_id",
        "longitude",
        "latitude",
        "osm_way_id",
        "mapillary_value",
        "sign_value",
        "label",
        "tier1",
        "session_id",
        "user",
        "trace",
    }
    for body in (ac.build_tier1_body("typesafe/jev-1.14", READABLE), ac.build_tier2_body(READABLE)):
        assert not forbidden & set(walk_keys(body))
        text = json.dumps(body)
        assert "mapillary_" not in text and "19." not in text.split("base64,")[0]


def test_original_bytes_for_luna_models():  # D-603
    for model in ("openai/gpt-6-luna-decisions", "openai/gpt-6-luna"):
        sent, transform = ac.prepare_image(model, READABLE)
        assert sent == READABLE and transform == "ORIGINAL"


@pytest.mark.parametrize("size", [(49, 56), (175, 172), (285, 280), (2048, 1152), (300, 300)])
def test_jev_fit_limits(size):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 0, 0)).save(buf, format="JPEG")
    out, _ = ac.prepare_image("typesafe/jev-1.14", buf.getvalue())
    w, h = Image.open(io.BytesIO(out)).size
    assert 280 <= w <= 1568 and 280 <= h <= 1568 and 78_400 <= w * h <= 2_458_624
    if size in ((285, 280), (300, 300)):
        assert out == buf.getvalue()  # już w limitach: bez zmian


# --- Transport: termin 40 s, brak ponowień, nagłówki ------------------------------------


class Clock:
    def __init__(self, step):
        self.t = 0.0
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


def client_with(handler, step=0.0, key="sk-or-test-123"):
    return ac.OpenRouterClient(
        transport=httpx.MockTransport(handler), clock=Clock(step), api_key=lambda: key
    )


def test_deadline_exceeded_is_timeout():  # AC-25
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, text="{}")

    with pytest.raises(ac.ModelUnavailable) as exc:
        client_with(handler, step=20.6).post_json(ac.DECISIONS_URL, {"a": 1})
    assert exc.value.reason == "timeout" and len(calls) == 1


def test_response_within_39s_accepted():
    raw = client_with(lambda r: httpx.Response(200, text="{}"), step=19.5).post_json(
        ac.DECISIONS_URL, {}
    )
    assert raw.status == 200 and raw.text == "{}"


def test_transport_exception_no_retry():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("boom")

    with pytest.raises(ac.ModelUnavailable) as exc:
        client_with(handler).post_json(ac.DECISIONS_URL, {})
    assert exc.value.reason == "network_error" and len(calls) == 1


def test_read_timeout_maps_to_timeout():
    def handler(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(ac.ModelUnavailable) as exc:
        client_with(handler).post_json(ac.DECISIONS_URL, {})
    assert exc.value.reason == "timeout"


def test_auth_header_built_from_env_only_at_send(monkeypatch):
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return httpx.Response(200, text="{}")

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-from-env")
    ac.OpenRouterClient(transport=httpx.MockTransport(handler)).post_json(ac.CHAT_URL, {})
    assert seen["authorization"] == "Bearer sk-or-from-env"
    assert "x-session-id" not in seen


def test_api_key_missing_or_empty(monkeypatch):  # AC-37
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert ac.api_key_present() is False
    monkeypatch.setenv("OPENROUTER_API_KEY", "  ")
    assert ac.api_key_present() is False
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    assert ac.api_key_present() is True


def test_no_retry_transport_or_sdk_in_code():  # TAC-003-01
    for path in Path(map_qa.__file__).parent.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"retries\s*=", text), path
        assert not re.search(
            r"^\s*(import|from)\s+(openrouter|openai|tenacity|backoff)\b", text, re.M
        ), path


def test_contract_flag_exists():
    assert isinstance(ac.RESPONSE_CONTRACT_VERIFIED, bool)
