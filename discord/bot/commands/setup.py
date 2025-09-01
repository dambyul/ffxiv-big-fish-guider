# bot/commands/setup.py

import discord
from discord import app_commands, Interaction, PermissionOverwrite
from discord.ext.commands import Bot

from db.guild import select_guild_config, upsert_guild_config
from bot.views.main_button import mainActionView
from config import SETUP_COMMAND


async def register_setup_command(bot: Bot):
    @bot.tree.command(
        name=SETUP_COMMAND["name"],
        description=SETUP_COMMAND["description"]
    )
    @app_commands.describe(channel_name=SETUP_COMMAND["arg_channel_name"])
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(interaction: Interaction, channel_name: str):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                SETUP_COMMAND["error_not_in_guild"], ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        row = await select_guild_config(guild.id)

        target_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if target_channel is None:
            overwrites = {
                guild.default_role: PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                ),
                guild.me: PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    send_messages_in_threads=True,
                    create_public_threads=True,
                    create_private_threads=True,
                    manage_messages=True,
                ),
            }
            target_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        if row:
            old_channel = bot.get_channel(row["channel_id"]) or None
            if old_channel is None:
                try:
                    old_channel = await bot.fetch_channel(row["channel_id"])
                except (discord.NotFound, discord.Forbidden):
                    old_channel = None
                except Exception as e:
                    print(SETUP_COMMAND["log_fetch_old_channel_failed"].format(error=e))
                    old_channel = None

            if isinstance(old_channel, discord.TextChannel):
                try:
                    old_message = await old_channel.fetch_message(row["message_id"])
                    await old_message.edit(content=SETUP_COMMAND["guide_message"], view=mainActionView())
                    await upsert_guild_config(guild.id, old_channel.id, old_message.id)
                    await interaction.followup.send(
                        SETUP_COMMAND["success_channel_created"].format(channel_mention=old_channel.mention),
                        ephemeral=True,
                    )
                    return
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(SETUP_COMMAND["log_old_message_delete_failed"].format(error=e))

        perms = target_channel.permissions_for(guild.me)
        needed_ok = (
            perms.view_channel
            and perms.send_messages
            and perms.read_message_history
            and perms.embed_links
            and perms.attach_files
            and perms.send_messages_in_threads
            and perms.create_public_threads
        )
        if not needed_ok:
            try:
                await target_channel.set_permissions(
                    guild.me,
                    view_channel=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    send_messages_in_threads=True,
                    create_public_threads=True,
                    create_private_threads=True,
                    manage_messages=True,
                )
            except discord.Forbidden as e:
                await interaction.followup.send(SETUP_COMMAND["error_missing_perms"], ephemeral=True)
                print(SETUP_COMMAND["log_channel_permission_fix_failed"].format(error=e))
                return
            except Exception as e:
                print(SETUP_COMMAND["log_channel_permission_fix_failed"].format(error=e))
                await interaction.followup.send(SETUP_COMMAND["error_missing_perms"], ephemeral=True)
                return

        try:
            view = mainActionView()
            msg = await target_channel.send(
                content=SETUP_COMMAND["guide_message"],
                view=view
            )
        except Exception as e:
            print(SETUP_COMMAND["log_guide_message_send_failed"].format(error=e))
            await interaction.followup.send(SETUP_COMMAND["error_missing_perms"], ephemeral=True)
            return

        await upsert_guild_config(guild.id, target_channel.id, msg.id)

        await interaction.followup.send(
            SETUP_COMMAND["success_channel_created"].format(
                channel_mention=target_channel.mention
            ),
            ephemeral=True,
        )
