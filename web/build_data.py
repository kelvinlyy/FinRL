"""
Build web/data.json (and optional static PNG) for the SMA chart site.

Run from repository root:
    python web/build_data.py
    python web/build_data.py --ticker MSFT --short 10 --long 30 --png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_WEB = Path(__file__).resolve().parent
_ROOT = _WEB.parent
# web/ first for sma_*, then repo root for finrl
for p in (_WEB, _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from finrl.main import check_and_make_directories
from finrl.meta.preprocessor.yahoodownloader import YahooDownloader

from sma_backtest import run_backtest
from sma_chart_payload import series_for_chart


def _save_png(
    backtest_df,
    ticker: str,
    short_w: int,
    long_w: int,
    start: str,
    end: str,
    path: Path,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})

    df = backtest_df
    ax1 = axes[0]
    ax1.plot(df.index, df["close"], label=f"{ticker} close", color="black", linewidth=1.0)
    ax1.plot(df.index, df[f"sma_{short_w}"], label=f"SMA {short_w}", alpha=0.85)
    ax1.plot(df.index, df[f"sma_{long_w}"], label=f"SMA {long_w}", alpha=0.85)
    ax1.set_ylabel("Price (USD)")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.set_title(f"{ticker} — SMA {short_w}/{long_w} crossover ({start} to {end})")
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(df.index, df["portfolio_value"], label="SMA strategy", linewidth=1.2)
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

    p = argparse.ArgumentParser(description="Build data.json for web/ SMA chart site")
    p.add_argument("--ticker", default="AAPL", help="Stock ticker")
    p.add_argument("--start", default="2019-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", default="2026-05-02", help="End date YYYY-MM-DD")
    p.add_argument("--short", type=int, default=20, help="Short SMA window")
    p.add_argument("--long", type=int, default=50, help="Long SMA window")
    p.add_argument(
        "--output-dir",
        default="",
        help="Write data.json here (default: directory containing this script)",
    )
    p.add_argument("--png", action="store_true", help="Also write preview.png in the web folder")
    args = p.parse_args()

    out_dir = Path(args.output_dir).resolve() if args.output_dir else web_dir
    check_and_make_directories([str(out_dir)])

    raw = YahooDownloader(
        start_date=args.start,
        end_date=args.end,
        ticker_list=[args.ticker],
    ).fetch_data()

    backtest_df, _, _ = run_backtest(
        raw,
        short_window=args.short,
        long_window=args.long,
    )

    chart = series_for_chart(backtest_df)
    title = f"{args.ticker} SMA {args.short}/{args.long} — {args.start} to {args.end}"
    doc = {
        "meta": {
            "title": title,
            "note": "Hover for values; click legend entries to show/hide series.",
            "ticker": args.ticker,
            "start": args.start,
            "end": args.end,
            "short_window": args.short,
            "long_window": args.long,
        },
        "chart": chart,
    }

    data_path = out_dir / "data.json"
    data_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {data_path}")

    if args.png:
        _save_png(
            backtest_df,
            args.ticker,
            args.short,
            args.long,
            args.start,
            args.end,
            out_dir / "preview.png",
        )


if __name__ == "__main__":
    main()
