"""Kontrola wycinka przed wysłaniem, fail closed (ADR-003 §3.2, D-304).

Sprawdzamy hash z `signs.csv`, sygnaturę JPEG/PNG i brak metadanych (JPEG APP1, PNG eXIf).
Obrazu nie przetwarzamy ponownie.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

JPEG_SOI = b"\xff\xd8"
PNG_SIG = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class CropCheck:
    ok: bool
    data: bytes | None
    reason: str | None  # crop_invalid | unsupported_format | metadata_present


def _jpeg_has_app1(data: bytes) -> bool:
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return False  # uszkodzona struktura: brak markera
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker == 0xDA:  # SOS: dalej dane obrazu
            return False
        if 0xD0 <= marker <= 0xD9 or marker == 0x01:
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        if marker == 0xE1:
            return True
        i += 2 + length
    return False


def _png_has_exif(data: bytes) -> bool:
    i = len(PNG_SIG)
    while i + 8 <= len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        kind = data[i + 4 : i + 8]
        if kind == b"eXIf":
            return True
        if kind == b"IEND":
            return False
        i += 12 + length
    return False


def check_crop(path: Path, expected_sha256: str) -> CropCheck:
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError:
        return CropCheck(False, None, "crop_invalid")
    if hashlib.sha256(data).hexdigest() != (expected_sha256 or "").strip().lower():
        return CropCheck(False, None, "crop_invalid")
    if data.startswith(JPEG_SOI):
        if _jpeg_has_app1(data):
            return CropCheck(False, None, "metadata_present")
    elif data.startswith(PNG_SIG):
        if _png_has_exif(data):
            return CropCheck(False, None, "metadata_present")
    else:
        return CropCheck(False, None, "unsupported_format")
    return CropCheck(True, data, None)
