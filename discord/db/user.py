# 유저 데이터와 관련된 데이터베이스 작업을 위한 함수들

import json
from db.db import get_connection

"""
유저 데이터 업로드를 위한 개인 스레드 함수
"""
# 특정 유저의 업로드용 스레드 존재 여부 확인
async def select_upload_thread(guild_id: int, user_id: int) -> int:
    conn = await get_connection()
    row = await conn.fetchrow("""
        SELECT thread_id
        FROM discord.upload_thread
        WHERE guild_id = $1 AND user_id = $2
    """, guild_id, user_id)
    await conn.close()
    return row["thread_id"] if row else None

# 특정 유저의 업로드용 스레드 생성 혹은 갱신
async def insert_upload_thread(guild_id: int, user_id: int, thread_id: int) -> None:
    conn = await get_connection()
    await conn.execute("""
        INSERT INTO discord.upload_thread (guild_id, user_id, thread_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (guild_id, user_id)
        DO UPDATE SET thread_id = EXCLUDED.thread_id, created_at = NOW()
    """, guild_id, user_id, thread_id)
    await conn.close()

# 특정 유저의 업로드용 스레드 삭제
async def delete_upload_thread(guild_id: int, user_id: int) -> None:
    conn = await get_connection()
    await conn.execute("""
        DELETE FROM discord.upload_thread
        WHERE guild_id = $1 AND user_id = $2
    """, guild_id, user_id)
    await conn.close()

"""
유저 데이터 업로드 함수
"""
# 특정 유저가 잡은 물고기 ID 목록 반환
async def select_caught_fish(user_id: int) -> list[int]:
    conn = await get_connection()
    row = await conn.fetchrow("SELECT caught_fish FROM discord.v_caught_fish WHERE user_id = $1", user_id)
    await conn.close()
    return row["caught_fish"] if row else []

# 특정 유저의 잡은 물고기 데이터 삽입 혹은 갱신
async def upsert_caught_fish(user_id: int, fish_ids: list[int]) -> None:
    conn = await get_connection()
    seen = set()
    uniq: list[int] = []
    for x in fish_ids:
        if x not in seen:
            seen.add(x)
            uniq.append(x)

    json_array = json.dumps(uniq, ensure_ascii=False, separators=(",", ":"))

    await conn.execute("""
        INSERT INTO discord.user (user_id, caught_fish, updated_at)
        VALUES ($1, $2::jsonb, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET caught_fish = EXCLUDED.caught_fish, updated_at = NOW()
    """, user_id, json_array)
    await conn.close()

# 새로 잡은 물고기 정보 반환
async def select_new_caught_fish(fish_ids: list[int]) -> list[dict]:
    if not fish_ids:
        return []

    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT name_ko, name_en, name_ja, king_fish
        FROM v_fish
        WHERE big_fish IS TRUE
          AND id = ANY($1::int[])
        ORDER BY id
    """, fish_ids)
    await conn.close()

    return [dict(r) for r in rows]

# 선호 언어 변경
async def update_user_prefer_lang(user_id: int, lang: str) -> None:
    conn = await get_connection()
    try:
        # user 테이블이 이미 존재한다고 가정, 없으면 생성/업서트 패턴
        await conn.execute("""
            INSERT INTO discord.user (user_id, prefer_lang, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET prefer_lang = EXCLUDED.prefer_lang,
                          updated_at  = NOW()
        """, user_id, lang)
    finally:
        await conn.close()

# 물고기 APPEND
async def append_caught_fish(user_id: int, fish_id: int) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO discord.user (user_id, caught_fish, updated_at)
            VALUES ($1, to_jsonb(ARRAY[$2::int]), NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET caught_fish = CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(discord.user.caught_fish) AS e(elem)
                    WHERE e.elem = to_jsonb($2::int)
                )
                THEN discord.user.caught_fish
                ELSE discord.user.caught_fish || to_jsonb(ARRAY[$2::int])
            END,
                updated_at = NOW()
            """,
            user_id, fish_id
        )
    finally:
        await conn.close()