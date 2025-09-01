from airflow.sdk import DAG, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
import requests
import re
import json
import math
from datetime import datetime

URL = "https://ff14fish.carbuncleplushy.com/js/app/data.js"
UNQUOTED_KEY = re.compile(r'(?<=[{,\s])([A-Za-z_][A-Za-z0-9_]*)\s*:', re.MULTILINE)
INT_RE = re.compile(r'^-?\d+$')

def extract_js_object_block(js_text: str, var_name: str = "DATA") -> str:
    pattern = re.compile(
        rf'(?:^|\s)(?:var|let|const)\s+{re.escape(var_name)}\s*=\s*\{{',
        re.MULTILINE,
    )
    m = pattern.search(js_text)
    if not m:
        raise ValueError(f"{var_name} 시작 시그니처를 찾지 못했습니다.")

    start = m.end() - 1
    depth = 0
    i = start
    in_str = False
    esc = False
    quote = ''

    while i < len(js_text):
        ch = js_text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == quote:
                in_str = False
        else:
            if ch in ("'", '"'):
                in_str = True
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return js_text[start:i+1]
        i += 1

    raise ValueError(f"{var_name} 오류.")

def js_object_to_json_text(js_obj_text: str) -> str:
    return UNQUOTED_KEY.sub(r'"\1":', js_obj_text)

def to_int_safe(x):
    if isinstance(x, (list, tuple)) and x:
        x = x[0]
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        try:
            return int(x)
        except Exception:
            return None
    if isinstance(x, str):
        s = x.strip().strip('",\'')
        if INT_RE.match(s):
            try: return int(s)
            except: return None
    return None

