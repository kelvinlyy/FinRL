"""
Build web/data.json for multi-strategy rule simulations.

Run from repository root:
    python web/build_data.py
    python web/build_data.py --strategies sma_crossover
    python web/build_data.py --strategies sma_crossover,macd_crossover --png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_WEB = Path(__file__).resolve().parent
_ROOT = _WEB.parent
for p in (_WEB, _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from finrl.main import check_and_make_directories
from finrl.meta.preprocessor.yahoodownloader import YahooDownloader

from chart_series_for_json import dataframe_to_chart_series
from simulation_registry import chart_overlay_specs, list_strategy_ids, run_strategy, STRATEGIES


def _save_png_first(
    backtest_df,
    strategy_id: str,
    ticker: str,
    start: str,
    end: str,
    path: Path,
    short_w: int,
    long_w: int,
) -> None:
    df = backtest_df
    if strategy_id == "macd_crossover" and "macd_line" in df.columns:
        fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [1.2, 0.9, 1]})
        axes[0].plot(df.index, df["close"], label=f"{ticker} close", color="black", linewidth=1.0)
        axes[0].set_ylabel("Price ($)")
        axes[0].legend(loc="upper left", fontsize=9)
        axes[0].grid(True, alpha=0.3)
        axes[1].plot(df.index, df["macd_line"], label="MACD", alpha=0.85)
        axes[1].plot(df.index, df["macd_signal"], label="Signal", alpha=0.85)
        axes[1].set_ylabel("MACD")
        axes[1].legend(loc="upper left", fontsize=9)
        axes[1].grid(True, alpha=0.3)
        axes[0].set_title(f"{ticker} — {STRATEGIES[strategy_id]['label']} ({start} to {end})")
        ax2 = axes[2]
    else:
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
        ax1 = axes[0]
        ax1.plot(df.index, df["close"], label=f"{ticker} close", color="black", linewidth=1.0)
        ax1.plot(df.index, df[f"sma_{short_w}"], label=f"SMA {short_w}", alpha=0.85)
        ax1.plot(df.index, df[f"sma_{long_w}"], label=f"SMA {long_w}", alpha=0.85)
        ax1.set_ylabel("Price ($)")
        ax1.legend(loc="upper left", fontsize=9)
        ax1.set_title(f"{ticker} — {STRATEGIES[strategy_id]['label']} ({start} to {end})")
        ax1.grid(True, alpha=0.3)
        ax2 = axes[1]

    ax2.plot(df.index, df["portfolio_value"], label="Strategy", linewidth=1.2)
    ax2.plot(df.index, df["buy_hold_value"], label="Buy & hold", linewidth=1.2, alpha=0.85)
    ax2.set_ylabel("Portfolio value ($)")
    ax2.set_xlabel("Date")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Wrote {path}")


def main() -> None:
    web_dir = Path(__file__).resolve().parent
    all_ids = list_strategy_ids()

    p = argparse.ArgumentParser(description="Build data.json for web multi-strategy charts")
    p.add_argument("--ticker", default="AAPL", help="Stock ticker")
    p.add_argument("--start", default="2019-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", default="2026-05-02", help="End date YYYY-MM-DD")
    p.add_argument("--short", type=int, default=20, help="SMA short window")
    p.add_argument("--long", type=int, default=50, help="SMA long window")
    p.add_argument("--macd-fast", type=int, default=12, dest="macd_fast")
    p.add_argument("--macd-slow", type=int, default=26, dest="macd_slow")
    p.add_argument("--macd-signal", type=int, default=9, dest="macd_signal")
    p.add_argument(
        "--strategies",
        default=",".join(all_ids),
        help=f"Comma-separated ids (default: all). Available: {','.join(all_ids)}",
    )
    p.add_argument(
        "--output-dir",
        default="",
        help="Write data.json here (default: directory containing this script)",
    )
    p.add_argument("--png", action="store_true", help="PNG preview for first strategy only")
    args = p.parse_args()

    strategy_ids = [s.strip() for s in args.strategies.split(",") if s.strip()]
    for sid in strategy_ids:
        if sid not in STRATEGIES:
            raise SystemExit(f"Unknown strategy {sid}. Choose from {all_ids}")

    out_dir = Path(args.output_dir).resolve() if args.output_dir else web_dir
    check_and_make_directories([str(out_dir)])

    build_kw = {
        "short_window": args.short,
        "long_window": args.long,
        "macd_fast": args.macd_fast,
        "macd_slow": args.macd_slow,
        "macd_signal": args.macd_signal,
    }

    raw = YahooDownloader(
        start_date=args.start,
        end_date=args.end,
        ticker_list=[args.ticker],
    ).fetch_data()

    strategies_payload: dict[str, dict] = {}
    first_df = None

    for sid in strategy_ids:
        df_bt = run_strategy(sid, raw, build_kw)
        overlays = chart_overlay_specs(sid)
        chart = dataframe_to_chart_series(df_bt, overlay_specs=overlays)

        strategies_payload[sid] = {
            "label": STRATEGIES[sid]["label"],
            "portfolio_value": chart["portfolio_value"],
            "overlay_series": chart["overlay_series"],
        }
        if first_df is None:
            first_df = df_bt

    assert first_df is not None
    shared_chart = dataframe_to_chart_series(first_df, overlay_specs=chart_overlay_specs(strategy_ids[0]))

    doc = {
        "meta": {
            "title": f"{args.ticker} — rule strategies ({args.start} to {args.end})",
            "note": "Use the strategy selector; enable compare to overlay all model equity curves.",
            "ticker": args.ticker,
            "start": args.start,
            "end": args.end,
            "strategy_ids": strategy_ids,
            "params": {
                "sma_short": args.short,
                "sma_long": args.long,
                "macd_fast": args.macd_fast,
                "macd_slow": args.macd_slow,
                "macd_signal": args.macd_signal,
            },
        },
        "shared": {
            "labels": shared_chart["labels"],
            "close": shared_chart["close"],
            "buy_hold_value": shared_chart["buy_hold_value"],
        },
        "strategies": strategies_payload,
    }

    data_path = out_dir / "data.json"
    data_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {data_path} with strategies: {', '.join(strategy_ids)}")

    if args.png and strategy_ids:
        _save_png_first(
            run_strategy(strategy_ids[0], raw, build_kw),
            strategy_ids[0],
            args.ticker,
            args.start,
            args.end,
            out_dir / "preview.png",
            args.short,
            args.long,
        )


if __name__ == "__main__":
    main()
