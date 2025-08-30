import json
from datetime import datetime, timedelta
from typing import Optional, Any, Iterable

import discord
from config import KST


# -------- 공통 유틸 --------
def _normalize_lang3(v: Any, default: str = "KO") -> str:
    if isinstance(v, (list, tuple, set)):
        v = next(iter(v), "")
    lang = (str(v) if v is not None else "").upper()
    return lang if lang in ("KO", "EN", "JA") else default

def _normalize_patch(patch: Any) -> str:
    if patch is None:
        return ""

    def _short(v: float) -> str:
        s = str(v)
        # '3.0' -> '3', '2.40' -> '2.4'
        if s.endswith(".0"):
            return s[:-2]
        return s.rstrip("0").rstrip(".")

    try:
        val = float(str(patch))
    except Exception:
        # 숫자 변환 실패 시 원문 반환
        return str(patch)

    if 2.0 <= val < 3.0:
        return "신생"
    if 3.0 <= val < 4.0:
        return "창천"
    if 4.0 <= val < 5.0:
        return "홍련"
    if 5.0 <= val < 6.0:
        return "칠흑"
    if 6.0 <= val < 7.0:
        return "효월"
    if 7.0 <= val < 8.0:
        return "황금"

    # 8.x 또는 그 외 값은 기존 로직 유지(숫자 표시)
    return _short(val)

