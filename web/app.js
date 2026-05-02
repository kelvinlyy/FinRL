/**
 * Loads data.json and renders Chart.js line charts (matches chart options in this folder's prior HTML generator).
 */
(function () {
  const titleEl = document.getElementById("page-title");
  const metaEl = document.getElementById("page-meta");

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
            const id = ctx.chart.canvas.id;
            const money = id === "chartPerf";
            return (
              ctx.dataset.label +
              ": $" +
              v.toLocaleString(
                undefined,
                money ? { maximumFractionDigits: 0 } : { minimumFractionDigits: 2, maximumFractionDigits: 2 },
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

  function renderCharts(RAW, meta) {
    if (meta && meta.title && titleEl) titleEl.textContent = meta.title;
    if (meta && meta.note && metaEl) metaEl.textContent = meta.note;

    const priceDatasets = [
      {
        label: "Close",
        data: RAW.close,
        borderColor: "#f0f6fc",
        backgroundColor: "rgba(240,246,252,0.05)",
        borderWidth: 1.2,
        pointRadius: 0,
        tension: 0.1,
        spanGaps: true,
      },
    ];
    (RAW.sma_series || []).forEach((s, i) => {
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

    new Chart(document.getElementById("chartPrice"), {
      type: "line",
      data: { labels: RAW.labels, datasets: priceDatasets },
      options: commonOptions,
    });

    new Chart(document.getElementById("chartPerf"), {
      type: "line",
      data: {
        labels: RAW.labels,
        datasets: [
          {
            label: "SMA strategy",
            data: RAW.portfolio_value,
            borderColor: "#3fb950",
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.12,
            spanGaps: true,
          },
          {
            label: "Buy & hold",
            data: RAW.buy_hold_value,
            borderColor: "#a371f7",
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.12,
            spanGaps: true,
          },
        ],
      },
      options: {
        ...commonOptions,
        scales: {
          x: commonOptions.scales.x,
          y: {
            ticks: {
              color: "#8b949e",
              callback: (v) => "$" + Number(v).toLocaleString(),
            },
            grid: { color: "#21262d" },
          },
        },
      },
    });
  }

  fetch("data.json")
    .then((r) => {
      if (!r.ok) throw new Error(r.status + " " + r.statusText);
      return r.json();
    })
    .then((doc) => {
      const RAW = doc.chart || doc;
      const meta = doc.meta || {};
      renderCharts(RAW, meta);
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
