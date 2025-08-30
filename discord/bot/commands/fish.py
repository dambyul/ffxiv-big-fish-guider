import asyncio
import json
import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot

from db.detail import select_fish_by_search, select_bait_by_fish_id
from bot.views.fish_embed import create_fish_embed
from bot.views.fish_button import FishActionView
from config import FISH_COMMAND


async def register_fish_command(bot: Bot):
    @bot.tree.command(
        name=FISH_COMMAND["name"],
        description=FISH_COMMAND["description"],
    )
    @app_commands.describe(name=FISH_COMMAND["arg_name"])
    async def fish_command(interaction: Interaction, name: str):
        await interaction.response.defer()

        fish = await select_fish_by_search(name)
        if not fish:
            await interaction.followup.send(FISH_COMMAND["not_found"])
            return

        base_path = await select_bait_by_fish_id(fish["id"]) or []

        predators = fish.get("predators") or []
        if isinstance(predators, str):
            try:
                predators = json.loads(predators)
            except Exception:
                predators = []
        predators = list(predators or [])

        merged_bait_path: list[dict] = []

        for p in predators:
            p_path = p.get("bait_path") or p.get("path") or p.get("steps")
            if isinstance(p_path, list) and p_path:
                merged_bait_path.extend([step for step in p_path if isinstance(step, dict)])

        id_to_predator = {}
        fetch_ids = []
        for p in predators:
            has_path = isinstance(p.get("bait_path") or p.get("path") or p.get("steps"), list)
            if has_path:
                continue
            raw_id = p.get("predator_id", p.get("id", p.get("fish_id")))
            try:
                pid = int(raw_id) if raw_id is not None else None
            except Exception:
                pid = None
            if pid:
                id_to_predator[pid] = p
                fetch_ids.append(pid)

        if fetch_ids:
            results = await asyncio.gather(
                *(select_bait_by_fish_id(pid) for pid in fetch_ids),
                return_exceptions=True
            )
            for pid, res in zip(fetch_ids, results):
                if isinstance(res, Exception):
                    continue
                path = res or []
                id_to_predator[pid]["bait_path"] = path
                merged_bait_path.extend([step for step in path if isinstance(step, dict)])

        if base_path:
            merged_bait_path.extend([step for step in base_path if isinstance(step, dict)])

        prefer_lang = "KO"

        embed = create_fish_embed(
            fish,
            bait_path=merged_bait_path,   # 포식자 → 대상 물고기 순서로 병합된 경로
            predators=predators,
            prefer_lang=prefer_lang,
        )
        view = FishActionView(
            fish=fish,
            bait_path=merged_bait_path,
            predators=predators,
            prefer_lang=prefer_lang,
            timeout=600.0,
        )

        msg = await interaction.followup.send(embed=embed, view=view)
        view.message = msg
