import requests
import re
import json
from datetime import datetime
from airflow.sdk import DAG, task
from airflow.providers.postgres.hooks.postgres import PostgresHook

URL = "https://ff14fish.carbuncleplushy.com/js/app/fish_info_data.js"

ARR_REGEX = re.compile(
    r"(?:^|\s)(?:var|let|const)\s+FISH_INFO\s*=\s*(\[[\s\S]*?\])\s*;",
    re.MULTILINE
)

@task()
def fetch_and_upsert_fish_info():
    # 1) 가져오기
    resp = requests.get(URL, timeout=20, headers={"User-Agent": "Mozilla/5.0 Airflow/3.0"})
    resp.raise_for_status()
    text = resp.text

    fish_map = None

    # 2) 배열형 우선 매칭
    m_arr = ARR_REGEX.search(text)
    if m_arr:
        arr = json.loads(m_arr.group(1))  # [ { "id": 4776, "name_en": "...", ... }, ... ]
        fish_map = {}
        for item in arr:
            fid = int(item["id"])
            fish_map[fid] = {
                "name_ko": item.get("name_ko"),
                "name_en": item.get("name_en"),
                "name_ja": item.get("name_ja"),
                # 소스 구조에 따라 아이콘 키가 다를 수 있음
                "icon": item.get("icon") or item.get("icon_url") or item.get("iconId"),
            }

    # 3) (옵션) 객체형도 허용
    if fish_map is None:
        m_obj = OBJ_REGEX.search(text)
        if m_obj:
            obj = json.loads(m_obj.group(1) or m_obj.group(2))  # { "4776": {...}, ... }
            fish_map = {int(k): v for k, v in obj.items()}

    if fish_map is None:
        snippet = text[:300].replace("\n", "\\n")
        raise ValueError(f"FISH_INFO / fish_info_data JSON not found. snippet={snippet}")

    # 4) DB 업서트
    hook = PostgresHook(postgres_conn_id="postgres")
    with hook.get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fish_info (
                id INTEGER PRIMARY KEY,
                name_ko TEXT,
                name_en TEXT,
                name_ja TEXT,
                icon TEXT,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        upsert_sql = """
            INSERT INTO fish_info (id, name_ko, name_en, name_ja, icon, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET
              name_ko = EXCLUDED.name_ko,
              name_en = EXCLUDED.name_en,
              name_ja = EXCLUDED.name_ja,
              icon = EXCLUDED.icon,
              updated_at = NOW();
        """
        for fid, f in fish_map.items():
            cur.execute(
                upsert_sql,
                (
                    fid,
                    f.get("name_ko"),
                    f.get("name_en"),
                    f.get("name_ja"),
                    f.get("icon"),
                ),
            )
        conn.commit()

with DAG(
    dag_id="fetch_fish_info",
    start_date=datetime(2025, 7, 1),
    schedule="*/30 * * * *",
    catchup=False,
    tags=["data", "carbuncleplushy", "json"],
    description="물고기 기본 데이터 수집",
) as dag:
    fetch_task = fetch_and_upsert_fish_info()
