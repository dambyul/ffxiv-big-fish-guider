import discord
import json
import tempfile
from typing import List

from db.user import select_caught_fish
from db.list import select_users_caught_fish
from db.thread import select_duplicated_thread, upsert_thread
from config import USER_SELECT, USER_SELECT_MERGE, USER_SELECT_THREAD

class UserSelectView(discord.ui.View):
    def __init__(self, request_user: discord.User, mode: str):
        super().__init__(timeout=USER_SELECT.get("timeout_sec", 60))
        self.request_user = request_user
        self.mode = mode

        self.user_select = discord.ui.UserSelect(
            placeholder=USER_SELECT.get("placeholder", USER_SELECT.get("prompt", "")),
            min_values=USER_SELECT.get("min_values", 2),
            max_values=USER_SELECT.get("max_values", 10),
        )
        self.user_select.callback = self.process_selection
        self.add_item(self.user_select)

    async def process_selection(self, interaction: discord.Interaction):
        selected_users: List[discord.User] = self.user_select.values

        if self.mode == "merge":
            await self._handle_merge(interaction, selected_users)
        elif self.mode == "thread":
            await self._handle_thread(interaction, selected_users)

    async def _handle_merge(self, interaction: discord.Interaction, selected_users: List[discord.User]) -> List[int]:
        user_ids = [u.id for u in selected_users]

        union_fish: List[int] = await select_users_caught_fish(user_ids)

        missing_users: List[str] = []
        for user in selected_users:
            fish = await select_caught_fish(user.id)
            if not fish:
                missing_users.append(user.name)

        if not union_fish:
            if interaction.response.is_done():
                await interaction.followup.send(
                    content=USER_SELECT_MERGE["no_config"], ephemeral=True
                )
            else:
                await interaction.response.edit_message(
                    content=USER_SELECT_MERGE["no_config"], view=None
                )
            return []

        with tempfile.NamedTemporaryFile(
            mode="w+",
            suffix=USER_SELECT_MERGE.get("tempfile_suffix", ".json"),
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(sorted(union_fish), f, ensure_ascii=False)
            temp_path = f.name

        reply_message = USER_SELECT_MERGE["reply_done"]
        if missing_users:
            reply_message += "\n" + USER_SELECT_MERGE["reply_missing_users"].format(
                users=", ".join(missing_users)
            )

        if interaction.response.is_done():
            await interaction.followup.send(
                content=reply_message,
                file=discord.File(
                    temp_path,
                    filename=USER_SELECT_MERGE.get("tempfile_filename", "union_fish.json"),
                ),
                ephemeral=True,  
            )
        else:
            await interaction.response.edit_message(
                content=reply_message,
                attachments=[
                    discord.File(
                        temp_path,
                        filename=USER_SELECT_MERGE.get("tempfile_filename", "union_fish.json"),
                    )
                ],
                view=None,
            )

        return union_fish

    async def _handle_thread(self, interaction: discord.Interaction, selected_users: List[discord.User]):
        channel = interaction.channel

        user_ids = [u.id for u in selected_users]
        existing_thread_id = await select_duplicated_thread(channel.id, user_ids)

        if existing_thread_id:
            try:
                thread = await interaction.client.fetch_channel(existing_thread_id)
                if interaction.response.is_done():
                    await interaction.followup.send(
                        content=USER_SELECT_THREAD["duplicate_found"].format(url=thread.jump_url),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.edit_message(
                        content=USER_SELECT_THREAD["duplicate_found"].format(url=thread.jump_url),
                        view=None,
                    )
                return
            except discord.NotFound:
                pass

        user_names = [user.display_name for user in selected_users]
        thread_name = USER_SELECT_THREAD.get("name_sep", " / ").join(user_names)

        thread = await channel.create_thread(
            name=thread_name[:100],
            type=discord.ChannelType.public_thread,
            auto_archive_duration=USER_SELECT_THREAD.get("auto_archive_min", 60),
            reason=USER_SELECT_THREAD["created_reason"].format(user=interaction.user.name),
        )
        
        await upsert_thread(channel.id, user_ids, thread.id, None)

        await thread.send(
            USER_SELECT_THREAD["thread_head"].format(
                mention=interaction.user.mention,
                mentions=", ".join(user.mention for user in selected_users),
            )
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                content=USER_SELECT_THREAD["created_notice_ephemeral"], ephemeral=True
            )
        else:
            await interaction.response.edit_message(
                content=USER_SELECT_THREAD["created_notice_ephemeral"], view=None
            )
