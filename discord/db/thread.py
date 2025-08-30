# 터주 스레드 관리를 위한 데이터베이스 작업을 위한 함수

from db.db import get_connection

# 채널 내 특정 유저들의 스레드 존재 여부 반환
async def select_duplicated_thread(channel_id: int, user_ids: list[int]) -> int | None:
    conn = await get_connection()
    row = await conn.fetchrow("""
        SELECT channel_id
        FROM discord.thread
        WHERE channel_id = $1 AND user_ids = $2::BIGINT[]
    """, channel_id, sorted(user_ids))
    await conn.close()
    return row["channel_id"] if row else None

# 특정 유저들의 스레드 생성 혹은 갱신
async def upsert_thread (channel_id: int, user_ids: list[int], thread_id: int, message_id: int) -> None:
    conn = await get_connection()
    await conn.execute("""
        INSERT INTO discord.thread (channel_id, user_ids, thread_id, message_id)
        VALUES ($1, $2::BIGINT[], $3, $4)
        ON CONFLICT (channel_id, user_ids)
        DO UPDATE SET thread_id = EXCLUDED.thread_id, message_id = EXCLUDED.message_id, updated_at = NOW()
    """, channel_id, sorted(user_ids), thread_id, message_id)
    await conn.close()

# 특정 스레드 ID를 가진 스레드 삭제
async def delete_thread_by_id(thread_id: int) -> None:
    conn = await get_connection()
    await conn.execute("""
        DELETE FROM discord.thread_data
        WHERE thread_id = $1
    """, thread_id)
    await conn.close()

# 모든 스레드 정보 반환
async def select_thread() -> list[dict]:
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT * FROM discord.thread
    """)
    await conn.close()
    return [dict(r) for r in rows]

# 메세지 ID 업데이트
async def update_thread_message_id(thread_id: int, message_id: int) -> None:
    conn = await get_connection()
    await conn.execute("""
        UPDATE discord.thread
        SET message_id = $2
        WHERE thread_id = $1
    """, thread_id, message_id)
    await conn.close()

# 메세지 해쉬 업데이트
async def update_thread_hash(message_id: int, last_embed_hash: str) -> None:
    conn = await get_connection()
    await conn.execute("""
        UPDATE discord.thread
        SET last_embed_hash = $2
        WHERE message_id = $1
    """, message_id, last_embed_hash)
    await conn.close()
