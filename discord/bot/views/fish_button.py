from typing import Optional, Literal, Any
import discord

from bot.views.fish_embed import create_fish_embed, _normalize_lang3
from db.user import update_user_prefer_lang, append_caught_fish

Lang3 = Literal["KO", "EN", "JA"]


class FishActionView(discord.ui.View):
    def __init__(
        self,
        fish: dict,
        bait_path: Optional[list] = None,
        predators: Optional[list] = None,
        prefer_lang: Optional[Any] = "KO",
        timeout: Optional[float] = 600.0,
    ):
        super().__init__(timeout=timeout)
        self.fish = fish
        self.bait_path = bait_path or []
        self.predators = predators or []
        self.lang: Lang3 = _normalize_lang3(prefer_lang, default="KO")

        self.message: Optional[discord.Message] = None

        if self.lang == "KO":
            self.remove_item(self.btn_lang_ko)
        elif self.lang == "EN":
            self.remove_item(self.btn_lang_en)
        else:  # JA
            self.remove_item(self.btn_lang_ja)

    async def on_timeout(self) -> None:
        """timeout 시 버튼/임베드 제거"""
        try:
            if self.message:
                await self.message.delete()
        except Exception:
            pass
        finally:
            self.stop()

    async def _edit_message(self, interaction: discord.Interaction, *, embed: discord.Embed, view: "FishActionView"):
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=view)
            try:
                msg = await interaction.original_response()
                view.message = msg
            except Exception:
                pass
        else:
            await interaction.message.edit(embed=embed, view=view)
            view.message = interaction.message

    async def _switch_lang(self, interaction: discord.Interaction, new_lang: Lang3, persist: bool):
        embed = create_fish_embed(
            self.fish,
            bait_path=self.bait_path,
            predators=self.predators,
            prefer_lang=new_lang,
        )
        new_view = FishActionView(
            fish=self.fish,
            bait_path=self.bait_path,
            predators=self.predators,
            prefer_lang=new_lang,
            timeout=self.timeout,
        )
        await self._edit_message(interaction, embed=embed, view=new_view)

        if persist:
            try:
                await update_user_prefer_lang(interaction.user.id, new_lang)
            except Exception:
                pass

    @discord.ui.button(label="한국어", style=discord.ButtonStyle.primary, custom_id="fish:lang_ko")
    async def btn_lang_ko(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_lang(interaction, "KO", persist=True)

    @discord.ui.button(label="영어", style=discord.ButtonStyle.primary, custom_id="fish:lang_en")
    async def btn_lang_en(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_lang(interaction, "EN", persist=True)

    @discord.ui.button(label="일본어", style=discord.ButtonStyle.primary, custom_id="fish:lang_ja")
    async def btn_lang_ja(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._switch_lang(interaction, "JA", persist=True)

    @discord.ui.button(label="낚음", style=discord.ButtonStyle.success, custom_id="fish:caught")
    async def btn_caught(self, interaction: discord.Interaction, button: discord.ui.Button):
        fish_id = int(self.fish["id"])
        try:
            await append_caught_fish(interaction.user.id, fish_id)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"✅ '{self.fish.get('name_ko','')}'을(를) 내 잡은 물고기에 추가했어요.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"✅ '{self.fish.get('name_ko','')}'을(를) 내 잡은 물고기에 추가했어요.",
                    ephemeral=True
                )
        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ 추가 실패: {e}", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send(f"❌ 추가 실패: {e}", ephemeral=True)
