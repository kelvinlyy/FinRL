"""Train Stable-Baselines3 agents (FinRL DRL pipeline) and roll out equity curves."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

from finrl.agents.stablebaselines3.models import DRLAgent
from finrl.config import INDICATORS
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.meta.preprocessor.preprocessors import FeatureEngineer


def _yahoo_raw_to_processed(df_raw: pd.DataFrame, ticker_upper: bool = True) -> pd.DataFrame:
    """Apply FinRL FeatureEngineer (same indicators as INDICATORS in config)."""
    df = df_raw.copy()
    df.columns = [str(c).lower() for c in df.columns]
    if ticker_upper:
        df["tic"] = df["tic"].astype(str).str.upper()
    fe = FeatureEngineer(
        use_technical_indicator=True,
        tech_indicator_list=INDICATORS,
        use_vix=False,
        use_turbulence=False,
        user_defined_feature=False,
    )
    return fe.preprocess_data(df)


def _split_by_calendar_dates(
    processed: pd.DataFrame,
    train_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame, list[pd.Timestamp], int]:
    proc = processed.copy()
    proc["_cal"] = pd.to_datetime(proc["date"]).dt.normalize()
    dates = sorted(proc["_cal"].unique())
    if len(dates) < 10:
        raise ValueError(
            f"Need more trading days for DRL train/test split (got {len(dates)}). "
            "Use a wider --start/--end range."
        )
    split_i = max(1, min(len(dates) - 2, int(len(dates) * train_fraction)))
    train_dates = set(dates[:split_i])
    trade_dates = set(dates[split_i:])
    train_df = proc[proc["_cal"].isin(train_dates)].drop(columns=["_cal"]).copy()
    trade_df = proc[proc["_cal"].isin(trade_dates)].drop(columns=["_cal"]).copy()
    if len(train_df) < 5 or len(trade_df) < 3:
        raise ValueError(
            "Train/test split produced too few rows; increase date range or adjust train_fraction."
        )
    return train_df, trade_df, dates


def _reindex_by_trading_day(df: pd.DataFrame) -> pd.DataFrame:
    """StockTradingEnv indexes rows by trading-day index (0..n-1), one row per day per tic."""
    out = df.sort_values(["date", "tic"]).copy()
    day_codes = pd.factorize(out["date"].astype(str), sort=True)[0]
    out.index = day_codes
    return out


def simulate_drl_sb3(
    df_raw: pd.DataFrame,
    *,
    algorithm: str,
    train_fraction: float = 0.65,
    timesteps: int = 8000,
    seed: int | None = 42,
    initial_amount: float = 100_000.0,
    hmax: int = 100,
    commission: float = 0.001,
    deterministic_predict: bool = True,
    tech_indicator_list: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Train an SB3 agent on an early slice of calendar dates, evaluate on the remainder.

    Uses FinRL ``StockTradingEnv`` + ``DRLAgent`` (same stack as ``examples/FinRL_StockTrading_2026_2_train.py``).
    """
    algo = algorithm.lower().strip()
    indicators = tech_indicator_list if tech_indicator_list is not None else list(INDICATORS)

    processed = _yahoo_raw_to_processed(df_raw)
    proc_cal = processed.copy()
    proc_cal["_cal"] = pd.to_datetime(proc_cal["date"]).dt.normalize()
    full_close_by_day = proc_cal.groupby("_cal", sort=True)["close"].first()

    train_df, trade_df, calendar_dates = _split_by_calendar_dates(processed, train_fraction)
    train_df = _reindex_by_trading_day(train_df)
    trade_df = _reindex_by_trading_day(trade_df)

    stock_dim = len(train_df["tic"].unique())
    state_space = 1 + 2 * stock_dim + len(indicators) * stock_dim

    buy_cost_list = sell_cost_list = [commission] * stock_dim
    num_stock_shares = [0] * stock_dim

    env_kwargs: dict[str, Any] = {
        "hmax": hmax,
        "initial_amount": int(round(initial_amount)),
        "num_stock_shares": num_stock_shares,
        "buy_cost_pct": buy_cost_list,
        "sell_cost_pct": sell_cost_list,
        "state_space": state_space,
        "stock_dim": stock_dim,
        "tech_indicator_list": indicators,
        "action_space": stock_dim,
        "reward_scaling": 1e-4,
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        env_train = StockTradingEnv(df=train_df, **env_kwargs)
        env_train_sb, _ = env_train.get_sb_env()

        agent = DRLAgent(env=env_train_sb)
        model = agent.get_model(algo, seed=seed, tensorboard_log=None)
        agent.train_model(model=model, tb_log_name=f"web_{algo}", total_timesteps=int(timesteps))

        env_trade = StockTradingEnv(df=trade_df, **env_kwargs)
        df_account_value, df_actions = DRLAgent.DRL_prediction(
            model=model,
            environment=env_trade,
            deterministic=deterministic_predict,
        )

    df_account_value = df_account_value.sort_values("date").reset_index(drop=True)
    dates = pd.to_datetime(df_account_value["date"]).dt.normalize()
    account_values = df_account_value["account_value"].astype(float)

    sig_vals: list[int] = []
    if df_actions is not None and len(df_actions) > 0 and stock_dim == 1:
        df_act = df_actions.sort_values("date").reset_index(drop=True)
        if "actions" in df_act.columns:
            act_series = df_act["actions"]
        else:
            cols = [c for c in df_act.columns if c != "date"]
            act_series = df_act[cols[0]] if cols else None
        if act_series is not None:
            for v in act_series:
                if hasattr(v, "__len__") and not isinstance(v, str):
                    x = float(np.asarray(v).ravel()[0])
                else:
                    try:
                        x = float(v)
                    except (TypeError, ValueError):
                        x = 0.0
                sig_vals.append(1 if x > 0.05 else (0 if x < -0.05 else 0))
    # Align length to equity series (prepend zeros if fewer actions than days)
    while len(sig_vals) < len(dates):
        sig_vals.insert(0, 0)
    sig_vals = sig_vals[: len(dates)]

    idx_test = pd.DatetimeIndex(dates)
    sig_test = pd.Series(sig_vals[: len(idx_test)], index=idx_test, name="signal_long")
    pv_test = pd.Series(account_values.values[: len(idx_test)], index=idx_test, name="strategy")
    # Pad to full Yahoo window so mixed builds align `shared.labels` with rule strategies.
    full_idx = pd.DatetimeIndex(pd.to_datetime(calendar_dates)).normalize()
    close_full = full_close_by_day.reindex(full_idx).astype(float).values
    first_close_global = float(close_full[np.isfinite(close_full)][0])
    bh_shares_global = float(initial_amount) / (first_close_global * (1 + commission))
    buy_hold_full = close_full * bh_shares_global

    pv_map = {idx_test[k]: float(pv_test.iloc[k]) for k in range(len(idx_test))}
    sig_map = {idx_test[k]: float(sig_test.iloc[k]) for k in range(len(idx_test))}
    pv_full = np.array([pv_map.get(d, float(initial_amount)) for d in full_idx], dtype=float)
    sig_full = np.array([sig_map.get(d, 0.0) for d in full_idx], dtype=float)

    out = pd.DataFrame(
        {
            "close": close_full,
            "signal_long": sig_full,
            "portfolio_value": pv_full,
            "buy_hold_value": buy_hold_full,
        },
        index=full_idx,
    )
    pv_s = pd.Series(pv_full, index=full_idx, name="strategy")
    bh_s = pd.Series(buy_hold_full, index=full_idx, name="buy_hold")
    return out, pv_s, bh_s
