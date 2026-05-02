"""Convert simulation DataFrame into JSON-ready series for Chart.js / data.json."""

from __future__ import annotations

from typing import Any

import pandas as pd


def dataframe_to_chart_series(
    df: pd.DataFrame,
    overlay_specs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """overlay_specs entries: column, label, chart optional ('price', 'indicator', or legacy 'macd')."""
    idx = df.index
    labels = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in idx]

    def col(name: str) -> list[float | None]:
        s = df[name]
        out: list[float | None] = []
        for v in s:
            out.append(None if pd.isna(v) else float(v))
        return out

    overlay_series: list[dict[str, Any]] = []

    if overlay_specs:
        for spec in overlay_specs:
            c = spec["column"]
            if c not in df.columns:
                continue
            chart = spec.get("chart", "price")
            overlay_series.append(
                {
                    "key": c,
                    "label": spec["label"],
                    "chart": chart,
                    "data": col(c),
                }
            )
    else:
        sma_cols = sorted(
            [c for c in df.columns if c.startswith("sma_")],
            key=lambda x: int(x.split("_")[1]),
        )
        for c in sma_cols:
            overlay_series.append(
                {
                    "key": c,
                    "label": c.replace("_", " ").upper(),
                    "chart": "price",
                    "data": col(c),
                }
            )

    return {
        "labels": labels,
        "close": col("close"),
        "portfolio_value": col("portfolio_value"),
        "buy_hold_value": col("buy_hold_value"),
        "overlay_series": overlay_series,
        "sma_series": [
            {"key": x["key"], "label": x["label"], "data": x["data"]}
            for x in overlay_series
            if x.get("chart", "price") == "price"
        ],
    }
