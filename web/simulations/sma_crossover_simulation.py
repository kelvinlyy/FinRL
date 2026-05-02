"""SMA crossover strategy simulation (long-only) on FinRL YahooDownloader output."""

from __future__ import annotations

import pandas as pd

from simulations.data_prep import prepare_ohlcv
from simulations.long_only_engine import frame_with_pf


def simulate_sma_crossover(
    df: pd.DataFrame,
    short_window: int = 20,
    long_window: int = 50,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long-only SMA crossover: fully invested when short SMA > long SMA, else cash."""
    close, _, _, _ = prepare_ohlcv(df)

    sma_short = close.rolling(short_window).mean()
    sma_long = close.rolling(long_window).mean()

    signal = pd.Series(0, index=close.index)
    signal.loc[sma_short > sma_long] = 1
    signal.loc[sma_short < sma_long] = 0

    extras = {
        f"sma_{short_window}": sma_short,
        f"sma_{long_window}": sma_long,
    }
    return frame_with_pf(extras, close, signal, initial_cash=initial_cash, commission=commission)
