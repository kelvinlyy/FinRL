/**
 * Multi-strategy dashboard: reads data.json with shared + strategies, or legacy chart blob.
 */
(function () {
  /** Distinct line color for strategy index `i` when comparing `total` models (even hue spacing). */
  function perfStrategyColor(i, total) {
    const n = Math.max(total, 1);
    const hue = ((i * 360) / n) % 360;
    return `hsl(${hue}, 72%, 58%)`;
  }

  /** Fallback palette when index matters less than hue rings */
  const OVERLAY_PRICE_COLORS = [
    "#58a6ff",
    "#d2a8ff",
    "#79c0ff",
    "#ffa657",
    "#56d364",
    "#f0883e",
    "#ff7b72",
    "#e6edf3",
  ];

  const OVERLAY_INDICATOR_COLORS = [
    "#58a6ff",
    "#d29922",
    "#8b949e",
    "#79c0ff",
    "#db61a2",
    "#56d364",
    "#f0883e",
    "#a371f7",
  ];

  const titleEl = document.getElementById("page-title");
  const metaEl = document.getElementById("page-meta");
  const toolbar = document.getElementById("toolbar");
  const strategySelect = document.getElementById("strategy-select");
  const compareAllCb = document.getElementById("compare-all");
  const macdWrap = document.getElementById("chartMacdWrap");
  const priceHeading = document.getElementById("price-heading");
  const btnResetPrice = document.getElementById("reset-price-zoom");
  const btnResetIndicator = document.getElementById("reset-indicator-zoom");
  const btnResetPerf = document.getElementById("reset-perf-zoom");

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

  /** Wheel/pinch zoom + drag pan on X axis (requires hammerjs + chartjs-plugin-zoom in index.html). */
  function zoomPluginOptions() {
    return {
      zoom: {
        limits: {
          x: { min: "original", max: "original" },
          y: { min: "original", max: "original" },
        },
        pan: {
          enabled: true,
          mode: "x",
          modifierKey: null,
        },
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: "x",
          drag: { enabled: false },
        },
      },
    };
  }

  function mergeChartOptions(base, extraPlugins = {}) {
    const zp = zoomPluginOptions();
    return {
      ...base,
      plugins: {
        ...base.plugins,
        ...extraPlugins,
        zoom: {
          ...zp.zoom,
          ...(extraPlugins.zoom || {}),
        },
      },
    };
  }

  function bindReset(btn, chartGetter) {
    if (!btn) return;
    btn.onclick = () => {
      const ch = chartGetter();
      if (ch && typeof ch.resetZoom === "function") ch.resetZoom();
    };
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
            if (canvasId === "chartPerf") {
              return (
                ctx.dataset.label +
                ": $" +
                v.toLocaleString(undefined, { maximumFractionDigits: 0 })
              );
            }
            return (
              ctx.dataset.label +
              ": " +
              Number(v).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 4,
              })
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
    const indicatorOverlays = (strat.overlay_series || []).filter(
      (s) => s.chart === "indicator" || s.chart === "macd",
    );

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
      priceDatasets.push({
        label: s.label,
        data: s.data,
        borderColor: OVERLAY_PRICE_COLORS[i % OVERLAY_PRICE_COLORS.length],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.15,
        spanGaps: true,
      });
    });

    if (priceHeading) {
      priceHeading.textContent =
        indicatorOverlays.length && priceOverlays.length === 0 ? "Price" : "Price & overlays";
    }

    chartPrice = new Chart(document.getElementById("chartPrice"), {
      type: "line",
      data: { labels: shared.labels, datasets: priceDatasets },
      options: mergeChartOptions(commonOptions),
    });
    bindReset(btnResetPrice, () => chartPrice);

    if (indicatorOverlays.length) {
      macdWrap.classList.remove("hidden");
      const macdDatasets = indicatorOverlays.map((s, i) => ({
        label: s.label,
        data: s.data,
        borderColor: OVERLAY_INDICATOR_COLORS[i % OVERLAY_INDICATOR_COLORS.length],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.12,
        spanGaps: true,
      }));
      chartMacd = new Chart(document.getElementById("chartMacd"), {
        type: "line",
        data: { labels: shared.labels, datasets: macdDatasets },
        options: mergeChartOptions(commonOptions),
      });
      bindReset(btnResetIndicator, () => chartMacd);
    } else {
      macdWrap.classList.add("hidden");
    }

    let perfDatasets;
    if (compareAll && ids.length > 1) {
      perfDatasets = ids.map((id, i) => ({
        label: strategies[id].label || id,
        data: strategies[id].portfolio_value,
        borderColor: perfStrategyColor(i, ids.length),
        borderWidth: 2,
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
      options: mergeChartOptions({
        ...commonOptions,
        scales: {
          x: commonOptions.scales.x,
          y: perfMoneyAxis(),
        },
      }),
    });
    bindReset(btnResetPerf, () => chartPerf);
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
