"""
Traderbot platform bridge — paths and env shared with ../traderbot.
"""

from __future__ import annotations

import os
from pathlib import Path


def traderbot_root() -> Path:
    env = os.environ.get("TRADERBOT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    sibling = Path(__file__).resolve().parents[2].parent / "traderbot"
    return sibling.resolve()


def load_platform_env() -> None:
    from src.config.env_loader import load_all_env

    load_all_env(Path(__file__).resolve().parents[2])
