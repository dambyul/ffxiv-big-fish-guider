import discord
from bot.handlers.json_input import handle_json_input
from bot.utils.message_parse import extract_json_text
from config import DM_UPLOAD

async def handle_dm_message(bot, message: discord.Message):
    try:
        text = await extract_json_text(message)
        await handle_json_input(message, text)
    except ValueError as e:
        await message.channel.send(DM_UPLOAD["error_user"].format(error=e))
    except Exception as e:
        await message.channel.send(DM_UPLOAD["error_unknown"].format(error=e))