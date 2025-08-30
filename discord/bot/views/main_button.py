import discord
from bot.views.user_select_action import UserSelectView
from config import MAIN_BTN

class mainActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label=MAIN_BTN["merge_button_label"],
        style=discord.ButtonStyle.success,
        custom_id="action:merge_json",
    )
    async def merge_json(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            MAIN_BTN["merge_prompt"],
            view=UserSelectView(interaction.user, mode="merge"),
            ephemeral=True,
        )

    @discord.ui.button(
        label=MAIN_BTN["thread_button_label"],
        style=discord.ButtonStyle.primary,
        custom_id="action:create_thread",
    )
    async def create_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            MAIN_BTN["thread_prompt"],
            view=UserSelectView(interaction.user, mode="thread"),
            ephemeral=True,
        )