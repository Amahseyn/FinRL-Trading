#!/usr/bin/env python3
"""Run adaptive rotation backtest and report metrics on last N periods (not annualized)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.window_metrics import equity_window_metrics


def _equity_from_weights_csv(weights_csv: Path, data_dir: Path) -> pd.Series:
    weights_df = pd.read_csv(weights_csv)
    weights_df["date"] = pd.to_datetime(weights_df["date"])
    meta_cols = ["date", "cash", "regime"]
    asset_cols = [c for c in weights_df.columns if c not in meta_cols]

    prices = {}
    for sym in asset_cols:
        csv_path = data_dir / f"{sym}_daily.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df["date"] = pd.to_datetime(df["date"])
            prices[sym] = df.set_index("date")["close"]
    price_df = pd.DataFrame(prices)
    dates = weights_df["date"].values

    portfolio_values = [1.0]
    for i in range(len(dates) - 1):
        d0, d1 = pd.Timestamp(dates[i]), pd.Timestamp(dates[i + 1])
        row = weights_df.iloc[i]
        period_return = 0.0
        for sym in asset_cols:
            w = row[sym]
            if w > 0 and sym in price_df.columns:
                p0_s = price_df[sym].loc[:d0].dropna()
                p1_s = price_df[sym].loc[:d1].dropna()
                if len(p0_s) > 0 and len(p1_s) > 0:
                    period_return += w * (p1_s.iloc[-1] / p0_s.iloc[-1] - 1)
        portfolio_values.append(portfolio_values[-1] * (1 + period_return))

    equity = pd.Series(portfolio_values, index=pd.to_datetime(dates), name="portfolio")
    return equity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", type=int, default=100)
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--data-dir", default="data/fmp_daily")
    parser.add_argument("--skip-backtest", action="store_true")
    args = parser.parse_args(argv)

    end = pd.Timestamp(args.end)
    start = (end - pd.Timedelta(weeks=args.periods + 8)).strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")

    runner = PROJECT_ROOT / "src/strategies/run_adaptive_rotation_strategy.py"
    config = PROJECT_ROOT / "src/strategies/AdaptiveRotationConf_v1.2.1.yaml"
    cmd = [
        sys.executable,
        str(runner),
        "--config",
        str(config),
        "--data-dir",
        str(PROJECT_ROOT / args.data_dir),
        "--backtest",
        "--start",
        start,
        "--end",
        end_s,
        "--freq",
        "W-FRI",
    ]
    if not args.skip_backtest:
        print("Running:", " ".join(cmd))
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)

    weights_csv = (
        PROJECT_ROOT
        / "src/strategies/output/weights/adaptive_rotation"
        / f"ars_portfolio_weights_{start}_to_{end_s}.csv"
    )
    if not weights_csv.exists():
        # fallback glob
        candidates = sorted(
            (PROJECT_ROOT / "src/strategies/output/weights/adaptive_rotation").glob(
                "ars_portfolio_weights_*.csv"
            )
        )
        weights_csv = candidates[-1]

    equity = _equity_from_weights_csv(weights_csv, PROJECT_ROOT / args.data_dir)
    window_eq = equity.iloc[-(args.periods + 1) :]
    metrics = equity_window_metrics(window_eq)

    bench = {}
    for sym in ("SPY", "QQQ"):
        csv_path = PROJECT_ROOT / args.data_dir / f"{sym}_daily.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        series = df.set_index("date")["close"]
        bench_vals = []
        for dt in window_eq.index:
            px = series.loc[:dt].dropna()
            if len(px) == 0:
                continue
            bench_vals.append(px.iloc[-1])
        if len(bench_vals) != len(window_eq):
            continue
        bench_eq = pd.Series(bench_vals, index=window_eq.index) / bench_vals[0]
        bench[sym] = equity_window_metrics(bench_eq)

    report = {
        "strategy": "adaptive_rotation",
        "rebalance_freq": "W-FRI",
        "periods_requested": args.periods,
        "weights_file": str(weights_csv),
        "date_range": {
            "first": str(window_eq.index[0].date()),
            "last": str(window_eq.index[-1].date()),
        },
        "strategy_window_metrics_not_annualized": metrics,
        "benchmarks_window_metrics_not_annualized": bench,
    }
    out = PROJECT_ROOT / "data" / f"adaptive_rotation_{args.periods}periods_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
