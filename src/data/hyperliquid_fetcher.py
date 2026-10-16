"""
Hyperliquid perp OHLCV (1m, 5m, etc.) via the public Info API.
"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

HYPERLIQUID_RESOLUTIONS = ("1", "5", "15", "30", "60", "240", "D")

_RESOLUTION_TO_INTERVAL: dict[str, str] = {
    "1": "1m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "1h",
    "240": "4h",
    "D": "1d",
}

_RESOLUTION_BAR_SECONDS: dict[str, int] = {
    "1": 60,
    "5": 5 * 60,
    "15": 15 * 60,
    "30": 30 * 60,
    "60": 60 * 60,
    "240": 4 * 60 * 60,
    "D": 24 * 60 * 60,
}

HYPERLIQUID_PERP_TAKER_FEE = 0.00045
CANDLE_REQUEST_DELAY_SECONDS = 0.2


@lru_cache(maxsize=1)
def _info_client():
    from hyperliquid.info import Info
    from hyperliquid.utils import constants

    return Info(constants.MAINNET_API_URL, skip_ws=True)


def hyperliquid_interval(resolution: str) -> str:
    interval = _RESOLUTION_TO_INTERVAL.get(str(resolution))
    if interval is None:
        raise ValueError(
            f"Hyperliquid resolution must be one of {HYPERLIQUID_RESOLUTIONS} (got {resolution!r})"
        )
    return interval


def _bar_duration_seconds(resolution: str) -> int:
    seconds = _RESOLUTION_BAR_SECONDS.get(str(resolution))
    if seconds is None:
        raise ValueError(f"unsupported Hyperliquid resolution: {resolution!r}")
    return seconds


def _normalize_candle(candle: dict[str, Any], *, coin: str, resolution: str) -> dict[str, Any]:
    open_unix_seconds = int(int(candle["t"]) / 1000)
    return {
        "symbol": f"{coin.upper()}USDT",
        "resolution": str(resolution),
        "timestamp": open_unix_seconds,
        "open": float(candle["o"]),
        "high": float(candle["h"]),
        "low": float(candle["l"]),
        "close": float(candle["c"]),
        "volume": float(candle.get("v") or 0),
    }


def _trim_forming_candle(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bars = sorted(bars, key=lambda row: row["timestamp"])
    if len(bars) >= 2:
        return bars[:-1]
    return bars


def fetch_hyperliquid_recent_closed_bars(
    *,
    coin: str,
    resolution: str,
    max_bars: int = 500,
) -> list[dict[str, Any]]:
    if max_bars < 1:
        return []
    symbol = coin.strip().upper()
    interval = hyperliquid_interval(resolution)
    bar_seconds = _bar_duration_seconds(resolution)
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (max_bars + 2) * bar_seconds * 1000
    candles = _info_client().candles_snapshot(symbol, interval, start_ms, end_ms)
    if not candles:
        return []
    bars = [_normalize_candle(row, coin=symbol, resolution=resolution) for row in candles]
    closed = _trim_forming_candle(bars)
    return closed[-max_bars:]


def bars_to_ohlcv_frame(bars: list[dict[str, Any]]) -> pd.DataFrame:
    if not bars:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(bars)
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def save_bars_csv(bars: list[dict[str, Any]], path: Path) -> Path:
    """Write OHLCV compatible with traderbot ``load_bars_csv`` (timestamp + resolution)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    resolution = str(bars[0].get("resolution", "1")) if bars else "1"
    rows = []
    for bar in bars:
        ts = int(bar["timestamp"])
        rows.append(
            {
                "symbol": bar.get("symbol", ""),
                "resolution": resolution,
                "timestamp": ts,
                "datetime_utc": pd.Timestamp(ts, unit="s", tz="UTC").strftime("%Y-%m-%d %H:%M:%S"),
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def verify_hyperliquid_credentials() -> dict[str, Any]:
    """Read-only account check when wallet env vars are set (no orders)."""
    import os

    wallet = os.environ.get("HYPERLIQUID_WALLET_ADDRESS", "").strip()
    has_key = bool(os.environ.get("HYPERLIQUID_PRIVATE_KEY", "").strip())
    result: dict[str, Any] = {
        "wallet_configured": bool(wallet),
        "private_key_configured": has_key,
        "account_value_usd": None,
        "ok": False,
    }
    if not wallet:
        result["message"] = "HYPERLIQUID_WALLET_ADDRESS not set"
        return result
    state = _info_client().user_state(wallet)
    margin = state.get("marginSummary") or {}
    result["account_value_usd"] = float(margin.get("accountValue") or 0.0)
    result["ok"] = True
    result["message"] = "user_state fetched"
    return result
