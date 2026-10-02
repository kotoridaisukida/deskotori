"""把窗口放进桌面四个角。纯计算，不依赖界面库。"""

CORNERS = ("tl", "tr", "bl", "br")

# Clockwise quarter-turns that put the picture's bottom-left right angle
# onto that screen corner, with the two cut edges along the screen edges.
QUARTER_TURNS = {"tl": 1, "tr": 2, "bl": 0, "br": 3}


def quarter_turns(corner: str) -> int:
    if corner not in QUARTER_TURNS:
        raise ValueError(f"unknown corner: {corner}")
    return QUARTER_TURNS[corner]


def corner_position(
    corner: str,
    area: tuple[int, int, int, int],
    win_w: int,
    win_h: int,
) -> tuple[int, int]:
    """Put the window flush into a corner of ``area`` (x, y, width, height)."""
    if corner not in CORNERS:
        raise ValueError(f"unknown corner: {corner}")
    ax, ay, aw, ah = area
    if corner == "tl":
        return ax, ay
    if corner == "tr":
        return ax + aw - win_w, ay
    if corner == "bl":
        return ax, ay + ah - win_h
    return ax + aw - win_w, ay + ah - win_h
