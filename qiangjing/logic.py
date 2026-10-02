"""换角和倒计时文案。"""

import random

from qiangjing.geometry import CORNERS

CORNER_LABELS = {
    "tl": "左上角",
    "tr": "右上角",
    "bl": "左下角",
    "br": "右下角",
}

CORNER_SHORT = {
    "tl": "左上",
    "tr": "右上",
    "bl": "左下",
    "br": "右下",
}


def next_corner(current: str, rng: random.Random) -> str:
    """Pick a different corner so a refresh is always visible."""
    choices = [corner for corner in CORNERS if corner != current]
    if not choices:
        choices = list(CORNERS)
    return rng.choice(choices)


def format_seconds(total: int) -> str:
    total = max(0, int(total))
    if total >= 60:
        minutes, seconds = divmod(total, 60)
        if seconds == 0:
            return f"{minutes} 分钟"
        return f"{minutes} 分 {seconds} 秒"
    return f"{total} 秒"


def describe_status(
    corner: str,
    *,
    paused: bool,
    phase: str,
    remaining_ms: int,
) -> tuple[str, str]:
    """Return status text and a tone of ``green`` or ``amber``."""
    label = CORNER_LABELS.get(corner, "桌面上")
    if paused:
        return f"{label} · 已暂停", "amber"
    if phase == "waiting":
        return f"{label} · 准备出发", "green"
    if phase != "idle":
        return f"{label} · 正在出现", "green"
    if remaining_ms < 0:
        return f"{label} · 马上换角", "green"
    seconds = (remaining_ms + 999) // 1000
    if seconds <= 0:
        return f"{label} · 马上换角", "green"
    return f"{label} · {format_seconds(seconds)}后换角", "green"