def to_num_safe(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        return float(x)
    if isinstance(x, str):
        s = x.strip().strip('",\'')
        try:
            return float(s)
        except Exception:
            return None
    return None

def to_float_safe(x, limit=1e9):
    if isinstance(x, (list, tuple)) and x:
        x = x[0]
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        v = float(x)
        if math.isnan(v) or math.isinf(v) or abs(v) > limit:
            return None
        return v
    if isinstance(x, str):
        s = x.strip().strip('",\'')
        try:
            v = float(s)
            if math.isnan(v) or math.isinf(v) or abs(v) > limit:
                return None
            return v
        except Exception:
            return None
    return None

def to_str_safe(x):
    return str(x).strip() if isinstance(x, str) else None

def to_bool_safe(x):
    return bool(x) if isinstance(x, bool) else None

@task()
def upsert_from_data_js():
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 Airflow/3.0"})
    resp.raise_for_status()
    text = resp.text

    js_obj = extract_js_object_block(text, "DATA")
    data = json.loads(js_object_to_json_text(js_obj))

    fish_map   = (data or {}).get("FISH")   or {}
    zones_map  = (data or {}).get("ZONES")  or {}
    area_map  = (data or {}).get("WEATHER_RATES") or {}

    hook = PostgresHook(postgres_conn_id="postgres")
    with hook.get_conn() as conn, conn.cursor() as cur:
        if isinstance(zones_map, dict):
            for zid_raw, z in zones_map.items():
                zid = to_int_safe(zid_raw)
                if zid is None:
                    continue
                cur.execute("""
                    INSERT INTO zone (zone_id, name_en, name_ja, name_ko)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (zone_id) DO UPDATE SET
                      name_en=EXCLUDED.name_en,
                      name_ja=EXCLUDED.name_ja,
                      name_ko=EXCLUDED.name_ko
                """, (
                    zid,
                    (z or {}).get("name_en"),
                    (z or {}).get("name_ja"),
                    (z or {}).get("name_ko"),
                ))

        upsert_rule_sql = """
            INSERT INTO fish_rule (
                fish_id, location_id, start_hour, end_hour, patch, folklore_id,
                collectable, fish_eyes, big_fish, snagging, lure_id, hookset, tug, gig,
                aquarium_water, aquarium_size, intuition_length, data_missing, updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
            ON CONFLICT (fish_id) DO UPDATE SET
              location_id=EXCLUDED.location_id,
              start_hour=EXCLUDED.start_hour,
              end_hour=EXCLUDED.end_hour,
              patch=EXCLUDED.patch,
              folklore_id=EXCLUDED.folklore_id,
              collectable=EXCLUDED.collectable,
              fish_eyes=EXCLUDED.fish_eyes,
              big_fish=EXCLUDED.big_fish,
              snagging=EXCLUDED.snagging,
              lure_id=EXCLUDED.lure_id,
              hookset=EXCLUDED.hookset,
              tug=EXCLUDED.tug,
              gig=EXCLUDED.gig,
              aquarium_water=EXCLUDED.aquarium_water,
              aquarium_size=EXCLUDED.aquarium_size,
              intuition_length = EXCLUDED.intuition_length,
              data_missing=EXCLUDED.data_missing,
              updated_at=NOW()
        """
        
        upsert_best_path  = """
            INSERT INTO fish_best_path (fish_id, step_no, item_id)
            VALUES (%s,%s,%s)
            ON CONFLICT (fish_id, step_no) DO UPDATE SET item_id=EXCLUDED.item_id
        """
        upsert_predator = """
            INSERT INTO fish_predator (fish_id, predator_id, required_count)
            VALUES (%s,%s,%s)
            ON CONFLICT (fish_id, predator_id) DO UPDATE SET
            required_count = EXCLUDED.required_count
        """

        if isinstance(fish_map, dict):
            for k_raw, v in fish_map.items():
                if not isinstance(v, dict):
                    continue
                fid = to_int_safe(v.get("_id")) or to_int_safe(k_raw)
                if fid is None:
                    continue

                aq = v.get("aquarium") or {}
                cur.execute(
                    upsert_rule_sql,
                    (
                        fid,
                        to_int_safe(v.get("location")),
                        to_num_safe(v.get("startHour")),
                        to_num_safe(v.get("endHour")),
                        to_num_safe(v.get("patch")),
                        to_int_safe(v.get("folklore")),
                        to_int_safe(v.get("collectable")),
                        to_bool_safe(v.get("fishEyes")),
                        to_bool_safe(v.get("bigFish")),
                        to_bool_safe(v.get("snagging")),
                        to_int_safe(v.get("lure")),
                        to_str_safe(v.get("hookset")),
                        to_str_safe(v.get("tug")),
                        to_str_safe(v.get("gig")),
                        to_str_safe(aq.get("water")) if isinstance(aq, dict) else None,
                        to_int_safe(aq.get("size")) if isinstance(aq, dict) else None,
                        to_int_safe(v.get("intuitionLength")),
                        to_bool_safe(v.get("dataMissing")),
                    ),
                )

                for idx, item_raw in enumerate(v.get("bestCatchPath") or [], start=1):
                    item_id = to_int_safe(item_raw)
                    if item_id is not None:
                        cur.execute(upsert_best_path, (fid, idx, item_id))

                for p_raw in (v.get("predators") or []):
                    pid = None
                    cnt = None
                    if isinstance(p_raw, (list, tuple)):
                        if len(p_raw) >= 1:
                            pid = to_int_safe(p_raw[0])
                        if len(p_raw) >= 2:
                            cnt = to_int_safe(p_raw[1])
                    else:
                        pid = to_int_safe(p_raw)

                    if pid is not None:
                        cur.execute(upsert_predator, (fid, pid, cnt))

        for top_key, section in (data or {}).items():
            if top_key in ("FISH", "ZONES", "WEATHER_RATES", "WEATHER_TYPE", "WEATHER_TYPES", "WEATHER"):
                continue
            if not isinstance(section, dict):
                continue
            for sid_raw, obj in section.items():
                if not isinstance(obj, dict):
                    continue

                if ("name_en" in obj or "name_ja" in obj or "name_ko" in obj) and ("icon" in obj or "ilvl" in obj):
                    item_id = to_int_safe(obj.get("_id")) or to_int_safe(sid_raw)
                    if item_id is not None:
                        cur.execute("""
                            INSERT INTO item_meta (item_id, name_en, name_ja, name_ko, icon, ilvl, updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s, NOW())
                            ON CONFLICT (item_id) DO UPDATE SET
                              name_en=EXCLUDED.name_en,
                              name_ja=EXCLUDED.name_ja,
                              name_ko=EXCLUDED.name_ko,
                              icon=EXCLUDED.icon,
                              ilvl=EXCLUDED.ilvl,
                              updated_at=NOW()
                        """, (
                            item_id,
                            obj.get("name_en"),
                            obj.get("name_ja"),
                            obj.get("name_ko"),
                            obj.get("icon"),
                            to_int_safe(obj.get("ilvl")),
                        ))

                if "territory_id" in obj and "map_coords" in obj:
                    spot_id = to_int_safe(obj.get("_id")) or to_int_safe(sid_raw)
                    if spot_id is None:
                        continue
                    coords = obj.get("map_coords") or []
                    mx = to_float_safe(coords[0]) if isinstance(coords, (list, tuple)) and len(coords) >= 1 else None
                    my = to_float_safe(coords[1]) if isinstance(coords, (list, tuple)) and len(coords) >= 2 else None
                    mz = to_float_safe(coords[2]) if isinstance(coords, (list, tuple)) and len(coords) >= 3 else None

                    cur.execute("""
                        INSERT INTO fishing_spot (spot_id, name_en, name_ja, name_ko, territory_id, placename_id, map_x, map_y, map_z, updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                        ON CONFLICT (spot_id) DO UPDATE SET
                          name_en=EXCLUDED.name_en,
                          name_ja=EXCLUDED.name_ja,
                          name_ko=EXCLUDED.name_ko,
                          territory_id=EXCLUDED.territory_id,
                          placename_id=EXCLUDED.placename_id,
                          map_x=EXCLUDED.map_x,
                          map_y=EXCLUDED.map_y,
                          map_z=EXCLUDED.map_z,
                          updated_at=NOW()
                    """, (
                        spot_id,
                        obj.get("name_en"),
                        obj.get("name_ja"),
                        obj.get("name_ko"),
                        to_int_safe(obj.get("territory_id")),
                        to_int_safe(obj.get("placename_id")),
                        mx, my, mz
                    ))

        if isinstance(area_map, dict):
            for area_raw, obj in area_map.items():
                area_id = to_int_safe(area_raw)
                if area_id is None or not isinstance(obj, dict):
                    continue

                cur.execute("""
                    INSERT INTO area (area_id, map_id, map_scale, zone_id, region_id, updated_at)
                    VALUES (%s,%s,%s,%s,%s, NOW())
                    ON CONFLICT (area_id) DO UPDATE SET
                      map_id=EXCLUDED.map_id,
                      map_scale=EXCLUDED.map_scale,
                      zone_id=EXCLUDED.zone_id,
                      region_id=EXCLUDED.region_id,
                      updated_at=NOW()
                """, (
                    area_id,
                    to_int_safe(obj.get("map_id")),
                    to_int_safe(obj.get("map_scale")),
                    to_int_safe(obj.get("zone_id")),
                    to_int_safe(obj.get("region_id")),
                ))

        conn.commit()

with DAG(
    dag_id="fetch_data_info",
    start_date=datetime(2025, 7, 1),
    schedule="*/30 * * * *",
    catchup=False,
    tags=["data", "carbuncleplushy", "json"],
    description="물고기 관련 데이터 수집",
) as dag:
    load = upsert_from_data_js()
