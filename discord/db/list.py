# 터주 타이머와 관련된 데이터베이스 작업을 위한 함수들

from db.db import get_connection

# 특정 스레드를 위한 물고기 목록 반환
async def select_fish_list_by_thread(thread_id: int) -> list[dict]:
    conn = await get_connection()
    rows = await conn.fetch("""
        WITH caught_fish AS (SELECT jsonb_agg(DISTINCT f) AS fish_ids
                            FROM discord.thread_data t1
                                    JOIN discord.v_caught_fish t2
                                        ON t2.user_id = ANY (t1.user_ids)
                                    JOIN LATERAL jsonb_array_elements(t2.caught_fish) AS f(f)
                                        ON TRUE
                            WHERE t1.thread_id = $1)
        SELECT *
        FROM v_fish_list v1
        WHERE NOT EXISTS (SELECT 1
                        FROM caught_fish w1
                        WHERE v1.id = ANY (SELECT jsonb_array_elements_text(w1.fish_ids)::int))
        order by current_start NULLS FIRST, uptime_percent DESC
        LIMIT 30      
    """, thread_id)
    await conn.close()

    return [dict(r) for r in rows]

# 터주왕 목록 반환
async def select_king_fish_list() -> list[dict]:
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT *
        FROM v_fish_list v1 where king_fish is true
        order by current_start NULLS FIRST, uptime_percent DESC
    """)
    await conn.close()

    return [dict(r) for r in rows]

# 여러 유저의 caught_fish 전체 합집합 반환
async def select_users_caught_fish(user_ids: list[int]) -> list[int]:
    conn = await get_connection()
    try:
        result = await conn.fetchval("""
            WITH elems AS (
                SELECT (f)::text::int AS fish_id
                FROM discord."user" u
                JOIN LATERAL jsonb_array_elements(u.caught_fish) AS f(f) ON TRUE
                WHERE u.user_id = ANY($1)
                  AND u.caught_fish IS NOT NULL
                  AND jsonb_typeof(f) = 'number'
            )
            SELECT COALESCE(array_agg(DISTINCT fish_id ORDER BY fish_id), '{}')::int[]
            FROM elems;
        """, user_ids)
        return list(result) if result else []
    finally:
        await conn.close()