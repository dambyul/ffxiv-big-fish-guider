import json
import discord

async def extract_json_text(message: discord.Message) -> str:
    if message.content and message.content.strip():
        text = message.content.strip()
    else:
        text = None
        for att in message.attachments:
            if att.filename.endswith((".json", ".txt")):
                content = await att.read()
                text = content.decode("utf-8").strip()
                break

    if not text:
        raise ValueError("JSON 형식 텍스트나 .json/.txt 파일을 보내주세요.")

    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}")

    return text