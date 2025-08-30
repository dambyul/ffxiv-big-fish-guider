# 물고기 검색과 관련된 데이터베이스 작업을 위한 함수들

import json
from db.db import get_connection

# 특정 이름의 물고기 반환 (정확검색 -> 유사검색)
async def select_fish_by_search(name: str) -> dict:
    conn = await get_connection()
    row = await conn.fetchrow("""
        SELECT *
        FROM v_fish
        WHERE name_ko = $1 OR name_en = $1 OR name_ja = $1 OR id::TEXT = $1
        LIMIT 1
    """, name)

    if not row:
        row = await conn.fetchrow("""
            SELECT *
            FROM v_fish
            WHERE name_ko ILIKE $1 OR name_en ILIKE $1 OR name_ja ILIKE $1
            LIMIT 1
        """, f"%{name}%")

    await conn.close()
    return dict(row) if row else None

# 특정 ID의 물고기 반환
async def select_fish_by_id(fish_id: int):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT * FROM v_fish WHERE id = $1", fish_id)
    await conn.close()
    return dict(row) if row else None

# 특정 ID의 낚시법 반환
async def select_bait_by_fish_id(fish_id: int):
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT *
        FROM v_fish_bait
        WHERE fish_id = $1
        ORDER BY step_no
    """, fish_id)
    await conn.close()
    return [dict(r) for r in rows]