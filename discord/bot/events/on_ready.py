import discord
from discord.ext import commands
#from core.updater import resume_all_updaters
from bot.utils.check_setup import check_setup
from db.guild import select_all_guild_ids

def bind_on_ready(bot: commands.Bot):
    @bot.event
    async def on_ready():
        print(f"{bot.user} 봇 가동 (ID: {bot.user.id})")
        synced = await bot.tree.sync()
        print(f"🔧 Synced {len(synced)} application commands.")
        
        from bot.views.main_button import mainActionView
        bot.add_view(mainActionView())

        guild_ids = await select_all_guild_ids()
        for gid in guild_ids:
            await check_setup(bot, gid)

        #스레드 갱신 코드
        #await resume_all_updaters(bot)