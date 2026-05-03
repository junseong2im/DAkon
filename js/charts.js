/* Charts — TradingView Lightweight Charts v5 Wrapper */
const Charts = (() => {
  const instances = new Map();
  const colors = {
    ink: '#141413', textSec: '#6B6966', grid: 'rgba(20,20,19,0.06)',
    up: '#22c55e', down: '#ef4444',
    areaTop: 'rgba(20,20,19,0.12)', areaBot: 'rgba(20,20,19,0.01)',
  };

  function baseOpts(el) {
    return {
      width: el.clientWidth || 300, height: el.clientHeight || 200,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: colors.textSec, fontFamily: "'Sofia Sans', sans-serif", fontSize: 11 },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      rightPriceScale: { borderColor: colors.grid, scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderColor: colors.grid, timeVisible: false },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      handleScroll: true, handleScale: true,
    };
  }

  /* ── Candlestick Chart ── */
  function createCandlestick(id, data) {
    const el = document.getElementById(id);
    if (!el) return null;
    destroy(id); el.innerHTML = '';
    const chart = LightweightCharts.createChart(el, baseOpts(el));
    /* v5 API: use chart.addSeries() with series type */
    const s = chart.addSeries(LightweightCharts.CandlestickSeries, {
      upColor: colors.up, downColor: colors.down,
      borderUpColor: colors.up, borderDownColor: colors.down,
      wickUpColor: colors.up, wickDownColor: colors.down,
    });
    if (data?.length) { s.setData(data); chart.timeScale().fitContent(); }
    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }));
    ro.observe(el);
    instances.set(id, { chart, series: s, ro });
    return { chart, series: s };
  }

  /* ── Area / Line Chart ── */
  function createLine(id, data, opts = {}) {
    const el = document.getElementById(id);
    if (!el) return null;
    destroy(id); el.innerHTML = '';
    const chart = LightweightCharts.createChart(el, baseOpts(el));
    const s = chart.addSeries(LightweightCharts.AreaSeries, {
      lineColor: opts.lineColor || colors.ink,
      topColor: opts.topColor || colors.areaTop,
      bottomColor: opts.bottomColor || colors.areaBot,
      lineWidth: 2,
    });
    if (data?.length) { s.setData(data); chart.timeScale().fitContent(); }
    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }));
    ro.observe(el);
    instances.set(id, { chart, series: s, ro });
    return { chart, series: s };
  }

  /* ── Sparkline (minimal chart for landing page) ── */
  function createSparkline(id, data, opts = {}) {
    const el = document.getElementById(id);
    if (!el) return null;
    destroy(id); el.innerHTML = '';
    const chart = LightweightCharts.createChart(el, {
      width: el.clientWidth || 80, height: el.clientHeight || 32,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: 'transparent' },
      rightPriceScale: { visible: false }, timeScale: { visible: false },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: { mode: LightweightCharts.CrosshairMode.Hidden },
      handleScroll: false, handleScale: false,
    });
    const s = chart.addSeries(LightweightCharts.AreaSeries, {
      lineColor: opts.color || colors.ink,
      topColor: opts.topColor || 'rgba(20,20,19,0.08)',
      bottomColor: 'transparent',
      lineWidth: 1.5,
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    if (data?.length) { s.setData(data); chart.timeScale().fitContent(); }
    instances.set(id, { chart, series: s, ro: null });
    return { chart, series: s };
  }

  function destroy(id) {
    const i = instances.get(id);
    if (i) { if (i.ro) i.ro.disconnect(); try { i.chart.remove(); } catch (e) {} instances.delete(id); }
  }
  function updateData(id, data) { const i = instances.get(id); if (i?.series) { i.series.setData(data); i.chart.timeScale().fitContent(); } }
  function appendPoint(id, pt) { const i = instances.get(id); if (i?.series) i.series.update(pt); }

  return { createCandlestick, createLine, createSparkline, destroy, updateData, appendPoint };
})();
