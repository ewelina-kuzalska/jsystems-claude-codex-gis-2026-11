"""ADR-003 §8: brak ponowień i brak cache błędów na prawdziwym kliencie z zapisem 401."""

import json
from pathlib import Path

from map_qa import ai_client as ac
from map_qa.cache import AiCache
from map_qa.signs.resolve import CropItem, resolve_signs

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def test_401_stops_loop_called_once_and_not_cached(httpx_mock, monkeypatch, tmp_path):
    cap = json.loads((FIX / "openrouter" / "error-401-decisions.json").read_text("utf-8"))
    httpx_mock.add_response(url=cap["endpoint"], status_code=401, content=cap["body"].encode())
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-real")
    crops = FIX / "map_qa" / "signs" / "crops"
    items = [
        CropItem(p.stem, f"sha-{p.stem}", p.read_bytes(), None) for p in sorted(crops.glob("*.jpg"))
    ][:3]
    client = ac.OpenRouterClient()
    budget = ac.RequestBudget(limit=25, cost_limit_usd=0.5)
    try:
        res = resolve_signs(
            items, budget, AiCache(tmp_path / "c"), ac.SignReader(client, ac.JEV_MODEL), 0.7
        )
    finally:
        client.close()
    assert len(httpx_mock.get_requests()) == 1
    assert [r.manual_reason for r in res] == ["model_unavailable"] * 3
    assert budget.used == 1 and budget.stopped_reason == "model_unavailable"
    assert budget.last_error.startswith("http_401")
    assert not (tmp_path / "c").exists()
