"""AC-21 (tylko obraz, bez metadanych); ADR-003 §3.2, D-304."""

import hashlib

import pytest

from map_qa.signs.crop_check import check_crop

CROP = "mapillary_1237130608489136"


@pytest.fixture
def crop(fixtures_dir, tmp_path):
    src = fixtures_dir / "map_qa" / "signs" / "crops" / f"{CROP}.jpg"
    dst = tmp_path / f"{CROP}.jpg"
    dst.write_bytes(src.read_bytes())
    return dst


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_crop(crop):
    res = check_crop(crop, sha(crop))
    assert res.ok and res.data == crop.read_bytes() and res.reason is None


def test_changed_byte_is_crop_invalid(crop):
    expected = sha(crop)
    data = bytearray(crop.read_bytes())
    data[100] ^= 0xFF
    crop.write_bytes(bytes(data))
    res = check_crop(crop, expected)
    assert not res.ok and res.reason == "crop_invalid" and res.data is None


def test_missing_file(tmp_path):
    res = check_crop(tmp_path / "nope.jpg", "0" * 64)
    assert not res.ok and res.reason == "crop_invalid"


def test_app1_exif_is_metadata_present(crop):
    data = crop.read_bytes()
    exif = b"\xff\xe1\x00\x10Exif\x00\x00MM\x00\x2a\x00\x00\x00\x08"
    tampered = data[:2] + exif + data[2:]
    crop.write_bytes(tampered)
    res = check_crop(crop, hashlib.sha256(tampered).hexdigest())
    assert not res.ok and res.reason == "metadata_present"


def test_png_with_exif_chunk(tmp_path):
    import struct
    import zlib

    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
        + chunk(b"eXIf", b"MM\x00\x2a")
        + chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + chunk(b"IEND", b"")
    )
    p = tmp_path / "x.png"
    p.write_bytes(png)
    res = check_crop(p, hashlib.sha256(png).hexdigest())
    assert res.reason == "metadata_present"


def test_unsupported_format(tmp_path):
    p = tmp_path / "x.gif"
    p.write_bytes(b"GIF89a....")
    res = check_crop(p, hashlib.sha256(p.read_bytes()).hexdigest())
    assert res.reason == "unsupported_format"


def test_all_fixture_crops_pass(fixtures_dir):
    import csv

    base = fixtures_dir / "map_qa" / "signs"
    with (base / "signs.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assert check_crop(base / "crops" / f"{row['photo_id']}.jpg", row["crop_sha256"]).ok
