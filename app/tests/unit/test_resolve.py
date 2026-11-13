"""AC-22a–e, AC-23, AC-24, AC-26; ADR-003 §3.1, §3.5–3.7, §3.10, TAC-003-04.

Fałszywy czytnik zwraca gotowe obiekty `SignReading` przez interfejs z T21/T22.
"""

import builtins
from pathlib import Path

import pytest

from map_qa.ai_client import ModelUnavailable, RequestBudget
from map_qa.cache import AiCache
from map_qa.model import SignReading
from map_qa.signs.resolve import CropItem, plan_sign_run, resolve_signs, select_sample


class FakeReader:
    def __init__(self, t1=None, t2=None, fail=None):
        self.t1 = t1 or {}
        self.t2 = t2 or {}
        self.fail = fail or {}  # (tier, photo_id) -> reason
        self.calls = []

    def model_for(self, tier):
        return "fake/t1" if tier == 1 else "fake/t2"

    def prepare(self, tier, crop_sha256, crop):
        return crop, "ORIGINAL", f"{tier}-{crop_sha256}"

    def _read(self, tier, pid, sha, crop, budget):
        budget.reserve(tier)
        self.calls.append((tier, pid))
        if (tier, pid) in self.fail:
            raise ModelUnavailable(self.fail[(tier, pid)])
        answer, p = (self.t1 if tier == 1 else self.t2).get(pid, ("unreadable", 0.9))
        reading = SignReading(
            pid,
            sha,
            tier,
            self.model_for(tier),
            answer,
            p,
            {answer: p} if tier == 1 else None,
            "ok",
            0.0001,
            f"{tier}-{sha}",
        )
        entry = {
            "status": 200,
            "body": "{}",
            "interpretation": {
                "answer": answer,
                "probability": p,
                "probabilities": reading.probabilities,
                "cost_usd": 0.0001,
            },
        }
        return reading, entry

    def read_tier1(self, pid, sha, crop, budget):
        return self._read(1, pid, sha, crop, budget)

    def read_tier2(self, pid, sha, crop, budget):
        return self._read(2, pid, sha, crop, budget)


def items(*ids):
    return [CropItem(pid, f"sha-{pid}", b"jpeg", None) for pid in ids]


def run(reader, crops, tmp_path, limit=25, threshold=0.7):
    budget = RequestBudget(limit=limit, cost_limit_usd=0.5)
    res = resolve_signs(crops, budget, AiCache(tmp_path / "cache"), reader, threshold)
    return {r.photo_id: r for r in res}, budget


def test_tier1_threshold_boundary(tmp_path):
    r = FakeReader(t1={"a": ("50", 0.70), "b": ("50", 0.69)}, t2={"b": ("50", 0.9)})
    res, _ = run(r, items("a", "b"), tmp_path)
    assert (res["a"].resolved_by, res["a"].final_value) == ("decision_model", "50")
    assert res["a"].tier2 is None  # krok 2 nie jest wołany dla pewnej odpowiedzi
    assert res["b"].resolved_by == "general_llm" and res["b"].tier1.answer == "50"


@pytest.mark.parametrize(
    "t1,expected",
    [
        (("none", 0.9), "decision_model"),
        (("unreadable", 0.99), "general_llm"),
        (("other", 0.99), "general_llm"),
    ],
)
def test_tier1_answer_kinds(tmp_path, t1, expected):
    res, _ = run(FakeReader(t1={"a": t1}, t2={"a": ("35", 0.95)}), items("a"), tmp_path)
    assert res["a"].resolved_by == expected


def test_tier2_threshold_and_reasons(tmp_path):
    r = FakeReader(
        t1={"a": ("50", 0.1), "b": ("50", 0.1), "c": ("50", 0.1)},
        t2={"a": ("50", 0.70), "b": ("50", 0.69), "c": ("unreadable", 0.99)},
    )
    res, _ = run(r, items("a", "b", "c"), tmp_path)
    assert res["a"].resolved_by == "general_llm"
    assert (res["b"].resolved_by, res["b"].manual_reason) == ("human_pending", "below_threshold")
    assert (res["c"].resolved_by, res["c"].manual_reason) == ("human_pending", "unreadable")
    assert res["b"].tier1.answer == "50" and res["b"].tier2.probability == 0.69  # podpowiedzi


def test_model_unavailable_stops_loop(tmp_path):  # AC-24
    r = FakeReader(t1={"a": ("50", 0.9)}, fail={(1, "b"): "http_402"})
    res, budget = run(r, items("a", "b", "c"), tmp_path)
    assert res["a"].resolved_by == "decision_model"
    for pid in ("b", "c"):
        assert (res[pid].resolved_by, res[pid].manual_reason) == (
            "human_pending",
            "model_unavailable",
        )
    assert r.calls == [(1, "a"), (1, "b")]  # bez ponowień i bez dalszych żądań
    assert budget.stopped_reason == "model_unavailable" and budget.stopped_at_photo_id == "b"


def test_tier2_error_stops_tier1_too(tmp_path):
    r = FakeReader(t1={"a": ("50", 0.1)}, fail={(2, "a"): "timeout"})
    res, _ = run(r, items("a", "b"), tmp_path)
    assert res["a"].manual_reason == "model_unavailable" and res["a"].tier1.answer == "50"
    assert res["b"].manual_reason == "model_unavailable"
    assert r.calls == [(1, "a"), (2, "a")]


