"""AC-23, AC-24; ADR-003 §3.6, D-303, TAC-003-02."""

import pytest

from map_qa.ai_client import BudgetExhausted, RequestBudget


def test_counter_increments_before_send_and_limit():
    b = RequestBudget(limit=1, cost_limit_usd=0.5)
    b.reserve(1)
    assert b.used == 1
    with pytest.raises(BudgetExhausted) as exc:
        b.reserve(2)
    assert exc.value.reason == "budget_exhausted" and b.used == 1


def test_25_never_exceeded():
    b = RequestBudget(limit=25, cost_limit_usd=10)
    for _ in range(25):
        b.reserve(1)
    with pytest.raises(BudgetExhausted):
        b.reserve(1)
    assert b.used == 25


def test_limit_above_25_rejected():
    with pytest.raises(ValueError):
        RequestBudget(limit=26, cost_limit_usd=1)


def test_cost_limit_uses_max_seen_per_tier():
    b = RequestBudget(limit=25, cost_limit_usd=0.10)
    b.reserve(2)
    b.record_cost(2, 0.06)
    with pytest.raises(BudgetExhausted) as exc:
        b.reserve(2)  # 0.06 + 0.06 > 0.10
    assert exc.value.reason == "cost_limit"
    b.reserve(1)  # krok 1 nie ma jeszcze obserwacji kosztu
    assert b.used == 2


def test_unknown_cost_noted():
    b = RequestBudget(limit=25, cost_limit_usd=0.5)
    b.reserve(1)
    b.record_cost(1, None)
    assert b.cost_unknown is True
    assert b.cost_used_usd == 0.0


def test_stop_blocks_further_requests():
    b = RequestBudget(limit=25, cost_limit_usd=0.5)
    b.stop("model_unavailable", "p1")
    with pytest.raises(BudgetExhausted) as exc:
        b.reserve(1)
    assert exc.value.reason == "model_unavailable"
    assert b.stopped_at_photo_id == "p1"
