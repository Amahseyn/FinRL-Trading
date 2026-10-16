import numpy as np
import pandas as pd

from src.backtest.intraday_engine import run_intraday_backtest


def test_intraday_backtest_runs_on_synthetic_bars():
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    trend = np.linspace(100, 120, n) + np.random.default_rng(0).normal(0, 0.2, n)
    ohlcv = pd.DataFrame(
        {
            "open": trend,
            "high": trend + 0.5,
            "low": trend - 0.5,
            "close": trend,
            "volume": 1.0,
        },
        index=idx,
    )
    result = run_intraday_backtest(ohlcv, resolution="5", fast_ema=8, slow_ema=20)
    assert result.bars == n
    assert result.equity_curve.iloc[-1] > 0
