"""MACD line vs signal crossover simulation (long-only) on YahooDownloader output."""

from __future__ import annotations

import pandas as pd

from simulations.data_prep import prepare_ohlcv
from simulations.long_only_engine import frame_with_pf


def simulate_macd_crossover(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long-only: fully invested when MACD line > signal line, else cash."""
    close, _, _, _ = prepare_ohlcv(df)

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    sig = pd.Series(0, index=close.index)
    sig.loc[macd_line > signal_line] = 1
    sig.loc[macd_line < signal_line] = 0

    extras = {
        "macd_line": macd_line,
        "macd_signal": signal_line,
        "macd_histogram": histogram,
    }
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)
