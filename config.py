from __future__ import annotations

import json
import os
from typing import Any, Dict

CONFIG_PATH = "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "update_ms": 500,
    "small_jump": 5,
    "large_jump": 20,
    "keys": {
        "play_pause": "<space>",
        "back_small": "<Left>",
        "fwd_small": "<Right>",
        "back_large": "<Shift-Left>",
        "fwd_large": "<Shift-Right>",
    },
}


def _deep_update(base: Dict[str, Any], updates: Dict[str, Any]) -> None:
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


def load_config() -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    cfg["keys"] = cfg["keys"].copy()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        _deep_update(cfg, loaded)
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
