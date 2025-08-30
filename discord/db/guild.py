# 디스코드 채널과 관련된 데이터베이스 작업을 위한 함수들

from db.db import get_connection

# 전체 가입 채널 조회
async def select_all_guild_ids() -> list[int]:
    conn = await get_connection()
    try:
        rows = await conn.fetch("SELECT guild_id FROM discord.guild")
        return [r["guild_id"] for r in rows]
    finally:
        await conn.close()

# 특정 채널의 설정값 반환
async def select_guild_config(guild_id: int) -> dict:
    conn = await get_connection()
    row = await conn.fetchrow("""
        SELECT channel_id, message_id
        FROM discord.guild
        WHERE guild_id = $1
    """, guild_id)
    await conn.close()
    return dict(row) if row else None

# 특정 채널의 설정 생성 혹은 갱신
async def upsert_guild_config(guild_id: int, channel_id: int, message_id: int) -> None:
    conn = await get_connection()
    await conn.execute("""
        INSERT INTO discord.guild (guild_id, channel_id, message_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (guild_id)
        DO UPDATE SET channel_id = $2, message_id = $3, updated_at = NOW()
    """, guild_id, channel_id, message_id)
    await conn.close()

# 특정 채널의 설정값 삭제
async def delete_guild_config(guild_id: int) -> None:
    conn = await get_connection()
    row = await conn.fetchrow("""
        DELETE FROM discord.guild
        WHERE guild_id = $1
    """, guild_id)
    await conn.close()
    return dict(row) if row else None

# 특정 채널의 메시지 ID 갱신
async def update_guild_message_id(guild_id: int, message_id: int) -> None:
    conn = await get_connection()
    await conn.execute("""
        UPDATE discord.guild
        SET message_id = $1, updated_at = NOW()
        WHERE guild_id = $2
    """, message_id, guild_id)
    await conn.close()