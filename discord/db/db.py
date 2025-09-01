# 데이터베이스 접속을 위한 함수

import asyncpg
from config import DATABASE_URL

async def get_connection():
    return await asyncpg.connect(DATABASE_URL)
