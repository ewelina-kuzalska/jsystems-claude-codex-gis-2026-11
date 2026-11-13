# /// script
# requires-python = ">=3.12"
# dependencies = ["duckdb==1.5.6"]
# ///
"""Dodatkowe zapytania profilujące (tylko odczyt) dla punktów otwartych w ADR."""
import hashlib
import json
import sys
from pathlib import Path

import duckdb

base = Path(sys.argv[1]).resolve()
con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial; SET memory_limit='3GB'; SET threads=4")


def q(title, sql):
    print(f"\n### {title}\n{sql.strip()}")
    con.sql(sql).show(max_rows=60, max_width=250)


osm = f"read_parquet('{(base / 'osm_roads.parquet').as_posix()}')"
ovt = f"read_parquet('{(base / 'overture_segments.parquet').as_posix()}')"
csv = lambda name: f"read_csv('{(base / name).as_posix()}', all_varchar=true)"  # noqa: E731

q("OSM schema", f"DESCRIBE SELECT * FROM {osm}")
q("Overture schema", f"DESCRIBE SELECT * FROM {ovt}")

q("Overture speed_limits: rules per segment",
  f"SELECT len(speed_limits) n_rules, count(*) segments FROM {ovt} WHERE speed_limits IS NOT NULL GROUP BY 1 ORDER BY 1")
q("Overture speed rule flags",
  f"""WITH r AS (SELECT unnest(speed_limits) s FROM {ovt})
  SELECT count(*) rules,
    count(*) FILTER (WHERE s['when'] IS NOT NULL) with_when,
    count(*) FILTER (WHERE s['between'] IS NOT NULL) with_between,
    count(*) FILTER (WHERE s.max_speed IS NULL) no_max_speed,
    count(*) FILTER (WHERE s.min_speed IS NOT NULL) with_min_speed,
    count(*) FILTER (WHERE s.is_max_speed_variable) is_variable
  FROM r""")
q("Overture speed units", f"WITH r AS (SELECT unnest(speed_limits) s FROM {ovt}) SELECT s.max_speed.unit unit, count(*) FROM r GROUP BY 1 ORDER BY 2 DESC")
q("Overture speed values", f"WITH r AS (SELECT unnest(speed_limits) s FROM {ovt}) SELECT s.max_speed.value v, count(*) n FROM r GROUP BY 1 ORDER BY 2 DESC LIMIT 25")
q("Overture speed 'when' examples",
  f"WITH r AS (SELECT unnest(speed_limits) s FROM {ovt}) SELECT to_json(s['when']) w, count(*) n FROM r WHERE s['when'] IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15")
