import discord
import asyncio
from db.user import select_upload_thread, delete_upload_thread
from bot.handlers.json_input import handle_json_input
from bot.utils.message_parse import extract_json_text
from config import THREAD_UPLOAD

async def handle_thread_message(bot, message: discord.Message):
    guild_id = message.guild.id
    user_id = message.author.id
    thread_id = message.channel.id

    current_thread = await select_upload_thread(guild_id, user_id)
    if current_thread != thread_id:
        pass

    try:
        text = await extract_json_text(message)
        await handle_json_input(message, text)

        await message.channel.send(THREAD_UPLOAD["success_and_delete"])
        await asyncio.sleep(30)
        await message.channel.delete()
        await delete_upload_thread(guild_id, user_id)

    except ValueError as e:
        await message.channel.send(THREAD_UPLOAD["error_user"].format(error=e))
    except Exception as e:
        await message.channel.send(THREAD_UPLOAD["error_unknown"].format(error=e))