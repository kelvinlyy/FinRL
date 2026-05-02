# AGENTS.md

## Cursor Cloud specific instructions

### Overview

FinRL is a Python-based financial reinforcement learning framework. It is a single Python package (not a monorepo) with no databases, web servers, or auxiliary services. All data is fetched at runtime from external APIs (primarily Yahoo Finance for free/no-auth usage).

### Virtual environment

All Python work must use the venv at `/workspace/.venv`. Activate it with:

```
source /workspace/.venv/bin/activate
```

### Lint

```
flake8 finrl/ --count --statistics
```

The repo has ~126 pre-existing flake8 warnings. Config is in `setup.cfg`.

### Tests

```
python -m pytest unit_tests/ -v
```

**Known test failures (pre-existing, not environment issues):**

- `test_alpaca_downloader.py` — requires Alpaca API keys (`ALPACA_API_KEY`, `ALPACA_API_SECRET`) which are not configured; these tests always fail without real credentials.
- `test_core.py::test_download_large` — asserts an exact row count from Yahoo Finance that drifts as tickers are delisted/added (e.g., WBA was removed from DOW 30).

### Web dashboard (`web/`)

Static Chart.js UI reads **`web/data.json`** from **`python web/build_data.py`** (see **`web/README.md`**). **`build_data.py`** prepends **`web/`** to **`sys.path`** before the repo root so **`web/simulations`** is imported reliably.

### Running the FinRL pipeline

There is no long-running server to start. The core workflow is: **download data → feature engineer → build gym env → train DRL agent → test/trade**.

When constructing a `StockTradingEnv`, the processed DataFrame index must be set to factorized date values:

```python
processed = processed.sort_values(['date', 'tic'], ignore_index=True)
processed.index = processed['date'].factorize()[0]
```

This is required because the environment uses `self.df.loc[self.day, :]` for indexing.

### System dependencies

The TA-Lib C library and `swig` must be installed at the system level before `pip install`. These are pre-installed in the current VM snapshot. If re-installing from scratch:

- `swig`: `apt-get install -y swig`
- TA-Lib C lib: download from https://github.com/TA-Lib/ta-lib/releases, `./configure && make && make install && ldconfig`
- SDL2 + portmidi: `apt-get install -y libsdl2-dev libportmidi-dev python3-dev` (needed if `pygame` must compile from source)

### Dependency notes

- `elegantrl` must be installed with `--no-deps` to avoid a broken `pygame` source build chain; its actual runtime deps (torch, numpy, etc.) are already satisfied by the other requirements.
- The codebase uses both `gym` (legacy) and `gymnasium` — some environments import `gym`, others use `gymnasium`. Both must be installed.
- `pygame-ce` (community edition) is installed instead of `pygame` since the original package fails to build on Python 3.12.
