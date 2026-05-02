"""
Registered simulations for the web dashboard (rule-based + optional FinRL SB3 agents).

To add a strategy: implement simulate_*(raw_df, **params), register in STRATEGIES.
Set ``requires_training: True`` for slow SB3 strategies excluded from default ``build_data`` runs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from simulations.macd_crossover_simulation import simulate_macd_crossover
from simulations.rule_strategy_simulations import (
    simulate_adx_di_trend,
    simulate_bollinger_breakout,
    simulate_bollinger_mean_reversion,
    simulate_donchian_breakout,
    simulate_obv_ma_cross,
    simulate_rsi_mr,
    simulate_zscore_mean_reversion,
)
from simulations.drl_sb3_simulation import simulate_drl_sb3
from simulations.sma_crossover_simulation import simulate_sma_crossover

SimFn = Callable[..., tuple[pd.DataFrame, pd.Series, pd.Series]]

_INDICATOR_CHART = "indicator"


def _kw_sma(kw: dict[str, Any]) -> dict[str, Any]:
    return {"short_window": kw["short_window"], "long_window": kw["long_window"]}


def _kw_macd(kw: dict[str, Any]) -> dict[str, Any]:
    return {
        "fast": kw["macd_fast"],
        "slow": kw["macd_slow"],
        "signal": kw["macd_signal"],
    }


def _kw_rsi(kw: dict[str, Any]) -> dict[str, Any]:
    return {"period": kw["rsi_period"], "rsi_low": kw["rsi_low"], "rsi_high": kw["rsi_high"]}


def _kw_bb(kw: dict[str, Any]) -> dict[str, Any]:
    return {"window": kw["bb_window"], "num_std": kw["bb_std"]}


def _kw_adx(kw: dict[str, Any]) -> dict[str, Any]:
    return {"period": kw["adx_period"], "adx_threshold": kw["adx_threshold"]}


def _kw_donchian(kw: dict[str, Any]) -> dict[str, Any]:
    return {"window": kw["donchian_window"]}


def _kw_zscore(kw: dict[str, Any]) -> dict[str, Any]:
    return {
        "window": kw["zscore_window"],
        "entry_z": kw["zscore_entry"],
        "exit_z": kw["zscore_exit"],
    }


def _kw_obv(kw: dict[str, Any]) -> dict[str, Any]:
    return {"close_ma_window": kw["obv_price_ma"], "obv_ma_window": kw["obv_ma_window"]}


def _kw_drl(kw: dict[str, Any]) -> dict[str, Any]:
    return {
        "algorithm": kw["drl_algorithm"],
        "train_fraction": kw["drl_train_fraction"],
        "timesteps": kw["drl_timesteps"],
        "seed": kw["drl_seed"],
        "initial_amount": kw["drl_initial_amount"],
        "hmax": kw["drl_hmax"],
        "commission": kw["drl_commission"],
    }


def _kw_drl_algo(algo: str):
    def fn(kw: dict[str, Any]) -> dict[str, Any]:
        d = _kw_drl(kw)
        d["algorithm"] = algo
        return d

    return fn


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
        "chart_overlays": [
            {"column": "macd_line", "label": "MACD", "chart": _INDICATOR_CHART},
            {"column": "macd_signal", "label": "Signal", "chart": _INDICATOR_CHART},
        ],
    },
    "rsi_mr": {
        "label": "RSI mean reversion",
        "simulate": simulate_rsi_mr,
        "build_kwargs": _kw_rsi,
        "chart_overlays": [{"column": "rsi", "label": "RSI", "chart": _INDICATOR_CHART}],
    },
    "bollinger_mr": {
        "label": "Bollinger mean reversion",
        "simulate": simulate_bollinger_mean_reversion,
        "build_kwargs": _kw_bb,
        "chart_overlays": [
            {"column": "bb_upper", "label": "BB upper", "chart": "price"},
            {"column": "bb_middle", "label": "BB middle", "chart": "price"},
            {"column": "bb_lower", "label": "BB lower", "chart": "price"},
        ],
    },
    "bollinger_breakout": {
        "label": "Bollinger breakout",
        "simulate": simulate_bollinger_breakout,
        "build_kwargs": _kw_bb,
        "chart_overlays": [
            {"column": "bb_upper", "label": "BB upper", "chart": "price"},
            {"column": "bb_middle", "label": "BB middle", "chart": "price"},
            {"column": "bb_lower", "label": "BB lower", "chart": "price"},
        ],
    },
    "adx_di_trend": {
        "label": "ADX + DI trend filter",
        "simulate": simulate_adx_di_trend,
        "build_kwargs": _kw_adx,
        "chart_overlays": [
            {"column": "plus_di", "label": "+DI", "chart": _INDICATOR_CHART},
            {"column": "minus_di", "label": "-DI", "chart": _INDICATOR_CHART},
            {"column": "adx", "label": "ADX", "chart": _INDICATOR_CHART},
        ],
    },
    "donchian_breakout": {
        "label": "Donchian breakout",
        "simulate": simulate_donchian_breakout,
        "build_kwargs": _kw_donchian,
        "chart_overlays": [
            {"column": "donchian_upper", "label": "Donchian high", "chart": "price"},
            {"column": "donchian_lower", "label": "Donchian low", "chart": "price"},
        ],
    },
    "zscore_mr": {
        "label": "Z-score mean reversion",
        "simulate": simulate_zscore_mean_reversion,
        "build_kwargs": _kw_zscore,
        "chart_overlays": [{"column": "zscore", "label": "Z-score", "chart": _INDICATOR_CHART}],
    },
    "obv_ma_cross": {
        "label": "OBV vs OBV MA",
        "simulate": simulate_obv_ma_cross,
        "build_kwargs": _kw_obv,
        "chart_overlays": [
            {"column": "obv", "label": "OBV", "chart": _INDICATOR_CHART},
            {"column": "obv_ma", "label": "OBV MA", "chart": _INDICATOR_CHART},
        ],
    },
    # FinRL Stable-Baselines3 agents (train on first fraction of dates, test on remainder)
    "drl_ppo": {
        "label": "DRL PPO (SB3)",
        "simulate": simulate_drl_sb3,
        "build_kwargs": _kw_drl_algo("ppo"),
        "chart_overlays": [{"column": "signal_long", "label": "Agent sign", "chart": _INDICATOR_CHART}],
        "requires_training": True,
    },
    "drl_a2c": {
        "label": "DRL A2C (SB3)",
        "simulate": simulate_drl_sb3,
        "build_kwargs": _kw_drl_algo("a2c"),
        "chart_overlays": [{"column": "signal_long", "label": "Agent sign", "chart": _INDICATOR_CHART}],
        "requires_training": True,
    },
    "drl_sac": {
        "label": "DRL SAC (SB3)",
        "simulate": simulate_drl_sb3,
        "build_kwargs": _kw_drl_algo("sac"),
        "chart_overlays": [{"column": "signal_long", "label": "Agent sign", "chart": _INDICATOR_CHART}],
        "requires_training": True,
    },
}


def list_strategy_ids(*, include_requires_training: bool = False) -> list[str]:
    if include_requires_training:
        return list(STRATEGIES.keys())
    return [sid for sid, meta in STRATEGIES.items() if not meta.get("requires_training")]


def default_build_kwargs() -> dict[str, Any]:
    """All CLI-backed keys needed by STRATEGIES."""
    return {
        "short_window": 20,
        "long_window": 50,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "rsi_period": 14,
        "rsi_low": 30.0,
        "rsi_high": 70.0,
        "bb_window": 20,
        "bb_std": 2.0,
        "adx_period": 14,
        "adx_threshold": 25.0,
        "donchian_window": 20,
        "zscore_window": 20,
        "zscore_entry": 2.0,
        "zscore_exit": 0.0,
        "obv_price_ma": 20,
        "obv_ma_window": 20,
        "drl_algorithm": "ppo",
        "drl_train_fraction": 0.65,
        "drl_timesteps": 8000,
        "drl_seed": 42,
        "drl_initial_amount": 100_000.0,
        "drl_hmax": 100,
        "drl_commission": 0.001,
    }


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
