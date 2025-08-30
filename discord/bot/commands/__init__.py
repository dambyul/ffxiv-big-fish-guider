# 명령어 등록

from bot.commands.update import register_update_command
from bot.commands.setup import register_setup_command
from bot.commands.fish import register_fish_command

async def register_commands(bot):
    await register_setup_command(bot)
    await register_update_command(bot)
    await register_fish_command(bot)