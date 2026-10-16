#!/usr/bin/env python3
"""
Fetch Hyperliquid 1m/5m bars, run intraday EMA backtest, verify wallet API (read-only).

Loads credentials from FinRL-Trading/.env and ../traderbot/.env when present.
Does not place orders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.env_loader import load_all_env
from src.data.hyperliquid_fetcher import (
    bars_to_ohlcv_frame,
    fetch_hyperliquid_recent_closed_bars,
    save_bars_csv,
    verify_hyperliquid_credentials,
    HYPERLIQUID_PERP_TAKER_FEE,
)
from src.backtest.intraday_engine import run_intraday_backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coin", default="BTC", help="Hyperliquid perp coin (default BTC)")
    parser.add_argument("--intervals", default="1,5", help="Resolutions: 1,5,...")
    parser.add_argument("--max-bars", type=int, default=100)
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "data" / "hyperliquid")
    args = parser.parse_args(argv)

    env_files = load_all_env(PROJECT_ROOT)
    print("Env files loaded:", [str(p) for p in env_files] or "(none — public candles only)")

    cred = verify_hyperliquid_credentials()
    print(
        "Hyperliquid account check:",
        json.dumps(
            {
                "ok": cred["ok"],
                "wallet_configured": cred["wallet_configured"],
                "private_key_configured": cred["private_key_configured"],
                "account_value_usd": cred.get("account_value_usd"),
                "message": cred.get("message"),
            }
        ),
    )

    intervals = [p.strip() for p in args.intervals.split(",") if p.strip()]
    coin = args.coin.strip().upper()
    report: dict = {"coin": coin, "intervals": {}, "credentials": cred}

    for resolution in intervals:
        print(f"\n--- resolution {resolution}m ---")
        bars = fetch_hyperliquid_recent_closed_bars(
            coin=coin, resolution=resolution, max_bars=args.max_bars
        )
        if not bars:
            print(f"No bars for {coin} @ {resolution}")
            return 1
        csv_path = save_bars_csv(
            bars, args.out_dir / f"{coin}USDT_{resolution}.csv"
        )
        ohlcv = bars_to_ohlcv_frame(bars)
        result = run_intraday_backtest(
            ohlcv,
            resolution=resolution,
            fee_per_side=HYPERLIQUID_PERP_TAKER_FEE,
        )
        summary = {
            "csv": str(csv_path),
            "bars": result.bars,
            "trades": result.trades,
            "window_metrics_not_annualized": result.window,
            "sharpe_per_bar": round(result.sharpe, 4),
            "meta": result.meta,
        }
        report["intervals"][resolution] = summary
        print(json.dumps(summary, indent=2))

    report_path = args.out_dir / f"intraday_experiment_{coin}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