q("Overture speed 'between' examples",
  f"WITH r AS (SELECT unnest(speed_limits) s FROM {ovt}) SELECT to_json(s['between']) b, count(*) n FROM r WHERE s['between'] IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
q("Overture example segment with >=2 speed rules",
  f"SELECT id, to_json(speed_limits) rules FROM {ovt} WHERE len(speed_limits) >= 2 ORDER BY id LIMIT 3")

q("Overture road_surface: rules per segment",
  f"SELECT len(road_surface) n_rules, count(*) segments FROM {ovt} WHERE road_surface IS NOT NULL GROUP BY 1 ORDER BY 1")
q("Overture road_surface values",
  f"WITH r AS (SELECT unnest(road_surface) s FROM {ovt}) SELECT s.value v, count(*) n, count(*) FILTER (WHERE s['between'] IS NOT NULL) with_between FROM r GROUP BY 1 ORDER BY 2 DESC")

q("Overture sources: dataset and record_id prefix",
  f"""WITH s AS (SELECT id, unnest(sources) src FROM {ovt})
  SELECT src.dataset, regexp_extract(src.record_id, '^([a-z]+)', 1) prefix,
         count(*) n, count(*) FILTER (WHERE regexp_matches(src.record_id, '^w[0-9]+@[0-9]+$')) way_pattern
  FROM s GROUP BY 1, 2 ORDER BY 3 DESC""")
q("Overture sources: example record_id", f"WITH s AS (SELECT unnest(sources) src FROM {ovt}) SELECT to_json(src) FROM s LIMIT 3")
q("Overture -> OSM way reference coverage",
  f"""WITH s AS (SELECT id, unnest(sources) src FROM {ovt}),
  w AS (SELECT DISTINCT id, CAST(regexp_extract(src.record_id, '^w([0-9]+)@', 1) AS BIGINT) way FROM s
        WHERE regexp_matches(src.record_id, '^w[0-9]+@'))
  SELECT (SELECT count(*) FROM {ovt}) segments,
         count(DISTINCT w.id) segments_with_way_ref,
         count(DISTINCT w.id) FILTER (WHERE o.osm_id IS NOT NULL) ref_way_in_snapshot,
         count(*) pairs,
         count(*) FILTER (WHERE o.osm_id IS NOT NULL) pairs_in_snapshot
  FROM w LEFT JOIN (SELECT osm_id FROM {osm}) o ON o.osm_id = w.way""")

q("OSM surface values (top 40)", f"SELECT surface, count(*) n FROM {osm} WHERE surface IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 40")
q("OSM maxspeed raw values (top 40)", f"SELECT maxspeed, count(*) n FROM {osm} WHERE maxspeed IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 40")
q("OSM maxspeed non-plain-integer values",
  f"SELECT maxspeed, count(*) n FROM {osm} WHERE maxspeed IS NOT NULL AND NOT regexp_matches(maxspeed, '^[0-9]+$') GROUP BY 1 ORDER BY 2 DESC")
q("OSM tags column vs dedicated columns (maxspeed consistency)",
  f"SELECT count(*) FILTER (WHERE json_extract_string(tags, '$.maxspeed') IS DISTINCT FROM maxspeed) mismatched FROM {osm}")
q("OSM tags: access / bridge / tunnel / layer",
  f"""SELECT count(*) FILTER (WHERE json_extract_string(tags,'$.access') IN ('private','no','customers','delivery','permit')) restricted,
    count(*) FILTER (WHERE json_extract_string(tags,'$.bridge') IS NOT NULL) bridge,
    count(*) FILTER (WHERE json_extract_string(tags,'$.tunnel') IS NOT NULL) tunnel,
    count(*) FILTER (WHERE coalesce(json_extract_string(tags,'$.layer'),'0') <> '0') layer_non0
  FROM {osm}""")

q("photos: heading empty vs zero, panorama",
  f"""SELECT source, count(*) n, count(*) FILTER (WHERE heading IS NULL OR heading = '') heading_empty,
    count(*) FILTER (WHERE TRY_CAST(heading AS DOUBLE) = 0) heading_zero,
    count(*) FILTER (WHERE is_panorama = 'True') panorama FROM {csv('photos.csv')} GROUP BY 1""")
q("photo_road_links: candidate_flags",
  f"""WITH f AS (SELECT unnest(string_split(candidate_flags, ';')) flag FROM {csv('photo_road_links.csv')} WHERE candidate_flags IS NOT NULL AND candidate_flags <> '')
  SELECT flag, count(*) n FROM f GROUP BY 1 ORDER BY 2 DESC""")
q("photo_road_links: photos with >=1 flag",
  f"SELECT count(*) FILTER (WHERE candidate_flags IS NOT NULL AND candidate_flags <> '') flagged, count(*) total FROM {csv('photo_road_links.csv')}")
q("photo_road_links: bearing_diff ranges",
  f"SELECT min(CAST(bearing_diff AS DOUBLE)) bd_min, max(CAST(bearing_diff AS DOUBLE)) bd_max, min(CAST(directed_bearing_diff AS DOUBLE)) dbd_min, max(CAST(directed_bearing_diff AS DOUBLE)) dbd_max FROM {csv('photo_road_links.csv')}")

q("signs.csv: counts and mapillary_value",
  f"SELECT source, mapillary_value, count(*) n, count(*) FILTER (WHERE compass_angle IS NULL OR compass_angle='') no_compass FROM {csv('signs/signs.csv')} GROUP BY ALL ORDER BY n DESC")
q("nearest_osm.csv: heading_diff_deg range, flags, directional tags",
  f"""SELECT count(*) n, min(CAST(heading_diff_deg AS DOUBLE)) hd_min, max(CAST(heading_diff_deg AS DOUBLE)) hd_max,
    count(*) FILTER (WHERE osm_way_id IS NULL OR osm_way_id='') no_way,
    count(*) FILTER (WHERE match_flags IS NOT NULL AND match_flags<>'') flagged,
    count(*) FILTER (WHERE maxspeed IS NOT NULL AND maxspeed<>'') with_maxspeed,
    count(*) FILTER (WHERE coalesce(maxspeed_forward,'')<>'' OR coalesce(maxspeed_backward,'')<>'') directional,
    count(*) FILTER (WHERE coalesce(maxspeed_conditional,'')<>'') conditional
  FROM {csv('signs/nearest_osm.csv')}""")
q("nearest_osm.csv: match_flags", f"SELECT match_flags, count(*) n FROM {csv('signs/nearest_osm.csv')} GROUP BY 1 ORDER BY 2 DESC")
q("labels.csv: encoding", f"SELECT sign_value, status, negative_type, count(*) n FROM {csv('signs/labels.csv')} GROUP BY ALL ORDER BY n DESC")
q("reference_labels.csv: schema", f"DESCRIBE SELECT * FROM {csv('reference_labels.csv')}")
q("reference_labels.csv: sample", f"SELECT * FROM {csv('reference_labels.csv')} LIMIT 3")
q("offline/ATTRIBUTION.csv", f"SELECT count(*) n FROM {csv('offline/ATTRIBUTION.csv')}")

# Crops: hash vs signs.csv, format, metadata segments (APP1 EXIF/XMP, PNG eXIf)
print("\n### Crops: hash / format / metadata")
rows = con.sql(f"SELECT photo_id, crop_sha256 FROM {csv('signs/signs.csv')}").fetchall()
stats = {"total": 0, "missing": 0, "hash_ok": 0, "hash_bad": 0, "jpeg": 0, "png": 0, "other": 0, "app1": 0, "png_exif": 0}
for photo_id, sha in rows:
    stats["total"] += 1
    p = base / "signs" / "crops" / f"{photo_id}.jpg"
    if not p.exists():
        stats["missing"] += 1
        continue
    b = p.read_bytes()
    stats["hash_ok" if hashlib.sha256(b).hexdigest() == sha else "hash_bad"] += 1
    if b[:3] == b"\xff\xd8\xff":
        stats["jpeg"] += 1
        i = 2
        while i + 4 <= len(b) and b[i] == 0xFF:
            marker = b[i + 1]
            if marker in (0xDA, 0xD9):
                break
            if marker == 0xE1:
                stats["app1"] += 1
                break
            i += 2 + int.from_bytes(b[i + 2:i + 4], "big")
    elif b[:8] == b"\x89PNG\r\n\x1a\n":
        stats["png"] += 1
        stats["png_exif"] += int(b"eXIf" in b)
    else:
        stats["other"] += 1
print(json.dumps(stats))

# --- Relacje kluczy i duplikaty (dodane 2026-11-12) ---
photos, links, signs, nearest, labels, refl, offl = (
    csv("photos.csv"), csv("photo_road_links.csv"), csv("signs/signs.csv"), csv("signs/nearest_osm.csv"),
    csv("signs/labels.csv"), csv("reference_labels.csv"), csv("offline/ATTRIBUTION.csv"))

q("Duplicates of photo_id per file",
  f"""SELECT 'photos' f, count(*) n, count(DISTINCT photo_id) uniq FROM {photos}
  UNION ALL SELECT 'photo_road_links', count(*), count(DISTINCT photo_id) FROM {links}
  UNION ALL SELECT 'signs', count(*), count(DISTINCT photo_id) FROM {signs}
  UNION ALL SELECT 'nearest_osm', count(*), count(DISTINCT photo_id) FROM {nearest}
  UNION ALL SELECT 'labels', count(*), count(DISTINCT photo_id) FROM {labels}
  UNION ALL SELECT 'reference_labels (photo_id, question)', count(*), count(DISTINCT (photo_id, question)) FROM {refl}
  UNION ALL SELECT 'reference_labels photos', count(DISTINCT photo_id), count(DISTINCT photo_id) FROM {refl}
  UNION ALL SELECT 'offline/ATTRIBUTION', count(*), count(DISTINCT photo_id) FROM {offl}""")
q("photo_id relations (orphans = child keys missing in parent)",
  f"""SELECT 'links -> photos' rel, count(*) FILTER (WHERE p.photo_id IS NULL) orphans, count(*) total FROM {links} l LEFT JOIN {photos} p USING (photo_id)
  UNION ALL SELECT 'photos -> links', count(*) FILTER (WHERE l.photo_id IS NULL), count(*) FROM {photos} p LEFT JOIN {links} l USING (photo_id)
  UNION ALL SELECT 'offline -> photos', count(*) FILTER (WHERE p.photo_id IS NULL), count(*) FROM {offl} o LEFT JOIN {photos} p USING (photo_id)
  UNION ALL SELECT 'reference_labels -> photos', count(DISTINCT r.photo_id) FILTER (WHERE p.photo_id IS NULL), count(DISTINCT r.photo_id) FROM {refl} r LEFT JOIN {photos} p USING (photo_id)
  UNION ALL SELECT 'nearest_osm -> signs', count(*) FILTER (WHERE s.photo_id IS NULL), count(*) FROM {nearest} n LEFT JOIN {signs} s USING (photo_id)
  UNION ALL SELECT 'labels -> signs', count(*) FILTER (WHERE s.photo_id IS NULL), count(*) FROM {labels} x LEFT JOIN {signs} s USING (photo_id)
  UNION ALL SELECT 'signs -> labels', count(*) FILTER (WHERE x.photo_id IS NULL), count(*) FROM {signs} s LEFT JOIN {labels} x USING (photo_id)
  UNION ALL SELECT 'signs -> photos.csv (overlap)', count(*) FILTER (WHERE p.photo_id IS NOT NULL), count(*) FROM {signs} s LEFT JOIN {photos} p USING (photo_id)""")
q("Way / segment key relations",
  f"""SELECT 'links.osm_way_id -> osm_roads' rel, count(*) FILTER (WHERE o.osm_id IS NULL) orphans, count(*) total
     FROM (SELECT CAST(osm_way_id AS BIGINT) w FROM {links} WHERE osm_way_id IS NOT NULL) l LEFT JOIN (SELECT osm_id FROM {osm}) o ON o.osm_id = l.w
  UNION ALL SELECT 'links.overture_id -> overture', count(*) FILTER (WHERE s.id IS NULL), count(*)
     FROM (SELECT overture_id FROM {links} WHERE overture_id IS NOT NULL) l LEFT JOIN (SELECT id FROM {ovt}) s ON s.id = l.overture_id
  UNION ALL SELECT 'nearest_osm.osm_way_id -> osm_roads', count(*) FILTER (WHERE o.osm_id IS NULL), count(*)
     FROM (SELECT CAST(osm_way_id AS BIGINT) w FROM {nearest}) n LEFT JOIN (SELECT osm_id FROM {osm}) o ON o.osm_id = n.w""")
q("signs: area and OSM context source",
  f"""SELECT s.area, n.source osm_source, count(*) n,
     count(*) FILTER (WHERE CAST(n.distance_m AS DOUBLE) > 25) beyond_25m,
     max(CAST(n.distance_m AS DOUBLE)) max_distance_m
  FROM {signs} s JOIN {nearest} n USING (photo_id) GROUP BY ALL ORDER BY n DESC""")
q("signs: bbox check (Kraków bbox 19.80-20.15 E, 49.95-50.15 N)",
  f"""SELECT count(*) FILTER (WHERE CAST(longitude AS DOUBLE) BETWEEN 19.80 AND 20.15 AND CAST(latitude AS DOUBLE) BETWEEN 49.95 AND 50.15) inside, count(*) total FROM {signs}""")

# --- Formaty tagów prędkości w pełnym JSON tags ---
for key in ["maxspeed:forward", "maxspeed:backward", "maxspeed:conditional", "maxspeed:type", "zone:maxspeed", "source:maxspeed", "maxspeed:hgv"]:
    q(f"OSM tags['{key}'] values",
      f"""SELECT json_extract_string(tags, '$."{key}"') v, count(*) n FROM {osm}
      WHERE json_extract_string(tags, '$."{key}"') IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15""")
q("OSM maxspeed* formats (all keys starting with maxspeed)",
  f"""WITH k AS (SELECT unnest(json_keys(tags)) tag_key, tags FROM {osm}),
  v AS (SELECT tag_key, json_extract_string(tags, '$."' || tag_key || '"') val FROM k WHERE tag_key LIKE 'maxspeed%')
  SELECT tag_key, count(*) n,
    count(*) FILTER (WHERE regexp_matches(val, '^[0-9]+$')) int_kmh,
    count(*) FILTER (WHERE regexp_matches(val, 'mph')) mph,
    count(*) FILTER (WHERE regexp_matches(val, '^[A-Z]{{2}}:')) zone_code,
    count(*) FILTER (WHERE val IN ('none','signals','walk')) special,
    count(*) FILTER (WHERE val LIKE '%;%' OR val LIKE '%|%') multi,
    count(*) FILTER (WHERE val LIKE '%@%') conditional_syntax
  FROM v GROUP BY 1 ORDER BY 2 DESC""")
q("traffic_signs.geojson: object_value",
  f"""SELECT f.properties.object_value v, count(*) n FROM (SELECT unnest(features) f FROM read_json('{(base / 'traffic_signs.geojson').as_posix()}', maximum_object_size=50000000))
  GROUP BY 1 ORDER BY 2 DESC LIMIT 15""")
