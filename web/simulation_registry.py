"""
Registered rule-based simulations for the web dashboard.

To add a strategy: implement simulate_*(raw_df, **params), register in STRATEGIES.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from macd_crossover_simulation import simulate_macd_crossover
from sma_crossover_simulation import simulate_sma_crossover

SimFn = Callable[..., tuple[pd.DataFrame, pd.Series, pd.Series]]


def _kw_sma(kw: dict[str, Any]) -> dict[str, Any]:
    return {"short_window": kw["short_window"], "long_window": kw["long_window"]}


def _kw_macd(kw: dict[str, Any]) -> dict[str, Any]:
    return {
        "fast": kw["macd_fast"],
        "slow": kw["macd_slow"],
        "signal": kw["macd_signal"],
    }


STRATEGIES: dict[str, dict[str, Any]] = {
    "sma_crossover": {
        "label": "SMA crossover",
        "simulate": simulate_sma_crossover,
        "build_kwargs": _kw_sma,
        "chart_overlays": None,
    },
    "macd_crossover": {
        "label": "MACD crossover",
        "simulate": simulate_macd_crossover,
        "build_kwargs": _kw_macd,
        # Line + signal only (histogram omitted: very different scale vs MACD line, chart looked broken)
        "chart_overlays": [
            {"column": "macd_line", "label": "MACD", "chart": "macd"},
            {"column": "macd_signal", "label": "Signal", "chart": "macd"},
        ],
    },
}


def list_strategy_ids() -> list[str]:
    return list(STRATEGIES.keys())


def run_strategy(strategy_id: str, raw_df: pd.DataFrame, build_kwargs: dict[str, Any]) -> pd.DataFrame:
    if strategy_id not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy_id}. Choose from {list(STRATEGIES.keys())}")
    entry = STRATEGIES[strategy_id]
    fn: SimFn = entry["simulate"]
    skw = entry["build_kwargs"](build_kwargs)
    backtest_df, _, _ = fn(raw_df, **skw)
    return backtest_df


def chart_overlay_specs(strategy_id: str) -> list[dict[str, str]] | None:
    """None = auto sma_* on price chart."""
    spec = STRATEGIES[strategy_id].get("chart_overlays")
    if spec is None:
        return None
    return list(spec)
