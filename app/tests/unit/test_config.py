from pathlib import Path

import pytest

from map_qa.config import TIER1_MODELS, ConfigError, RunConfig


def make(**kw):
    base = dict(input_dir=Path("in"), output_dir=Path("out"))
    base.update(kw)
    return RunConfig(**base)


def test_defaults():
    cfg = make()
    assert cfg.max_requests == 25
    assert cfg.threshold == 0.7
    assert cfg.max_cost_usd == 0.50
    assert cfg.tier1_model == "jev"
    assert cfg.tier1_model_id == "typesafe/jev-1.14"
    assert cfg.with_signs is False


@pytest.mark.parametrize("value", [0, 26, -1])
def test_max_requests_out_of_range(value):  # AC-23
    with pytest.raises(ConfigError):
        make(max_requests=value)


@pytest.mark.parametrize("value", [1, 25])
def test_max_requests_bounds_ok(value):
    assert make(max_requests=value).max_requests == value


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_threshold_out_of_range(value):  # AC-22a
    with pytest.raises(ConfigError):
        make(threshold=value)


def test_tier1_models():
    assert TIER1_MODELS == {
        "jev": "typesafe/jev-1.14",
        "luna-decisions": "openai/gpt-6-luna-decisions",
    }
    assert make(tier1_model="luna-decisions").tier1_model_id == "openai/gpt-6-luna-decisions"
    with pytest.raises(ConfigError):
        make(tier1_model="gpt")


def test_sign_sample_capped_by_half_limit():  # ADR-003 §3.1
    assert make().new_crop_budget == 12
    assert make(max_requests=1).new_crop_budget == 0
    assert make(sign_sample=5).new_crop_budget == 5
    assert make(sign_sample=50).new_crop_budget == 12


def test_cache_dir_default_and_env(monkeypatch, tmp_path):  # ADR-005 D-502
    monkeypatch.delenv("MAP_QA_CACHE_DIR", raising=False)
    assert make(input_dir=tmp_path).cache_dir == tmp_path / "data" / "cache" / "ai"
    monkeypatch.setenv("MAP_QA_CACHE_DIR", str(tmp_path / "c"))
    assert make(input_dir=tmp_path).cache_dir == tmp_path / "c"
