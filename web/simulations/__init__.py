"""Rule-based trading simulations for the web dashboard."""

from simulations.simulation_registry import (
    STRATEGIES,
    chart_overlay_specs,
    default_build_kwargs,
    list_strategy_ids,
    run_strategy,
)

__all__ = [
    "STRATEGIES",
    "chart_overlay_specs",
    "default_build_kwargs",
    "list_strategy_ids",
    "run_strategy",
]
