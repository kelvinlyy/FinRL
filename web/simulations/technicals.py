"""Technical indicators for rule-based web simulations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta.clip(upper=0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    vol = volume.astype(float).fillna(0)
    return (direction * vol).cumsum()


def donchian_prev_high(high: pd.Series, window: int) -> pd.Series:
    """Prior N-bar rolling max high (exclude today for breakout convention)."""
    return high.rolling(window).max().shift(1)


def donchian_prev_low(low: pd.Series, window: int) -> pd.Series:
    return low.rolling(window).min().shift(1)


def zscore(close: pd.Series, window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    ma = close.rolling(window).mean()
    sd = close.rolling(window).std()
    z = (close - ma) / sd.replace(0, np.nan)
    return z, ma, sd


def adx_di(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder-style +DI, -DI, ADX (approximation consistent with common TA implementations)."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=close.index)
    minus_dm = pd.Series(minus_dm, index=close.index)

    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    plus_di = 100.0 * (
        plus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan)
    )
    minus_di = 100.0 * (
        minus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan)
    )

    dx = (100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0)
    adx = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return plus_di, minus_di, adx
