"""AC-22, AC-24; ADR-003 §3.3–3.4, §3.6, §5, §8; ADR-006 D-604.

Mocki pytest-httpx odtwarzają wyłącznie odpowiedzi zapisane w T00b (bez wymyślonych kształtów).
"""

import json
from pathlib import Path

import pytest

from map_qa import ai_client as ac

FIX = Path(__file__).resolve().parents[1] / "fixtures"
CROPS = FIX / "map_qa" / "signs" / "crops"
READABLE_ID = "mapillary_1237130608489136"
HARD_ID = "mapillary_137982605041578"


def crop(pid):
    return (CROPS / f"{pid}.jpg").read_bytes()


def capture(name):
    return json.loads((FIX / "openrouter" / f"{name}.json").read_text(encoding="utf-8"))


def replay(httpx_mock, name):
    cap = capture(name)
    httpx_mock.add_response(
        url=cap["endpoint"],
        method="POST",
        status_code=cap["status"],
        headers=cap["headers"],
        content=cap["body"].encode("utf-8"),
    )
    return cap


@pytest.fixture
def reader(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-real")
    client = ac.OpenRouterClient()
    yield lambda model: ac.SignReader(client, model)
    client.close()


def budget():
    return ac.RequestBudget(limit=25, cost_limit_usd=0.5)


@pytest.mark.parametrize(
    "name,model,pid,answer,prob",
    [
        ("tier1-jev-readable", "typesafe/jev-1.14", READABLE_ID, "50", 1.0),
        ("tier1-jev-hard", "typesafe/jev-1.14", HARD_ID, "50", 0.84),
        ("tier1-luna-readable", "openai/gpt-6-luna-decisions", READABLE_ID, "50", 0.97),
        ("tier1-luna-hard", "openai/gpt-6-luna-decisions", HARD_ID, "unreadable", None),
    ],
)
def test_tier1_capture(httpx_mock, reader, name, model, pid, answer, prob):
    replay(httpx_mock, name)
    b = budget()
    reading, entry = reader(model).read_tier1(pid, "sha", crop(pid), b)
    assert reading.tier == 1 and reading.model_id == model
    assert reading.answer == answer
    assert reading.probabilities and abs(sum(reading.probabilities.values()) - 1) < 0.05
    if prob is not None:
        assert reading.probability == pytest.approx(prob)
    assert reading.probability == reading.probabilities[answer]
    assert reading.request_outcome == "ok"
    assert reading.cost_usd and reading.cost_usd > 0  # BYOK: upstream_inference_cost
    assert b.used == 1 and b.cost_used_usd == reading.cost_usd
    assert entry["status"] == 200 and entry["body"] == capture(name)["body"]
    assert "Authorization" not in json.dumps(entry)
    sent = httpx_mock.get_requests()[0]
    assert json.loads(sent.content)["model"] == model


@pytest.mark.parametrize(
    "name,pid,answer,conf",
    [("tier2-luna-readable", READABLE_ID, "50", 0.99), ("tier2-luna-hard", HARD_ID, "30", 0.38)],
)
def test_tier2_capture(httpx_mock, reader, name, pid, answer, conf):
    replay(httpx_mock, name)
    reading, _ = reader("typesafe/jev-1.14").read_tier2(pid, "sha", crop(pid), budget())
    assert (reading.tier, reading.model_id, reading.answer) == (2, "openai/gpt-6-luna", answer)
    assert reading.probability == pytest.approx(conf)
    assert reading.cost_usd and reading.cost_usd > 0


def test_401_raises_without_retry(httpx_mock, reader):
    replay(httpx_mock, "error-401-decisions")
    b = budget()
    with pytest.raises(ac.ModelUnavailable) as exc:
        reader("typesafe/jev-1.14").read_tier1(READABLE_ID, "sha", crop(READABLE_ID), b)
    assert exc.value.reason == "http_401"
    assert len(httpx_mock.get_requests()) == 1  # dokładnie jedno wywołanie
    assert b.used == 1


def test_400_dimension_error_is_model_unavailable(httpx_mock, reader):
    replay(httpx_mock, "jev-small-original")
    with pytest.raises(ac.ModelUnavailable) as exc:
        reader("openai/gpt-6-luna-decisions").read_tier1("p", "sha", crop(READABLE_ID), budget())
    assert exc.value.reason == "http_400"


# --- Interpretacja: przypadki brzegowe wyprowadzone z prawdziwego zapisu -------------------


def _tier1_body(**changes):
    body = json.loads(capture("tier1-luna-readable")["body"])
    body["answers"]["b33_value"].update(changes)
    return json.dumps(body)


def test_tier1_choice_outside_options_is_invalid():
    with pytest.raises(ac.ModelUnavailable) as exc:
        ac.interpret_tier1(_tier1_body(choice="55"))
    assert exc.value.reason == "invalid_response"


def test_tier1_missing_probabilities_is_invalid():
    body = json.loads(capture("tier1-luna-readable")["body"])
    del body["answers"]["b33_value"]["probabilities"]
    with pytest.raises(ac.ModelUnavailable):
        ac.interpret_tier1(json.dumps(body))


def _tier2_body(content):
    body = json.loads(capture("tier2-luna-readable")["body"])
    body["choices"][0]["message"]["content"] = json.dumps(content)
    return json.dumps(body)


def test_tier2_other_value_rules():
    ok = ac.interpret_tier2(
        _tier2_body({"answer": "other_value", "value_kmh": 35, "confidence": 0.8})
    )
    assert ok["answer"] == "35"
    with pytest.raises(ac.ModelUnavailable):
        ac.interpret_tier2(
            _tier2_body({"answer": "other_value", "value_kmh": 33, "confidence": 0.8})
        )


@pytest.mark.parametrize(
    "content",
    [
        {"answer": "55", "value_kmh": 55, "confidence": 0.9},
        {"answer": "50", "value_kmh": 50, "confidence": 1.2},
        {"answer": "50", "value_kmh": 50},
        {"answer": "50", "value_kmh": 50, "confidence": 0.9, "extra": 1},
    ],
)
def test_tier2_schema_violations_invalid(content):
    with pytest.raises(ac.ModelUnavailable):
        ac.interpret_tier2(_tier2_body(content))


def test_tier2_not_json_invalid():
    body = json.loads(capture("tier2-luna-readable")["body"])
    body["choices"][0]["message"]["content"] = "The sign shows 50."
    with pytest.raises(ac.ModelUnavailable):
        ac.interpret_tier2(json.dumps(body))


def test_contract_verified_after_parser_tests():
    assert ac.RESPONSE_CONTRACT_VERIFIED is True


# --- Prawdziwe endpointy (ADR-006 D-604): uv run pytest -m live_api -p no:recording --------


@pytest.mark.live_api
@pytest.mark.parametrize("model", ["typesafe/jev-1.14", "openai/gpt-6-luna-decisions"])
def test_live_tier1(model):
    if not ac.api_key_present():
        pytest.skip("brak OPENROUTER_API_KEY")
    client = ac.OpenRouterClient()
    try:
        reading, _ = ac.SignReader(client, model).read_tier1(
            READABLE_ID, "sha", crop(READABLE_ID), budget()
        )
    finally:
        client.close()
    assert reading.answer in ac.TIER1_OPTIONS and 0 <= reading.probability <= 1


@pytest.mark.live_api
def test_live_tier2():
    if not ac.api_key_present():
        pytest.skip("brak OPENROUTER_API_KEY")
    client = ac.OpenRouterClient()
    try:
        reading, _ = ac.SignReader(client, "typesafe/jev-1.14").read_tier2(
            READABLE_ID, "sha", crop(READABLE_ID), budget()
        )
    finally:
        client.close()
    assert reading.answer is not None and 0 <= reading.probability <= 1
