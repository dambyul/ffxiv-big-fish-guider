import json
import discord
from typing import Sequence, Any, List
from io import StringIO

from config import JSON_PARSE, MAX_DISCORD_MSG
from db.user import (
    select_caught_fish,
    upsert_caught_fish,
    select_new_caught_fish,
)
from core.js_parser import extract_fish_ids

def _ensure_int_list(v: Any) -> List[int]:
    if v is None:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            try:
                out.append(int(x))
            except Exception:
                pass
        return out
    if isinstance(v, (tuple, set)):
        return _ensure_int_list(list(v))
    if isinstance(v, int):
        return [v]
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                return _ensure_int_list(json.loads(s))
            except Exception:
                return []
        if s.startswith("{") and s.endswith("}"):
            inner = s[1:-1].strip()
            if not inner:
                return []
            out = []
            for part in inner.split(","):
                part = part.strip().strip('"').strip("'")
                if not part:
                    continue
                try:
                    out.append(int(part))
                except Exception:
                    pass
            return out
        out = []
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(int(part))
            except Exception:
                pass
        return out
    try:
        return [int(v)]
    except Exception:
        return []

async def send_new_fish_result(message: discord.Message, fish_ids: Sequence[int] | str) -> None:
    ids = _ensure_int_list(fish_ids)
    if not ids:
        await message.channel.send(JSON_PARSE["no_new_fish"])
        return

    fish_info = await select_new_caught_fish(ids) # ★ 문자열 아닌 list[int]만 전달
    names_ko = [f["name_ko"] for f in fish_info]

    if not names_ko:
        await message.channel.send(JSON_PARSE["no_new_fish"])
        return

    header = JSON_PARSE["new_fish_header"]
    body = "\n".join(names_ko)
    if len(header) + len(body) <= MAX_DISCORD_MSG:
        await message.channel.send(header + body)
    else:
        file = discord.File(fp=StringIO(body), filename="new_fish_names.txt")
        await message.author.send(content=header.strip(), file=file)

async def handle_json_input(message: discord.Message, content: str):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(JSON_PARSE["invalid_format"])

    try:
        fish_ids = extract_fish_ids(data)
    except ValueError as e:
        raise ValueError(str(e))

    fish_ids = _ensure_int_list(fish_ids)
    if not fish_ids:
        raise ValueError(JSON_PARSE["non_integer"])

    user_id = message.author.id

    before_list = _ensure_int_list(await select_caught_fish(user_id) or [])
    await upsert_caught_fish(user_id, fish_ids)
    after_list = _ensure_int_list(await select_caught_fish(user_id) or [])

    if not before_list:
        await message.channel.send(JSON_PARSE["first_save"])
        return

    before_set = set(before_list)
    added = [fid for fid in after_list if fid not in before_set]

    if not added:
        await message.channel.send(JSON_PARSE["no_new_fish"])
        return

    await send_new_fish_result(message, added)