def test_limit_1_one_request_rest_budget_exhausted(tmp_path):
    r = FakeReader(t1={"a": ("50", 0.9), "b": ("50", 0.9)})
    res, budget = run(r, items("a", "b", "c"), tmp_path, limit=1)
    assert budget.used == 1 and len(r.calls) == 1
    assert res["a"].resolved_by == "decision_model"
    assert [res[p].manual_reason for p in ("b", "c")] == ["budget_exhausted"] * 2


def test_all_escalate_stays_within_limit(tmp_path):
    ids = [f"p{i:02d}" for i in range(13)]
    r = FakeReader(t1={p: ("unreadable", 0.9) for p in ids}, t2={p: ("50", 0.9) for p in ids})
    sample, not_run = select_sample(items(*ids), AiCache(tmp_path / "c"), r, new_crop_budget=12)
    assert len(sample) == 12 and [x.photo_id for x in not_run] == ["p12"]
    res, budget = run(r, sample, tmp_path)
    assert budget.used == 24 <= 25
    assert all(x.resolved_by == "general_llm" for x in res.values())


def test_invalid_crop_not_sent(tmp_path):
    crops = [CropItem("x", "sha", None, "metadata_present")]
    r = FakeReader()
    res, budget = run(r, crops, tmp_path)
    assert (res["x"].resolved_by, res["x"].manual_reason, res["x"].detail) == (
        "human_pending",
        "model_unavailable",
        "metadata_present",
    )
    assert r.calls == [] and budget.used == 0


def test_cache_second_run_zero_requests(tmp_path):  # AC-26
    r = FakeReader(t1={"a": ("50", 0.1)}, t2={"a": ("50", 0.9)})
    first, _ = run(r, items("a"), tmp_path)
    r2 = FakeReader()
    second, budget = run(r2, items("a"), tmp_path)
    assert r2.calls == [] and budget.used == 0
    assert second["a"].resolved_by == first["a"].resolved_by == "general_llm"
    assert second["a"].tier1.request_outcome == "cached"


def test_errors_not_cached(tmp_path):
    run(FakeReader(fail={(1, "a"): "http_401"}), items("a"), tmp_path)
    assert not (tmp_path / "cache").exists() or not list((tmp_path / "cache").iterdir())


def test_states_sum_to_sample(tmp_path):  # AC-22e
    r = FakeReader(
        t1={"a": ("50", 0.9), "b": ("50", 0.1)}, t2={"b": ("50", 0.1)}, fail={(1, "c"): "http_500"}
    )
    res, _ = run(r, items("a", "b", "c", "d"), tmp_path)
    states = [x.resolved_by for x in res.values()]
    assert len(states) == 4
    assert set(states) <= {"decision_model", "general_llm", "human_pending", "not_run"}
    assert not any(x.resolved_by != "human_pending" and x.manual_reason for x in res.values())


def test_plan_counts(tmp_path):
    r = FakeReader(t1={"a": ("50", 0.1)}, t2={"a": ("50", 0.9)})
    run(r, items("a"), tmp_path)  # a: krok 1 i krok 2 w cache
    cache = AiCache(tmp_path / "cache")
    sample, not_run = select_sample(items("a", "b", "c"), cache, r, new_crop_budget=1)
    assert [x.photo_id for x in sample] == ["a", "b"] and [x.photo_id for x in not_run] == ["c"]
    plan = plan_sign_run(sample, cache, r, threshold=0.7, limit=25, cost_limit=0.5)
    assert (plan.cached_tier1, plan.new_tier1, plan.worst_tier2) == (1, 1, 1)


def test_resolve_never_opens_labels(tmp_path, monkeypatch):  # TAC-003-04
    opened = []
    real_open = builtins.open
    real_path_open = Path.open

    def spy(file, *a, **k):
        opened.append(str(file))
        return real_open(file, *a, **k)

    def spy_path(self, *a, **k):
        opened.append(str(self))
        return real_path_open(self, *a, **k)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(Path, "open", spy_path)
    run(FakeReader(t1={"a": ("50", 0.9)}), items("a"), tmp_path)
    assert not any("labels.csv" in f for f in opened)


def test_prepare_failure_fails_closed(tmp_path):  # przegląd T27: brak wyjątku na całym przebiegu
    class Broken(FakeReader):
        def prepare(self, tier, crop_sha256, crop):
            raise OSError("cannot identify image file")

    crops = items("a")
    sample, _ = select_sample(crops, AiCache(tmp_path / "c"), Broken(), new_crop_budget=12)
    res, budget = run(Broken(), sample, tmp_path)
    assert (res["a"].resolved_by, res["a"].manual_reason, res["a"].detail) == (
        "human_pending",
        "model_unavailable",
        "crop_invalid",
    )
    assert budget.used == 0


def test_worst_case_fits_limit_with_cached_tier1_pending(tmp_path):  # ADR-003 §3.1, przegląd T27
    first = [f"a{i:02d}" for i in range(12)]
    cache = AiCache(tmp_path / "cache")
    for p in first:  # krok 1 w cache (do eskalacji), krok 2 jeszcze nie
        interp = {"answer": "unreadable", "probability": 0.9, "probabilities": None}
        cache.put(f"1-sha-{p}", {"status": 200, "body": "{}", "interpretation": interp})
    new = [f"b{i:02d}" for i in range(13)]
    sample, _ = select_sample(
        items(*first, *new), cache, FakeReader(), new_crop_budget=12, threshold=0.7, limit=25
    )
    plan = plan_sign_run(sample, cache, FakeReader(), threshold=0.7, limit=25, cost_limit=0.5)
    assert plan.new_tier1 + plan.worst_tier2 <= 25
    assert plan.new_tier1 == 6
