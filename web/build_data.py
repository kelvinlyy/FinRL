"""
Build web/data.json for multi-strategy rule simulations.

Run from repository root:
    python web/build_data.py
    python web/build_data.py --strategies sma_crossover,rsi_mr
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

DEFAULT_DATA_START = "2023-01-01"

_WEB = Path(__file__).resolve().parent
_ROOT = _WEB.parent
# Insert repo root first, then web/ — both via insert(0) so final order is [web/, repo_root/].
# If repo_root came first, a top-level `simulations/` package could shadow `web/simulations`.
for p in (_ROOT, _WEB):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from finrl.main import check_and_make_directories  # noqa: E402
from finrl.meta.preprocessor.yahoodownloader import YahooDownloader  # noqa: E402

from chart_series_for_json import dataframe_to_chart_series  # noqa: E402
from simulations.simulation_registry import (  # noqa: E402
    STRATEGIES,
    chart_overlay_specs,
    default_build_kwargs,
    list_strategy_ids,
    run_strategy,
)


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
    spec = STRATEGIES[strategy_id].get("chart_overlays") or []
    uses_indicator_pane = any(
        isinstance(x, dict) and x.get("chart") in ("indicator", "macd") for x in spec
    )

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
    elif uses_indicator_pane:
        fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [1.2, 0.9, 1]})
        axes[0].plot(df.index, df["close"], label=f"{ticker} close", color="black", linewidth=1.0)
        if "bb_upper" in df.columns:
            axes[0].plot(df.index, df["bb_upper"], label="BB upper", alpha=0.7)
            axes[0].plot(df.index, df["bb_middle"], label="BB mid", alpha=0.7)
            axes[0].plot(df.index, df["bb_lower"], label="BB lower", alpha=0.7)
        if "donchian_upper" in df.columns:
            axes[0].plot(df.index, df["donchian_upper"], label="Donchian hi", alpha=0.7)
            axes[0].plot(df.index, df["donchian_lower"], label="Donchian lo", alpha=0.7)
        axes[0].set_ylabel("Price ($)")
        axes[0].legend(loc="upper left", fontsize=8)
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title(f"{ticker} — {STRATEGIES[strategy_id]['label']} ({start} to {end})")

        ax_mid = axes[1]
        mid_cols = [
            c
            for c in df.columns
            if c
            in (
                "rsi",
                "macd_line",
                "macd_signal",
                "plus_di",
                "minus_di",
                "adx",
                "zscore",
                "obv",
                "obv_ma",
            )
        ]
        for i, col in enumerate(mid_cols[:6]):
            ax_mid.plot(df.index, df[col], label=col, alpha=0.85)
        ax_mid.set_ylabel("Indicators")
        ax_mid.legend(loc="upper left", fontsize=8)
        ax_mid.grid(True, alpha=0.3)
        ax2 = axes[2]
    else:
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
        ax1 = axes[0]
        ax1.plot(df.index, df["close"], label=f"{ticker} close", color="black", linewidth=1.0)
        if f"sma_{short_w}" in df.columns:
            ax1.plot(df.index, df[f"sma_{short_w}"], label=f"SMA {short_w}", alpha=0.85)
        if f"sma_{long_w}" in df.columns:
            ax1.plot(df.index, df[f"sma_{long_w}"], label=f"SMA {long_w}", alpha=0.85)
        if "bb_upper" in df.columns:
            ax1.plot(df.index, df["bb_upper"], label="BB upper", alpha=0.7)
            ax1.plot(df.index, df["bb_middle"], label="BB mid", alpha=0.7)
            ax1.plot(df.index, df["bb_lower"], label="BB lower", alpha=0.7)
        if "donchian_upper" in df.columns:
            ax1.plot(df.index, df["donchian_upper"], label="Donchian hi", alpha=0.7)
            ax1.plot(df.index, df["donchian_lower"], label="Donchian lo", alpha=0.7)
        ax1.set_ylabel("Price ($)")
        ax1.legend(loc="upper left", fontsize=8)
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
    defaults = default_build_kwargs()
    default_end = date.today().isoformat()

    p = argparse.ArgumentParser(description="Build data.json for web multi-strategy charts")
    p.add_argument("--ticker", default="AAPL", help="Stock ticker")
    p.add_argument(
        "--start",
        default=DEFAULT_DATA_START,
        help=f"Start date YYYY-MM-DD (default: {DEFAULT_DATA_START})",
    )
    p.add_argument(
        "--end",
        default=default_end,
        help=f"End date YYYY-MM-DD (default: today, {default_end})",
    )
    p.add_argument("--short", type=int, default=defaults["short_window"], help="SMA short window")
    p.add_argument("--long", type=int, default=defaults["long_window"], help="SMA long window")
    p.add_argument("--macd-fast", type=int, default=defaults["macd_fast"], dest="macd_fast")
    p.add_argument("--macd-slow", type=int, default=defaults["macd_slow"], dest="macd_slow")
    p.add_argument("--macd-signal", type=int, default=defaults["macd_signal"], dest="macd_signal")
    p.add_argument("--rsi-period", type=int, default=defaults["rsi_period"], dest="rsi_period")
    p.add_argument("--rsi-low", type=float, default=defaults["rsi_low"], dest="rsi_low")
    p.add_argument("--rsi-high", type=float, default=defaults["rsi_high"], dest="rsi_high")
    p.add_argument("--bb-window", type=int, default=defaults["bb_window"], dest="bb_window")
    p.add_argument("--bb-std", type=float, default=defaults["bb_std"], dest="bb_std")
    p.add_argument("--adx-period", type=int, default=defaults["adx_period"], dest="adx_period")
    p.add_argument("--adx-threshold", type=float, default=defaults["adx_threshold"], dest="adx_threshold")
    p.add_argument("--donchian-window", type=int, default=defaults["donchian_window"], dest="donchian_window")
    p.add_argument("--zscore-window", type=int, default=defaults["zscore_window"], dest="zscore_window")
    p.add_argument("--zscore-entry", type=float, default=defaults["zscore_entry"], dest="zscore_entry")
    p.add_argument("--zscore-exit", type=float, default=defaults["zscore_exit"], dest="zscore_exit")
    p.add_argument("--obv-price-ma", type=int, default=defaults["obv_price_ma"], dest="obv_price_ma")
    p.add_argument("--obv-ma-window", type=int, default=defaults["obv_ma_window"], dest="obv_ma_window")
    p.add_argument(
        "--drl-train-fraction",
        type=float,
        default=defaults["drl_train_fraction"],
        dest="drl_train_fraction",
        help="Fraction of calendar days used for SB3 training (rest is rollout for charts)",
    )
    p.add_argument(
        "--drl-timesteps",
        type=int,
        default=defaults["drl_timesteps"],
        dest="drl_timesteps",
        help="Stable-Baselines3 train timesteps per DRL strategy",
    )
    p.add_argument(
        "--drl-seed",
        type=int,
        default=defaults["drl_seed"],
        dest="drl_seed",
        help="RNG seed for SB3 (None disables)",
    )
    p.add_argument(
        "--drl-initial-cash",
        type=float,
        default=defaults["drl_initial_amount"],
        dest="drl_initial_amount",
        help="Initial portfolio cash for FinRL StockTradingEnv",
    )
    p.add_argument("--drl-hmax", type=int, default=defaults["drl_hmax"], dest="drl_hmax")
    p.add_argument(
        "--drl-commission",
        type=float,
        default=defaults["drl_commission"],
        dest="drl_commission",
    )
    p.add_argument(
        "--include-drl-training",
        action="store_true",
        help="Include drl_ppo/drl_a2c/drl_sac in default --strategies list (slow)",
    )
    p.add_argument(
        "--strategies",
        default=None,
        help="Comma-separated ids (default: all rule strategies, or all+DRL if --include-drl-training)",
    )
    p.add_argument(
        "--output-dir",
        default="",
        help="Write data.json here (default: directory containing this script)",
    )
    p.add_argument("--png", action="store_true", help="PNG preview for first strategy only")
    args = p.parse_args()

    all_known = list_strategy_ids(include_requires_training=True)
    default_bundle = list_strategy_ids(include_requires_training=args.include_drl_training)
    if args.strategies is None:
        strategy_csv = ",".join(default_bundle)
    else:
        strategy_csv = args.strategies

    strategy_ids = [s.strip() for s in strategy_csv.split(",") if s.strip()]
    for sid in strategy_ids:
        if sid not in STRATEGIES:
            raise SystemExit(f"Unknown strategy {sid}. Choose from {all_known}")

    out_dir = Path(args.output_dir).resolve() if args.output_dir else web_dir
    check_and_make_directories([str(out_dir)])

    build_kw = {
        "short_window": args.short,
        "long_window": args.long,
        "macd_fast": args.macd_fast,
        "macd_slow": args.macd_slow,
        "macd_signal": args.macd_signal,
        "rsi_period": args.rsi_period,
        "rsi_low": args.rsi_low,
        "rsi_high": args.rsi_high,
        "bb_window": args.bb_window,
        "bb_std": args.bb_std,
        "adx_period": args.adx_period,
        "adx_threshold": args.adx_threshold,
        "donchian_window": args.donchian_window,
        "zscore_window": args.zscore_window,
        "zscore_entry": args.zscore_entry,
        "zscore_exit": args.zscore_exit,
        "obv_price_ma": args.obv_price_ma,
        "obv_ma_window": args.obv_ma_window,
        "drl_algorithm": "ppo",
        "drl_train_fraction": args.drl_train_fraction,
        "drl_timesteps": args.drl_timesteps,
        "drl_seed": args.drl_seed,
        "drl_initial_amount": args.drl_initial_amount,
        "drl_hmax": args.drl_hmax,
        "drl_commission": args.drl_commission,
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
            "params": build_kw,
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
