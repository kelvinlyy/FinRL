# SMA crossover chart site (static)

Interactive charts use [Chart.js](https://www.chartjs.org/) (CDN) and load series from **`data.json`**, produced by Python in this folder.

## Contents

| File | Role |
|------|------|
| `index.html` | Page shell |
| `app.js` | Fetches `data.json`, renders charts |
| `build_data.py` | CLI: downloads data, runs backtest, writes `data.json` (optional `preview.png`) |
| `sma_backtest.py` | SMA crossover simulation |
| `sma_chart_payload.py` | JSON shape for Chart.js |
| `data.sample.json` | Example payload shape |

## 1. Generate `data.json`

From the **repository root** (FinRL env activated):

```bash
python web/build_data.py
```

Options: `--ticker`, `--start`, `--end`, `--short`, `--long`, `--output-dir` (defaults to this folder), `--png` (writes `preview.png` here).

## 2. Serve over HTTP

Browsers block `fetch('data.json')` with `file://`. Example:

```bash
cd web
python -m http.server 8765
```

Open **http://localhost:8765**

## Notes

- FinRL writes training/backtest artifacts under **`results/`** at repo root (`RESULTS_DIR` in `finrl/config.py`); that folder is **not tracked** in git.
- **`data.json`** is gitignored (regenerate locally).
- Chart.js loads from jsDelivr; offline use requires vendoring Chart.js under `web/vendor/`.
