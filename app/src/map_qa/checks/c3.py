"""C3: niepewne dopasowania zdjęcie–droga i etykieta „uncertain link” (AC-16, AC-19)."""

from __future__ import annotations

import pandas as pd
from shapely.geometry import Point

from map_qa.checks import UNCERTAIN_NOTE, apply_photo
from map_qa.model import FILE_FLAGS, OWN_FLAGS, Candidate


def _flags(links: pd.DataFrame) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    return {
        r.photo_id: (tuple(sorted(r.file_flags)), tuple(r.own_flags))
        for r in links.itertuples(index=False)
    }


def check_uncertain(links: pd.DataFrame, photos: pd.DataFrame) -> tuple[dict, list[Candidate]]:
    """Podsumowanie flag (z pliku i własnych osobno) i jedno zadanie C3 na zdjęcie z flagą."""
    file_counts = dict.fromkeys(FILE_FLAGS, 0)
    own_counts = dict.fromkeys(OWN_FLAGS, 0)
    extra_file: dict[str, int] = {}
    cands: list[Candidate] = []
    by_photo = photos.set_index("photo_id")
    for r in links.sort_values("photo_id").itertuples(index=False):
        for f in r.file_flags:
            if f in file_counts:
                file_counts[f] += 1
            else:
                extra_file[f] = extra_file.get(f, 0) + 1
        for f in r.own_flags:
            own_counts[f] += 1
        if not (r.file_flags or r.own_flags):
            continue
        dist = r.recheck_distance_m if r.recheck_distance_m is not None else None
        if dist is None and r.distance_m not in ("", None):
            dist = float(r.distance_m)
        photo = by_photo.loc[r.photo_id]
        flags = ", ".join(sorted(r.file_flags) + list(r.own_flags))
        cand = Candidate(
            check="C3",
            reason_code="uncertain_link",
            osm_id=int(r.osm_way_id) if r.osm_way_id else None,
            segment_id=r.overture_id or "",
            photo_id=r.photo_id,
            photo_ids=(r.photo_id,),
            distance_m=None if dist is None else round(float(dist), 1),
            uncertain_link=True,
            file_flags=tuple(sorted(r.file_flags)),
            own_flags=tuple(r.own_flags),
            description_pl=(
                f"Dopasowanie zdjęcia do drogi jest niepewne (flagi: {flags}). Wymaga "
                "sprawdzenia przed użyciem zdjęcia jako dowodu. Kierunek aparatu nie jest "
                "kierunkiem jazdy."
            ),
            geometry=Point(float(photo["longitude"]), float(photo["latitude"])),
        )
        apply_photo(cand, photos)
        cands.append(cand)
    summary = {
        "file_flags": file_counts,
        "own_flags": own_counts,
        "other_file_flags": extra_file,
        "photos_with_flag": len(cands),
        "photos_total": int(len(links)),
    }
    return summary, cands


def label_uncertain(candidates: list[Candidate], links: pd.DataFrame) -> None:
    """Etykieta „uncertain link” dla kandydatów C1/C2/C4 ze zdjęciem z flagą (AC-19)."""
    flags = _flags(links)
    for c in candidates:
        file_f: set[str] = set()
        own_f: set[str] = set()
        for pid in c.photo_ids or ((c.photo_id,) if c.photo_id else ()):
            ff, of = flags.get(pid, ((), ()))
            file_f |= set(ff)
            own_f |= set(of)
        if not (file_f or own_f):
            continue
        c.file_flags = tuple(sorted(set(c.file_flags) | file_f))
        c.own_flags = tuple(f for f in OWN_FLAGS if f in own_f or f in c.own_flags)
        c.uncertain_link = True
        c.description_pl += UNCERTAIN_NOTE.format(flags=", ".join(c.file_flags + c.own_flags))
