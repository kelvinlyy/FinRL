"""Long-only portfolio simulation from a daily {0,1} position signal."""

from __future__ import annotations

import pandas as pd


def simulate_long_only_from_signal(
    close: pd.Series,
    signal_long: pd.Series,
    *,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.Series, pd.Series]:
    """
    Fully invest when signal_long == 1 and flat when 0.
    NaN or inf in signal treated as 0.
    """
    close = close.astype(float)
    sig = signal_long.fillna(0).astype(float)
    sig = sig.where(sig.notna(), 0)
    sig = (sig >= 0.5).astype(int)

    cash = initial_cash
    shares = 0.0
    portfolio_value = []

    first_valid = close.first_valid_index()
    bh_shares = initial_cash / (close.loc[first_valid] * (1 + commission))

    for dt in close.index:
        c = float(close.loc[dt])
        pos_target = int(sig.loc[dt]) if dt in sig.index else 0

        if pos_target == 1 and shares == 0 and cash > 0:
            shares = cash / (c * (1 + commission))
            cash = 0.0
        elif pos_target == 0 and shares > 0:
            proceeds = shares * c * (1 - commission)
            cash += proceeds
            shares = 0.0

        portfolio_value.append(cash + shares * c)

    pv_series = pd.Series(portfolio_value, index=close.index, name="strategy")
    bh_series = (close * bh_shares).rename("buy_hold")
    return pv_series, bh_series


def frame_with_pf(
    extras: dict[str, pd.Series],
    close: pd.Series,
    signal_long: pd.Series,
    *,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Merge indicator columns + portfolio columns."""
    pv, bh = simulate_long_only_from_signal(
        close, signal_long, initial_cash=initial_cash, commission=commission
    )
    cols = {"close": close, **extras, "signal_long": signal_long, "portfolio_value": pv, "buy_hold_value": bh}
    df = pd.DataFrame(cols)
    return df, pv, bh
