"""MACD line vs signal crossover simulation (long-only) on YahooDownloader output."""

from __future__ import annotations

import pandas as pd


def simulate_macd_crossover(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long-only: fully invested when MACD line > signal line, else cash."""
    d = df.sort_values("date").copy()
    d["date"] = pd.to_datetime(d["date"])
    d.set_index("date", inplace=True)

    close = d["close"].astype(float)
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    sig = pd.Series(0, index=close.index)
    sig.loc[macd_line > signal_line] = 1
    sig.loc[macd_line < signal_line] = 0

    cash = initial_cash
    shares = 0.0
    portfolio_value = []

    first_valid = close.first_valid_index()
    bh_shares = initial_cash / (close.loc[first_valid] * (1 + commission))

    for dt in close.index:
        c = float(close.loc[dt])
        pos_target = int(sig.loc[dt]) if not pd.isna(sig.loc[dt]) else 0

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
            "macd_line": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
            "signal_long": sig,
            "portfolio_value": pv_series,
            "buy_hold_value": bh_series,
        }
    )
    return out, pv_series, bh_series
