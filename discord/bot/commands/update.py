import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot

from db.user import select_upload_thread, insert_upload_thread, delete_upload_thread
from db.guild import select_guild_config
from config.text import UPDATE_COMMAND

async def register_update_command(bot: Bot):
    @bot.tree.command(
        name=UPDATE_COMMAND["name"],
        description=UPDATE_COMMAND["description"]
    )
    @app_commands.guild_only()
    async def update_command(interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send(UPDATE_COMMAND["error_guild_only"], ephemeral=True)
            return

        cfg = await select_guild_config(guild.id)
        if not cfg:
            await interaction.followup.send(UPDATE_COMMAND["error_setup_required"], ephemeral=True)
            return

        setup_channel_id = cfg["channel_id"]

        setup_channel = bot.get_channel(setup_channel_id)
        if setup_channel is None:
            try:
                setup_channel = await bot.fetch_channel(setup_channel_id)
            except discord.NotFound:
                await interaction.followup.send(UPDATE_COMMAND["error_setup_required"], ephemeral=True)
                return
            except discord.Forbidden:
                await interaction.followup.send(UPDATE_COMMAND["error_cannot_access_channel"], ephemeral=True)
                return
            except Exception as e:
                print(UPDATE_COMMAND["log_fetch_channel_failed"].format(error=e))
                await interaction.followup.send(UPDATE_COMMAND["error_unknown"], ephemeral=True)
                return

        if not isinstance(setup_channel, discord.TextChannel):
            await interaction.followup.send(UPDATE_COMMAND["error_wrong_setup_channel_type"], ephemeral=True)
            return

        perms = setup_channel.permissions_for(guild.me)
        if not (perms.view_channel and perms.send_messages and perms.create_public_threads and perms.send_messages_in_threads):
            await interaction.followup.send(UPDATE_COMMAND["error_missing_perms"], ephemeral=True)
            return

        user = interaction.user
        guild_id = guild.id

        existing_thread_id = await select_upload_thread(guild_id, user.id)
        if existing_thread_id:
            try:
                old_thread = await bot.fetch_channel(existing_thread_id)
                await old_thread.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
            except Exception as e:
                print(UPDATE_COMMAND["log_old_thread_delete_failed"].format(error=e))
            finally:
                await delete_upload_thread(guild_id, user.id)

        try:
            thread = await setup_channel.create_thread(
                name=f"{user.display_name}-update",
                type=discord.ChannelType.public_thread,
                invitable=False
            )
        except discord.Forbidden:
            await interaction.followup.send(UPDATE_COMMAND["error_missing_perms"], ephemeral=True)
            return
        except Exception as e:
            print(UPDATE_COMMAND["log_create_thread_failed"].format(error=e))
            await interaction.followup.send(UPDATE_COMMAND["error_unknown"], ephemeral=True)
            return

        await insert_upload_thread(guild_id, user.id, thread.id)

        await thread.send(UPDATE_COMMAND["thread_message_prompt"].format(mention=user.mention))

        await interaction.followup.send(
            UPDATE_COMMAND["success_thread_created"].format(channel_mention=setup_channel.mention),
            ephemeral=True
        )
