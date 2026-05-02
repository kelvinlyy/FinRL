# results/

This directory is FinRL’s default output folder (`RESULTS_DIR` in [`finrl/config.py`](../finrl/config.py)).

Training and trading scripts write artifacts here, for example:

- Account value CSVs / PNGs (`account_value_*`, etc.)
- Agent-specific subfolders (`a2c`, `ppo`, …) used by some examples

**Do not commit run outputs.** Generated files under `results/` are ignored by `.gitignore` (except this README and `.gitkeep`).

For the **interactive SMA chart demo**, use [`web/`](../web/) instead (`python web/build_data.py`, then serve `web/`).
