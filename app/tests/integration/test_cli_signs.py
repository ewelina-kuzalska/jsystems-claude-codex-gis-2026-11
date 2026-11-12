"""PRD 4.2–4.3, §9.1; AC-20, AC-22e, AC-23, AC-26, AC-37; ADR-003 §3.6; TAC-06.

Odpowiedzi HTTP pochodzą wyłącznie z zapisów T00b (pytest-httpx).
"""

import json
import re
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from map_qa import ai_client
from map_qa.cli import app

FIX = Path(__file__).resolve().parents[1] / "fixtures"
FAKE_KEY = "sk-or-v1-FAKE-test-key-do-not-use-7f3a9c"


def capture(name):
    return json.loads((FIX / "openrouter" / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def env(fixtures_dir, tmp_path, monkeypatch):
    snap = tmp_path / "in"
    shutil.copytree(fixtures_dir / "map_qa", snap)
    monkeypatch.setenv("MAP_QA_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    return {"snap": snap, "out": tmp_path / "out", "tmp": tmp_path}


def invoke(env, *extra, input=None):
    args = ["run", "--input", str(env["snap"]), "--output", str(env["out"]), "--with-signs", *extra]
    return CliRunner().invoke(app, args, input=input)


def summary(env):
    (run_dir,) = sorted(p for p in env["out"].iterdir() if p.is_dir())[-1:]
    return json.loads((run_dir / "summary.json").read_text(encoding="utf-8")), run_dir


def replay_all(httpx_mock, tier1="tier1-jev-readable", tier2="tier2-luna-readable"):
    for name in (tier1, tier2):
        cap = capture(name)
        httpx_mock.add_response(
            url=cap["endpoint"],
            status_code=cap["status"],
            content=cap["body"].encode("utf-8"),
            is_reusable=True,
            is_optional=True,
        )


def test_answer_no_is_not_run(env, httpx_mock):  # AC-20
    res = invoke(env, input="nie\n")
    assert res.exit_code == 0, res.output
    assert "Plan C4" in res.output and "tak/nie" in res.output
    s, _ = summary(env)
    assert s["c4"]["status"] == "not_run" and "potwierdzenia" in s["c4"]["reason"]
    assert httpx_mock.get_requests() == []


def test_empty_key_no_requests(env, httpx_mock, monkeypatch):  # AC-37
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    res = invoke(env, "--yes")
    assert res.exit_code == 0, res.output
    s, _ = summary(env)
    assert "Brak klucza OPENROUTER_API_KEY" in s["c4"]["reason"]
    assert s["counts"]["C1"] >= 0 and httpx_mock.get_requests() == []


def test_contract_unverified_no_requests(env, httpx_mock, monkeypatch):
    monkeypatch.setattr(ai_client, "RESPONSE_CONTRACT_VERIFIED", False)
    res = invoke(env, "--yes")
    assert res.exit_code == 0
    s, _ = summary(env)
    assert s["c4"]["reason"].startswith("contract_unverified")
    assert httpx_mock.get_requests() == []


def test_full_flow_then_cache_rerun(env, httpx_mock):  # AC-22e, AC-23, AC-26
    replay_all(httpx_mock)
    res = invoke(env, "--yes")
    assert res.exit_code == 0, res.output
    s, run_dir = summary(env)
    c4 = s["c4"]
    assert c4["status"] == "run" and c4["tier1_model"] == "typesafe/jev-1.14"
    assert sum(c4["resolved"].values()) == c4["sample_total"] == 8
    assert c4["requests"]["total"] <= 25
    assert len(httpx_mock.get_requests()) == c4["requests"]["total"] > 0
    assert "C4: żądania krok 1" in res.output
    # zapisany Jev odpowiada „50” z p=1,0, więc każdy wycinek kończy w kroku 1
    assert c4["resolved"]["decision_model"] == 8
    assert s["counts"]["C4"] >= 1  # np. znak z OSM 140 / 40 → sign_mismatch
    assert s["not_comparable"].get("outside_snapshot", 0) >= 1
    html = (run_dir / "report.html").read_text(encoding="utf-8")
    assert "Zgodność z roboczą referencją" in html and "_crop.jpg" in html
    first_requests = len(httpx_mock.get_requests())

    import time

    time.sleep(1.1)
    res2 = invoke(env, "--yes")
    assert res2.exit_code == 0, res2.output
    s2, _ = summary(env)
    assert len(httpx_mock.get_requests()) == first_requests  # zero nowych żądań
    assert s2["c4"]["requests"]["total"] == 0
    assert s2["c4"]["cached"]["tier1"] == 8
    assert s2["counts"] == s["counts"]


def test_401_stops_loop_and_secret_never_written(env, httpx_mock):  # AC-24, TAC-06
    cap = capture("error-401-decisions")
    httpx_mock.add_response(
        url=cap["endpoint"], status_code=401, content=cap["body"].encode("utf-8")
    )
    res = invoke(env, "--yes")
    assert res.exit_code == 0, res.output
    s, run_dir = summary(env)
    assert len(httpx_mock.get_requests()) == 1
    assert s["c4"]["stop_reason"] == "model_unavailable"
    assert s["c4"]["resolved"]["human_pending"] == 8
    assert s["counts"]["C4-manual"] == 8
    key_part = re.escape(FAKE_KEY[10:30])
    assert not re.search(key_part, res.output)
    for path in run_dir.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".html", ".json", ".csv", ".geojson"):
            assert FAKE_KEY[10:30] not in path.read_text(encoding="utf-8-sig"), path
    assert not (env["tmp"] / "cache").exists() or not list((env["tmp"] / "cache").iterdir())


def test_luna_decisions_tier1_option(env, httpx_mock):  # ADR-006 D-601
    replay_all(httpx_mock, tier1="tier1-luna-readable")
    res = invoke(env, "--yes", "--tier1-model", "luna-decisions", "--max-requests", "4")
    assert res.exit_code == 0, res.output
    s, _ = summary(env)
    assert s["c4"]["tier1_model"] == "openai/gpt-6-luna-decisions"
    assert s["c4"]["processed"] == 2 and s["c4"]["resolved"]["not_run"] == 6  # floor(4/2)
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["model"] == "openai/gpt-6-luna-decisions"
