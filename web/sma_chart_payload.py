"""Serialize SMA backtest DataFrame for Chart.js (data.json)."""

from __future__ import annotations

import pandas as pd


def series_for_chart(df: pd.DataFrame) -> dict:
    idx = df.index
    labels = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in idx]

    def col(name: str) -> list[float | None]:
        s = df[name]
        out: list[float | None] = []
        for v in s:
            out.append(None if pd.isna(v) else float(v))
        return out

    sma_cols = sorted(
        [c for c in df.columns if c.startswith("sma_")],
        key=lambda x: int(x.split("_")[1]),
    )
    out = {
        "labels": labels,
        "close": col("close"),
        "portfolio_value": col("portfolio_value"),
        "buy_hold_value": col("buy_hold_value"),
        "sma_series": [],
    }
    for c in sma_cols:
        out["sma_series"].append({"key": c, "label": c.replace("_", " ").upper(), "data": col(c)})
    return out
