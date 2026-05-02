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
) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    return train_df, trade_df


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
    train_df, trade_df = _split_by_calendar_dates(processed, train_fraction)
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
    dates = pd.to_datetime(df_account_value["date"])
    account_values = df_account_value["account_value"].astype(float)

    trade_close = trade_df.sort_values(["date", "tic"]).drop_duplicates("date")[["date", "close"]].copy()
    trade_close["date"] = pd.to_datetime(trade_close["date"])
    merged = pd.DataFrame({"date": dates}).merge(trade_close, on="date", how="left")
    close = merged["close"].astype(float)

    first_close = float(close.iloc[0])
    bh_shares = float(initial_amount) / (first_close * (1 + commission))
    buy_hold = close * bh_shares

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

    idx = pd.DatetimeIndex(dates)
    sig_s = pd.Series(sig_vals[: len(idx)], index=idx, name="signal_long")
    pv_s = pd.Series(account_values.values[: len(idx)], index=idx, name="strategy")
    bh_s = pd.Series(buy_hold.values[: len(idx)], index=idx, name="buy_hold")

    out = pd.DataFrame(
        {
            "close": close.values[: len(idx)],
            "signal_long": sig_s.values,
            "portfolio_value": pv_s.values,
            "buy_hold_value": bh_s.values,
        },
        index=idx,
    )
    return out, pv_s, bh_s
