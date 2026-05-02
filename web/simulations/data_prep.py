"""Normalize YahooDownloader OHLCV dataframe to date-indexed series."""

from __future__ import annotations

import numpy as np
import pandas as pd


def prepare_ohlcv(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Return close, high, low, volume (volume 0-filled if missing)."""
    d = df.sort_values("date").copy()
    d["date"] = pd.to_datetime(d["date"])
    d.set_index("date", inplace=True)
    close = d["close"].astype(float)
    high = d["high"].astype(float)
    low = d["low"].astype(float)
    if "volume" in d.columns:
        vol = d["volume"].astype(float)
    else:
        vol = pd.Series(0.0, index=close.index)
    vol = vol.fillna(0.0)
    return close, high, low, vol
