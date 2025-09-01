from discord.ext import commands
from .on_ready import bind_on_ready
from .on_message import bind_on_message

def register_events(bot: commands.Bot):
    bind_on_ready(bot)
    bind_on_message(bot)