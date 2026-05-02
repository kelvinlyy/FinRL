/**
 * Multi-strategy dashboard: reads data.json with shared + strategies, or legacy chart blob.
 */
(function () {
  const STRATEGY_COLORS = ["#3fb950", "#d29922", "#79c0ff", "#db61a2", "#a371f7"];

  const titleEl = document.getElementById("page-title");
  const metaEl = document.getElementById("page-meta");
  const toolbar = document.getElementById("toolbar");
  const strategySelect = document.getElementById("strategy-select");
  const compareAllCb = document.getElementById("compare-all");
  const macdWrap = document.getElementById("chartMacdWrap");
  const priceHeading = document.getElementById("price-heading");

  let chartPrice = null;
  let chartMacd = null;
  let chartPerf = null;

  function destroyCharts() {
    [chartPrice, chartMacd, chartPerf].forEach((c) => {
      if (c) c.destroy();
    });
    chartPrice = chartMacd = chartPerf = null;
  }

  /** Legacy single-chart data.json → shared + strategies */
  function normalizeDoc(doc) {
    if (doc.shared && doc.strategies) return doc;
    if (doc.chart) {
      const chart = doc.chart;
      const overlays =
        chart.overlay_series ||
        (chart.sma_series || []).map((x) => ({
          key: x.key,
          label: x.label,
          chart: "price",
          data: x.data,
        }));
      return {
        meta: doc.meta || {},
        shared: {
          labels: chart.labels,
          close: chart.close,
          buy_hold_value: chart.buy_hold_value,
        },
        strategies: {
          sma_crossover: {
            label: "Strategy",
            portfolio_value: chart.portfolio_value,
            overlay_series: overlays,
          },
        },
      };
    }
    throw new Error("data.json missing chart or shared/strategies");
  }

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "top", labels: { color: "#c9d1d9" } },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const v = ctx.parsed.y;
            if (v == null) return ctx.dataset.label + ": n/a";
            const canvasId = ctx.chart.canvas.id;
            const money = canvasId === "chartPerf";
            return (
              ctx.dataset.label +
              ": $" +
              v.toLocaleString(
                undefined,
                money ? { maximumFractionDigits: 0 } : { minimumFractionDigits: 2, maximumFractionDigits: 4 },
              )
            );
          },
        },
      },
    },
    scales: {
      x: {
        ticks: { maxTicksLimit: 12, color: "#8b949e" },
        grid: { color: "#21262d" },
      },
      y: {
        ticks: { color: "#8b949e" },
        grid: { color: "#21262d" },
      },
    },
  };

  function perfMoneyAxis() {
    return {
      ticks: {
        color: "#8b949e",
        callback: (v) => "$" + Number(v).toLocaleString(),
      },
      grid: { color: "#21262d" },
    };
  }

  function render(doc, selectedId, compareAll) {
    destroyCharts();

    const meta = doc.meta || {};
    const shared = doc.shared;
    const strategies = doc.strategies;
    const ids = meta.strategy_ids || Object.keys(strategies);

    if (meta.title && titleEl) titleEl.textContent = meta.title;
    if (meta.note && metaEl) metaEl.textContent = meta.note;

    const strat = strategies[selectedId];
    if (!strat) return;

    const priceOverlays = (strat.overlay_series || []).filter((s) => (s.chart || "price") === "price");
    const macdOverlays = (strat.overlay_series || []).filter((s) => s.chart === "macd");

    const priceDatasets = [
      {
        label: "Close",
        data: shared.close,
        borderColor: "#f0f6fc",
        backgroundColor: "rgba(240,246,252,0.05)",
        borderWidth: 1.2,
        pointRadius: 0,
        tension: 0.1,
        spanGaps: true,
      },
    ];
    priceOverlays.forEach((s, i) => {
      const colors = ["#58a6ff", "#d2a8ff", "#79c0ff", "#ffa657"];
      priceDatasets.push({
        label: s.label,
        data: s.data,
        borderColor: colors[i % colors.length],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.15,
        spanGaps: true,
      });
    });

    if (priceHeading) {
      priceHeading.textContent =
        macdOverlays.length && priceOverlays.length === 0 ? "Price" : "Price & overlays";
    }

    chartPrice = new Chart(document.getElementById("chartPrice"), {
      type: "line",
      data: { labels: shared.labels, datasets: priceDatasets },
      options: commonOptions,
    });

    if (macdOverlays.length) {
      macdWrap.classList.remove("hidden");
      const macdColors = ["#58a6ff", "#d29922", "#8b949e"];
      const macdDatasets = macdOverlays.map((s, i) => ({
        label: s.label,
        data: s.data,
        borderColor: macdColors[i % macdColors.length],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.12,
        spanGaps: true,
      }));
      chartMacd = new Chart(document.getElementById("chartMacd"), {
        type: "line",
        data: { labels: shared.labels, datasets: macdDatasets },
        options: commonOptions,
      });
    } else {
      macdWrap.classList.add("hidden");
    }

    let perfDatasets;
    if (compareAll && ids.length > 1) {
      perfDatasets = ids.map((id, i) => ({
        label: strategies[id].label || id,
        data: strategies[id].portfolio_value,
        borderColor: STRATEGY_COLORS[i % STRATEGY_COLORS.length],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.12,
        spanGaps: true,
      }));
      perfDatasets.push({
        label: "Buy & hold",
        data: shared.buy_hold_value,
        borderColor: "#a371f7",
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.12,
        spanGaps: true,
      });
    } else {
      perfDatasets = [
        {
          label: strat.label || selectedId,
          data: strat.portfolio_value,
          borderColor: "#3fb950",
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.12,
          spanGaps: true,
        },
        {
          label: "Buy & hold",
          data: shared.buy_hold_value,
          borderColor: "#a371f7",
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.12,
          spanGaps: true,
        },
      ];
    }

    chartPerf = new Chart(document.getElementById("chartPerf"), {
      type: "line",
      data: { labels: shared.labels, datasets: perfDatasets },
      options: {
        ...commonOptions,
        scales: {
          x: commonOptions.scales.x,
          y: perfMoneyAxis(),
        },
      },
    });
  }

  function readHashStrategy() {
    const h = (location.hash || "").replace(/^#/, "");
    const m = h.match(/strategy=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function setHashStrategy(id) {
    const base = location.pathname + location.search;
    history.replaceState(null, "", base + "#strategy=" + encodeURIComponent(id));
  }

  function wireToolbar(doc) {
    const ids = doc.meta.strategy_ids || Object.keys(doc.strategies);
    strategySelect.innerHTML = "";
    ids.forEach((id) => {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = doc.strategies[id].label || id;
      strategySelect.appendChild(opt);
    });

    let sel = readHashStrategy();
    if (!sel || !doc.strategies[sel]) sel = ids[0];
    strategySelect.value = sel;

    toolbar.hidden = false;

    compareAllCb.disabled = ids.length < 2;
    compareAllCb.checked = compareAllCb.checked && ids.length >= 2;

    function refresh() {
      const sid = strategySelect.value;
      setHashStrategy(sid);
      render(doc, sid, compareAllCb.checked);
    }

    strategySelect.onchange = refresh;
    compareAllCb.onchange = refresh;

    window.addEventListener("hashchange", () => {
      const h = readHashStrategy();
      if (h && doc.strategies[h]) {
        strategySelect.value = h;
        render(doc, h, compareAllCb.checked);
      }
    });

    render(doc, sel, compareAllCb.checked && ids.length >= 2);
  }

  fetch("data.json")
    .then((r) => {
      if (!r.ok) throw new Error(r.status + " " + r.statusText);
      return r.json();
    })
    .then((docRaw) => {
      wireToolbar(normalizeDoc(docRaw));
    })
    .catch((err) => {
      if (titleEl) titleEl.textContent = "Could not load data";
      if (metaEl) {
        metaEl.textContent =
          "Serve this folder over HTTP (see web/README.md). " + err.message;
      }
      console.error(err);
    });
})();
