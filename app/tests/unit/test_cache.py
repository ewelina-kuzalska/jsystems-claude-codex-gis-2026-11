"""AC-26; ADR-003 §3.7, D-305; ADR-006 D-601/D-603."""

import json

from map_qa.cache import AiCache, cache_key


def key(**kw):
    base = dict(
        crop_sha256="a" * 64,
        sent_sha256="a" * 64,
        tier=1,
        model_id="typesafe/jev-1.14",
        image_transform="JEV_RESIZE_V1",
    )
    base.update(kw)
    return cache_key(**base)


def test_key_changes_with_model_tier_image_and_transform():
    k = key()
    assert k == key()
    assert k != key(model_id="openai/gpt-6-luna-decisions")
    assert k != key(tier=2)
    assert k != key(crop_sha256="b" * 64)
    assert k != key(sent_sha256="c" * 64)
    assert k != key(image_transform="ORIGINAL")


def test_put_get_roundtrip(tmp_path):
    cache = AiCache(tmp_path / "cache")
    assert cache.get("k1") is None
    entry = {"status": 200, "body": "{}", "interpretation": {"answer": "50"}}
    cache.put("k1", entry)
    got = cache.get("k1")
    assert got["interpretation"] == {"answer": "50"}
    assert "cached_at" in got
    files = list((tmp_path / "cache").glob("*.json"))
    assert [f.stem for f in files] == ["k1"]


def test_put_rejects_non_2xx(tmp_path):
    cache = AiCache(tmp_path / "cache")
    cache.put("k", {"status": 401, "body": "x", "interpretation": None})
    assert cache.get("k") is None
    assert not (tmp_path / "cache").exists() or not list((tmp_path / "cache").iterdir())


def test_entry_has_no_secret_fields(tmp_path):
    cache = AiCache(tmp_path / "cache")
    cache.put("k", {"status": 200, "body": "{}", "interpretation": {}, "request_summary": {}})
    text = (tmp_path / "cache" / "k.json").read_text(encoding="utf-8")
    assert "Authorization" not in text and json.loads(text)["status"] == 200


def test_corrupt_entry_is_miss(tmp_path):
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "bad.json").write_text("{nie json", encoding="utf-8")
    assert AiCache(tmp_path / "c").get("bad") is None
