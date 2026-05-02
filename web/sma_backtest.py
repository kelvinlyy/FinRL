"""SMA crossover backtest (long-only) using FinRL YahooDownloader output."""

from __future__ import annotations

import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    short_window: int = 20,
    long_window: int = 50,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long-only SMA crossover: fully invested when short SMA > long SMA, else cash."""
    d = df.sort_values("date").copy()
    d["date"] = pd.to_datetime(d["date"])
    d.set_index("date", inplace=True)

    close = d["close"].astype(float)
    sma_short = close.rolling(short_window).mean()
    sma_long = close.rolling(long_window).mean()

    signal = pd.Series(0, index=close.index)
    signal.loc[sma_short > sma_long] = 1
    signal.loc[sma_short < sma_long] = 0

    cash = initial_cash
    shares = 0.0
    portfolio_value = []

    first_valid = close.first_valid_index()
    bh_shares = initial_cash / (close.loc[first_valid] * (1 + commission))

    for dt in close.index:
        c = float(close.loc[dt])
        pos_target = int(signal.loc[dt]) if not pd.isna(signal.loc[dt]) else 0

        if pos_target == 1 and shares == 0 and cash > 0:
            shares = cash / (c * (1 + commission))
            cash = 0.0
        elif pos_target == 0 and shares > 0:
            proceeds = shares * c * (1 - commission)
            cash += proceeds
            shares = 0.0

        pv = cash + shares * c
        portfolio_value.append(pv)

    pv_series = pd.Series(portfolio_value, index=close.index, name="strategy")
    bh_series = (close * bh_shares).rename("buy_hold")

    out = pd.DataFrame(
        {
            "close": close,
            f"sma_{short_window}": sma_short,
            f"sma_{long_window}": sma_long,
            "signal_long": signal,
            "portfolio_value": pv_series,
            "buy_hold_value": bh_series,
        }
    )
    return out, pv_series, bh_series
