"""Cache odpowiedzi AI po hashu obrazu i wersji kontraktu (ADR-003 §3.7, D-305).

Zapisujemy wyłącznie odpowiedzi 2xx po poprawnej interpretacji; błędy nie trafiają do cache.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path

CONTRACT_VERSION = "C4_V1"
QUESTION_VERSIONS = {"STATE_TEXT": "V1", "QUESTION": "V1", "SCHEMA": "V1"}


def cache_key(
    *, crop_sha256: str, sent_sha256: str, tier: int, model_id: str, image_transform: str
) -> str:
    payload = {
        "contract": CONTRACT_VERSION,
        "versions": QUESTION_VERSIONS,
        "crop_sha256": crop_sha256,
        "sent_sha256": sent_sha256,
        "tier": tier,
        "model_id": model_id,
        "image_transform": image_transform,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AiCache:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(entry, dict) or not 200 <= int(entry.get("status", 0)) < 300:
            return None
        return entry

    def put(self, key: str, entry: dict) -> bool:
        status = int(entry.get("status", 0))
        if not 200 <= status < 300 or entry.get("interpretation") is None:
            return False
        self.directory.mkdir(parents=True, exist_ok=True)
        data = {"cached_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), **entry}
        tmp = self._path(key).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self._path(key))
        return True
