"""Load FinRL and sibling traderbot .env files (secrets stay in env, not logged)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_all_env(project_root: Path | None = None) -> list[Path]:
    root = project_root or Path(__file__).resolve().parents[2]
    loaded: list[Path] = []
    finrl_env = root / ".env"
    if finrl_env.is_file():
        load_dotenv(finrl_env)
        loaded.append(finrl_env)
    traderbot_env = root.parent / "traderbot" / ".env"
    if traderbot_env.is_file():
        load_dotenv(traderbot_env, override=False)
        loaded.append(traderbot_env)
    return loaded
