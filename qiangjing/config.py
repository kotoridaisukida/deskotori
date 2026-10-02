"""把刷新时间、大小和暂停状态记在本机配置里。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


INTERVAL_MIN = 1
INTERVAL_MAX = 300
SIZE_MIN = 160
SIZE_MAX = 520


@dataclass
class PetConfig:
    interval_sec: int = 10
    size: int = 300
    peek: float = 0.0
    paused: bool = False

    def normalized(self) -> PetConfig:
        return PetConfig(
            interval_sec=_clamp_int(self.interval_sec, INTERVAL_MIN, INTERVAL_MAX, 10),
            size=_clamp_int(self.size, SIZE_MIN, SIZE_MAX, 300),
            peek=_clamp_float(self.peek),
            paused=self.paused if isinstance(self.paused, bool) else False,
        )


class ConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path if path is not None else default_config_path()

    def load(self) -> PetConfig:
        if not self.path.exists():
            return PetConfig()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return PetConfig()
        if not isinstance(data, dict):
            return PetConfig()
        config = PetConfig()
        if "interval_sec" in data:
            config.interval_sec = data["interval_sec"]
        if "size" in data:
            config.size = data["size"]
        if "peek" in data:
            config.peek = data["peek"]
        if "paused" in data and isinstance(data["paused"], bool):
            config.paused = data["paused"]
        return config.normalized()

    def save(self, config: PetConfig) -> PetConfig:
        config = config.normalized()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(config)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.path)
        return config


def default_config_path() -> Path:
    override = os.environ.get("QIANGJING_CONFIG")
    if override:
        return Path(override)
    custom = os.environ.get("XDG_CONFIG_HOME")
    base = Path(custom) if custom else Path.home() / ".config"
    return base / "qiangjing-niao" / "config.json"


def _clamp_int(value, low: int, high: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def _clamp_float(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number < 0:
        return 0.0
    if number > 1:
        return 1.0
    return number