def _parse_ts(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        dt = v
    else:
        try:
            dt = datetime.fromisoformat(str(v))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt

def _rel_day_label(dt: datetime, now: datetime) -> Optional[str]:
    d0 = now.date()
    d = (dt.astimezone(KST) if dt.tzinfo else dt.replace(tzinfo=KST)).date()
    if d == d0:
        return "오늘"
    if d == d0 + timedelta(days=1):
        return "내일"
    if d == d0 + timedelta(days=2):
        return "모레"
    return None

def _fmt_rel_kor(dt: datetime, now: datetime) -> str:
    if dt is None:
        return "?"
    dt = dt.astimezone(KST) if dt.tzinfo else dt.replace(tzinfo=KST)
    tag = _rel_day_label(dt, now)
    if tag == "오늘":
        return f"{tag} {dt:%H:%M:%S}"
    if tag in ("내일", "모레"):
        return f"{tag} {dt:%H시 %M분}"
    return f"{dt.month}월 {dt.day}일 {dt:%H시 %M분}"

def _fmt_duration_from_timefield(v: Any) -> Optional[str]:
    if v is None:
        return None
    h = m = s = 0
    try:
        if hasattr(v, "hour") and hasattr(v, "minute"):
            h, m, s = int(v.hour), int(v.minute), int(getattr(v, "second", 0))
        else:
            parts = str(v).strip().split(":")
            if len(parts) == 2:
                h, m = int(parts[0]), int(parts[1])
            elif len(parts) >= 3:
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                return None
    except Exception:
        return None
    chunks = []
    if h: chunks.append(f"{h}시간")
    if m: chunks.append(f"{m}분")
    if s or not chunks: chunks.append(f"{s}초")
    return " ".join(chunks)

def _fmt_seconds_label(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        x = float(v)
    except Exception:
        return None
    if abs(x - int(x)) < 1e-9:
        return f"{int(x)}초"
    return f"{x:.1f}초"

def _coerce_timeline(raw: Any) -> list[tuple[datetime, str]]:
    if raw is None:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []
    out: list[tuple[datetime, str]] = []
    for item in (data or []):
        if not isinstance(item, (list, tuple)) or len(item) < 1:
            continue
        ts = _parse_ts(item[0])
        if not ts:
            continue
        dur = str(item[1]) if len(item) > 1 and item[1] is not None else ""
        out.append((ts, dur))
    return out

def _fmt_day_time_line(dt: datetime, dur_text: str, now: datetime) -> str:
    dt = dt.astimezone(KST) if dt.tzinfo else dt.replace(tzinfo=KST)
    tag = _rel_day_label(dt, now)
    day_label = tag if tag else f"{dt.month}월 {dt.day}일"
    return f"  {day_label} {dt.hour}시 {dt.minute:02d}분 ({dur_text})" if dur_text else f"  {day_label} {dt.hour}시 {dt.minute:02d}분"

def _fmt_predator_uptime(
    now: datetime,
    start: Optional[datetime],
    end: Optional[datetime],
    duration_text: Optional[str] = None,
) -> str:
    if start and end:
        if start <= now <= end:
            return f"{_fmt_rel_kor(end, now)} 까지"
        return f"{_fmt_rel_kor(start, now)}부터 {duration_text}간" if duration_text else f"{_fmt_rel_kor(start, now)}부터"
    if end:
        return f"{_fmt_rel_kor(end, now)} 까지"
    return "-"

def _pick(obj: dict, key_base: str, lang3: str) -> str:
    suffix = {"KO": "ko", "EN": "en", "JA": "ja"}[lang3]
    return obj.get(f"{key_base}_{suffix}", "") or ""

SEP = "≻─── ⋆✩⋆ ───≺"
def _append_bait_path(block: Iterable[dict], name_key: str,
                      fishing_steps: list[str],
                      bite_time_lines: list[str],
                      bite_lines: list[str]) -> bool:
    if not block:
        return False
    steps = list(block)
    for idx, step in enumerate(steps):
        fishing_steps.append(step.get(name_key, "") or "-")

        bmin = _fmt_seconds_label(step.get("bite_min"))
        bmax = _fmt_seconds_label(step.get("bite_max"))
        bavg = _fmt_seconds_label(step.get("bite_avg"))
        if bmin and bmax and bavg:
            bite_time_lines.append(f"{bmin} ~ {bmax} (평균 {bavg})")
        elif bmin and bmax:
            bite_time_lines.append(f"{bmin} ~ {bmax}")
        elif bavg:
            bite_time_lines.append(f"평균 {bavg}")
        elif bmin or bmax:
            bite_time_lines.append(bmin or bmax)
        else:
            bite_time_lines.append("-")

        if step.get("tug") or step.get("hookset"):
            bite_lines.append(f"{step.get('tug','-')} / {step.get('hookset','-')}")
        else:
            bite_lines.append("-")

        is_last = (idx == len(steps) - 1)
        next_id = steps[idx + 1].get("fish_id") if not is_last else None
        if not is_last and step.get("fish_id") != next_id:
            fishing_steps.append(SEP)
            bite_time_lines.append(SEP)
            bite_lines.append(SEP)
    return True

def create_fish_embed(
    fish: dict,
    bait_path: Optional[Iterable[dict]] = None,
    prefer_lang: Optional[Any] = None,
    predators: Optional[Iterable[dict]] = None,
) -> discord.Embed:
    now = datetime.now(KST)
    lang3 = _normalize_lang3(prefer_lang, default="KO")

    title = _pick(fish, "name", lang3)
    embed = discord.Embed(
        title=title,
        url=f"https://ffxivteamcraft.com/db/ko/item/{fish.get('id')}",
        color=0x80DBFF,
        timestamp=now,
    )

    patch = _normalize_patch(fish.get("patch"))
    if patch:
        if fish.get("king_fish") is True:
            embed.description = f"{patch} 터주왕"
        elif fish.get("big_fish") is True:
            embed.description = f"{patch} 터주"
        else:
            embed.description = f"{patch} 물고기"

    zone = _pick(fish, "zone_name", lang3)
    spot = _pick(fish, "spot_name", lang3)
    author_name = f"{zone} - {spot}".strip(" -")
    if fish.get("spot_id"):
        embed.set_author(name=author_name or " ",
                         url=f"https://ffxivteamcraft.com/db/ko/fishing-spot/{fish['spot_id']}")
    else:
        embed.set_author(name=author_name or " ")

    # 출현율 / 미끼 / 직감
    if fish.get("uptime_percent") is not None:
        embed.add_field(name="💫 출현율", value=f"{fish['uptime_percent']}%", inline=True)

    bait_key = {"KO": "required_bait_ko", "EN": "required_bait_en", "JA": "required_bait_ja"}[lang3]
    raw = fish.get(bait_key)
    try:
        bait_list = json.loads(raw) if isinstance(raw, str) else (raw or [])
    except Exception:
        bait_list = []
    if bait_list:
        embed.add_field(name="🪱 미끼", value="\n".join(map(str, bait_list)), inline=True)

    it = fish.get("intuition_time")
    if it and str(it) != "00:00:00":
        embed.add_field(name="🩵 직감", value=str(it), inline=True)

    # 이번 출현
    current_start = _parse_ts(fish.get("current_start"))
    current_end   = _parse_ts(fish.get("current_end"))
    if fish.get("uptime_percent") == 100:
        embed.add_field(name="▶️ 이번 출현", value="상시 출현", inline=False)
    else:
        if current_start and current_end:
            if current_start <= now <= current_end:
                embed.add_field(name="▶️ 이번 출현",
                                value=f"{_fmt_rel_kor(current_end, now)} 까지",
                                inline=False)
            else:
                dur = _fmt_duration_from_timefield(fish.get("duration"))
                text = f"{_fmt_rel_kor(current_start, now)}부터 {dur}간" if dur else \
                       f"{_fmt_rel_kor(current_start, now)} ~ {_fmt_rel_kor(current_end, now)}"
                embed.add_field(name="▶️ 이번 출현", value=text, inline=False)
        elif current_end:
            embed.add_field(name="▶️ 이번 출현", value=f"{_fmt_rel_kor(current_end, now)} 까지", inline=False)

    # 다음 출현(타임라인)
    timeline_list = _coerce_timeline(fish.get("uptime_timeline"))
    if timeline_list and fish.get("uptime_percent") != 100:
        lines: list[str] = []
        for ts, dur in timeline_list:
            lines.append(_fmt_day_time_line(ts, str(dur), now))
        if lines:
            embed.add_field(name="⏭️ 다음 출현", value="\n".join(lines), inline=False)

    # 직감 조건 / 마리 수 / 이번 출현
    if it and str(it) != "00:00:00":
        if predators is None:
            predators = fish.get("predators") or []
            if isinstance(predators, str):
                try:
                    predators = json.loads(predators)
                except Exception:
                    predators = []
        predators = list(predators or [])
        if predators:
            name_lines, count_lines, uptime_lines = [], [], []
            for p in predators:
                p_name = (
                    p.get({"KO": "name_ko", "EN": "name_en", "JA": "name_ja"}[lang3])
                    or p.get("name_ko")
                    or str(p.get("predator_id", ""))
                )
                name_lines.append(p_name)

                count = p.get("required_count")
                count_lines.append(str(count) if count is not None else "?")

                p_start = _parse_ts(p.get("current_start"))
                p_end   = _parse_ts(p.get("current_end"))
                dur_txt = _fmt_duration_from_timefield(p.get("duration"))
                uptime_lines.append(_fmt_predator_uptime(now, p_start, p_end, dur_txt))

            embed.add_field(name="🔥 직감 조건", value="\n".join(name_lines), inline=True)
            embed.add_field(name="마리 수",        value="\n".join(count_lines), inline=True)
            embed.add_field(name="▶️ 이번 출현",   value="\n".join(uptime_lines), inline=True)

    # 낚시법 / 입질시간 / 입질
    name_key = {"KO": "name_ko", "EN": "name_en", "JA": "name_ja"}[lang3]
    fishing_steps, bite_time_lines, bite_lines = [], [], []
    any_added = False

    if bait_path:
        any_added |= _append_bait_path(bait_path, name_key, fishing_steps, bite_time_lines, bite_lines)

    if any_added and any(s.strip() for s in fishing_steps):
        embed.add_field(name="🎣 낚시법", value="\n".join(fishing_steps), inline=True)
        embed.add_field(name="입질",   value="\n".join(bite_lines), inline=True)
        embed.add_field(name="입질시간", value="\n".join(bite_time_lines), inline=True)

    icon_url = fish.get("icon_url")
    if icon_url:
        embed.set_thumbnail(url=icon_url)
    embed.set_footer(text=f"Fish ID: {fish.get('id')}")
    return embed
