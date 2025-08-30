import discord
from discord.ext import commands
from bot.handlers.thread_input import handle_thread_message
from bot.handlers.dm_input import handle_dm_message

def bind_on_message(bot: commands.Bot):
    @bot.event
    async def on_message(message: discord.Message):
        if message.author == bot.user:
            return

        if isinstance(message.channel, discord.Thread) and message.guild:
            await handle_thread_message(bot, message)
            return

        if isinstance(message.channel, discord.DMChannel):
            await handle_dm_message(bot, message)
            return