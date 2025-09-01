import discord
from discord.ext import commands
from config.env import BOT_TOKEN
from bot.commands import register_commands
from bot.events import register_events

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True
intents.guilds = True

bot = commands.Bot(command_prefix=None, intents=intents)

def run_bot():
    register_events(bot)

    import asyncio
    asyncio.run(register_commands(bot)) 

    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    run_bot()
