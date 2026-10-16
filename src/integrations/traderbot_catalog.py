"""FinRL-Trading surfaces exposed to traderbot."""

from __future__ import annotations

FINRL_USE_CASES = {
    "hyperliquid_intraday": {
        "entry": "scripts/run_hyperliquid_intraday_experiment.py",
        "traderbot_strategy": "finrl_ema_intraday",
        "data": "Hyperliquid perp candles (1m, 5m, …)",
    },
    "adaptive_rotation": {
        "entry": "src/strategies/run_adaptive_rotation_strategy.py",
        "deploy": "./deploy.sh --strategy adaptive_rotation --mode backtest",
        "traderbot": "pipeline finrl-platform / finrl run",
    },
    "ml_stock_selection": {
        "entry": "src/strategies/ml_strategy.py",
        "traderbot": "equity CSV / FinRL data store",
    },
    "drl_portfolio": {
        "entry": "src/strategies/fundamental_portfolio_drl.py",
        "traderbot": "research only (FinRL backtest engine)",
    },
    "professional_backtest": {
        "entry": "src/backtest/backtest_engine.py",
        "library": "bt",
    },
}


def catalog_for_traderbot() -> dict:
    return {"use_cases": FINRL_USE_CASES}
