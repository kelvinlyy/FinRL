"""Additional rule-based simulations (RSI, Bollinger, ADX, Donchian, z-score, OBV)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from simulations.data_prep import prepare_ohlcv
from simulations.long_only_engine import frame_with_pf
from simulations.technicals import (
    adx_di,
    bollinger_bands,
    donchian_prev_high,
    donchian_prev_low,
    obv,
    rsi_wilder,
    zscore,
)


def simulate_rsi_mr(
    df: pd.DataFrame,
    period: int = 14,
    rsi_low: float = 30.0,
    rsi_high: float = 70.0,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Enter long when RSI crosses up through rsi_low from below; exit when crosses down through rsi_high."""
    close, _, _, _ = prepare_ohlcv(df)
    rsi = rsi_wilder(close, period)
    prev = rsi.shift(1)
    sig_vals = []
    pos = 0
    for dt in close.index:
        r = rsi.loc[dt]
        pr = prev.loc[dt] if dt in prev.index else np.nan
        if pd.isna(r):
            sig_vals.append(pos)
            continue
        if pos == 0:
            if not pd.isna(pr) and pr < rsi_low and r >= rsi_low:
                pos = 1
        else:
            if not pd.isna(pr) and pr > rsi_high and r <= rsi_high:
                pos = 0
        sig_vals.append(pos)
    sig = pd.Series(sig_vals, index=close.index)
    extras = {"rsi": rsi}
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)


def simulate_bollinger_mean_reversion(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long when close <= lower band; flat when close >= middle band."""
    close, _, _, _ = prepare_ohlcv(df)
    upper, mid, lower = bollinger_bands(close, window, num_std)
    sig_vals = []
    pos = 0
    for dt in close.index:
        c = close.loc[dt]
        lo = lower.loc[dt]
        m = mid.loc[dt]
        if pd.isna(lo) or pd.isna(m):
            sig_vals.append(pos)
            continue
        if pos == 0 and c <= lo:
            pos = 1
        elif pos == 1 and c >= m:
            pos = 0
        sig_vals.append(pos)
    sig = pd.Series(sig_vals, index=close.index)
    extras = {"bb_upper": upper, "bb_middle": mid, "bb_lower": lower}
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)


def simulate_bollinger_breakout(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long when close > upper band; flat when close < middle band."""
    close, _, _, _ = prepare_ohlcv(df)
    upper, mid, lower = bollinger_bands(close, window, num_std)
    sig_vals = []
    pos = 0
    for dt in close.index:
        c = close.loc[dt]
        u = upper.loc[dt]
        m = mid.loc[dt]
        if pd.isna(u) or pd.isna(m):
            sig_vals.append(pos)
            continue
        if pos == 0 and c > u:
            pos = 1
        elif pos == 1 and c < m:
            pos = 0
        sig_vals.append(pos)
    sig = pd.Series(sig_vals, index=close.index)
    extras = {"bb_upper": upper, "bb_middle": mid, "bb_lower": lower}
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)


def simulate_adx_di_trend(
    df: pd.DataFrame,
    period: int = 14,
    adx_threshold: float = 25.0,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long when ADX > threshold and +DI > -DI; else flat."""
    close, high, low, _ = prepare_ohlcv(df)
    plus_di, minus_di, adx_val = adx_di(high, low, close, period)
    sig = ((adx_val > adx_threshold) & (plus_di > minus_di)).astype(int)
    sig = sig.where(~adx_val.isna(), 0)
    extras = {"plus_di": plus_di, "minus_di": minus_di, "adx": adx_val}
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)


def simulate_donchian_breakout(
    df: pd.DataFrame,
    window: int = 20,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long when close breaks prior N-bar high; flat when breaks prior N-bar low."""
    close, high, low, _ = prepare_ohlcv(df)
    ph = donchian_prev_high(high, window)
    pl = donchian_prev_low(low, window)
    sig_vals = []
    pos = 0
    for dt in close.index:
        c = close.loc[dt]
        h_prev = ph.loc[dt]
        l_prev = pl.loc[dt]
        if pd.isna(h_prev) or pd.isna(l_prev):
            sig_vals.append(pos)
            continue
        if pos == 0 and c > h_prev:
            pos = 1
        elif pos == 1 and c < l_prev:
            pos = 0
        sig_vals.append(pos)
    sig = pd.Series(sig_vals, index=close.index)
    extras = {"donchian_upper": ph, "donchian_lower": pl}
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)


def simulate_zscore_mean_reversion(
    df: pd.DataFrame,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long when z-score < -entry_z; flat when z-score > exit_z."""
    close, _, _, _ = prepare_ohlcv(df)
    z, ma, sd = zscore(close, window)
    sig_vals = []
    pos = 0
    for dt in close.index:
        zz = z.loc[dt]
        if pd.isna(zz):
            sig_vals.append(pos)
            continue
        if pos == 0 and zz < -entry_z:
            pos = 1
        elif pos == 1 and zz > exit_z:
            pos = 0
        sig_vals.append(pos)
    sig = pd.Series(sig_vals, index=close.index)
    extras = {"zscore": z, "zscore_ma": ma}
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)


def simulate_obv_ma_cross(
    df: pd.DataFrame,
    close_ma_window: int = 20,
    obv_ma_window: int = 20,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Long when OBV > SMA(OBV) and close > SMA(close); else flat."""
    close, _, _, vol = prepare_ohlcv(df)
    line = obv(close, vol)
    obv_ma = line.rolling(obv_ma_window).mean()
    close_ma = close.rolling(close_ma_window).mean()
    sig = ((line > obv_ma) & (close > close_ma)).astype(int)
    sig = sig.where(~(line.isna() | obv_ma.isna() | close_ma.isna()), 0)
    extras = {"obv": line, "obv_ma": obv_ma, "price_ma": close_ma}
    return frame_with_pf(extras, close, sig, initial_cash=initial_cash, commission=commission)
