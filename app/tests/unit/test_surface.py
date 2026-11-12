"""AC-13; ADR-001 §3.4, TAC-001-03."""

import csv
from importlib.resources import files

import pytest

from map_qa.normalize.surface import surface_family, surface_mapping


def test_csv_no_duplicates_and_valid_families():
    path = files("map_qa") / "data" / "surface_families.csv"
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    pairs = [(r["source"], r["value"]) for r in rows]
    assert len(pairs) == len(set(pairs))
    assert {r["family"] for r in rows} <= {"paved", "unpaved", "unknown"}
    assert {r["source"] for r in rows} == {"osm", "overture"}


@pytest.mark.parametrize(
    "source,value,family",
    [
        ("osm", "asphalt", "paved"),
        ("osm", "concrete_slabs", "paved"),
        ("osm", "metal_grid", "paved"),
        ("osm", "gravel", "unpaved"),
        ("osm", "grass_paver", "unknown"),
        ("osm", "contrete:plates", "unknown"),
        ("osm", "paving_Stones", "unknown"),  # bez ignorowania wielkości liter
        ("osm", "nowa_wartosc", "unknown"),
        ("overture", "paved", "paved"),
        ("overture", "paving_stones", "paved"),
        ("overture", "metal", "paved"),
        ("overture", "dirt", "unpaved"),
        ("overture", "unknown", "unknown"),
    ],
)
def test_family(source, value, family):
    assert surface_family(source, value) == family


def test_mapping_for_report():
    assert ("osm", "asphalt", "paved") in surface_mapping()
