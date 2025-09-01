import discord
from db.guild import select_guild_config, update_guild_message_id, delete_guild_config
from bot.views.main_button import mainActionView
from config import CHECK_SETUP, SETUP_COMMAND

async def check_setup(bot: discord.Client, guild_id: int):
    guild = bot.get_guild(guild_id)
    if guild is None:
        try:
            await delete_guild_config(guild_id)
        except Exception as e:
            print(CHECK_SETUP["log_guild_config_cleanup_failed"].format(guild_id=guild_id, error=e))
        print(CHECK_SETUP["log_guild_missing"].format(guild_id=guild_id))
        return

    row = await select_guild_config(guild_id)
    if not row:
        print(CHECK_SETUP["log_no_config"].format(guild_id=guild_id))
        return

    channel_id = row["channel_id"]
    message_id = row.get("message_id")

    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            print(CHECK_SETUP["log_channel_missing"].format(channel_id=channel_id))
            return
        except discord.Forbidden:
            print(CHECK_SETUP["log_channel_forbidden"].format(channel_id=channel_id))
            return
        except discord.HTTPException as e:
            print(CHECK_SETUP["log_channel_fetch_failed"].format(channel_id=channel_id, error=e))
            return

    old_msg: discord.Message | None = None
    if message_id:
        try:
            old_msg = await channel.fetch_message(message_id)
        except discord.NotFound:
            old_msg = None
        except discord.Forbidden:
            print(CHECK_SETUP["log_old_message_forbidden"].format(channel_id=channel_id, message_id=message_id))
            return
        except discord.HTTPException as e:
            print(CHECK_SETUP["log_old_message_fetch_failed"].format(channel_id=channel_id, message_id=message_id, error=e))

    if old_msg:
        try:
            await old_msg.edit(
                content=SETUP_COMMAND["guide_message"],
                view=mainActionView()
            )
            await update_guild_message_id(guild_id, old_msg.id)
            print(CHECK_SETUP["log_guide_message_updated"].format(channel_id=channel_id, message_id=old_msg.id))
            return
        except discord.Forbidden:
            print(CHECK_SETUP["log_old_message_edit_forbidden"].format(channel_id=channel_id, message_id=old_msg.id))
            return
        except discord.HTTPException as e:
            print(CHECK_SETUP["log_old_message_edit_failed"].format(channel_id=channel_id, message_id=old_msg.id, error=e))
            try:
                await old_msg.delete()
            except Exception as de:
                print(CHECK_SETUP["log_old_message_delete_failed"].format(error=de))

    try:
        new_msg = await channel.send(
            content=SETUP_COMMAND["guide_message"],
            view=mainActionView()
        )
        await update_guild_message_id(guild_id, new_msg.id)
        print(CHECK_SETUP["log_guide_message_sent"].format(channel_id=channel_id, message_id=new_msg.id))
    except discord.Forbidden:
        print(CHECK_SETUP["log_guide_message_send_forbidden"].format(channel_id=channel_id))
    except discord.HTTPException as e:
        print(CHECK_SETUP["log_guide_message_send_failed"].format(error=e))
