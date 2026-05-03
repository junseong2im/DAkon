/* Widget — Render & Manage Individual Widget Components */
const Widget = (() => {

  const icons = {
    refresh: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`,
    expand: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>`,
    close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  };

  function createWidgetHTML(config) {
    const typeBadge = { chart: 'widget-header__type-badge--chart', scorecard: 'widget-header__type-badge--score', text: 'widget-header__type-badge--text' };
    const typeLabel = { chart: 'CHART', scorecard: 'SCORE', text: 'TEXT' };
    const sourceClass = config.source === 'realtime' ? 'widget-footer__source--realtime' : 'widget-footer__source--llm';
    const sourceLabel = config.source === 'realtime' ? 'LIVE' : 'LLM';
    const bodyClass = config.type === 'chart' ? 'widget-body widget-body--chart' : config.type === 'scorecard' ? 'widget-body widget-body--scorecard' : 'widget-body widget-body--text';

    return `
      <div class="widget" data-widget-id="${config.id}">
        <div class="widget-header">
          <div class="widget-header__left">
            <span class="widget-header__title">${config.title}</span>
            <span class="widget-header__type-badge ${typeBadge[config.type]}">${typeLabel[config.type]}</span>
          </div>
          <div class="widget-header__actions">
            <button class="widget-header__btn widget-header__btn--refresh" title="새로고침" data-action="refresh">${icons.refresh}</button>
            <button class="widget-header__btn widget-header__btn--expand" title="확대" data-action="expand">${icons.expand}</button>
            <button class="widget-header__btn widget-header__btn--close" title="닫기" data-action="close">${icons.close}</button>
          </div>
        </div>
        <div class="widget-body__wrapper">
          <div class="${bodyClass}" id="widget-body-${config.id}"></div>
          <div class="widget-conflict" id="widget-conflict-${config.id}">
            <div class="widget-conflict__inner">
              <div class="widget-conflict__icon">${icons.warning}</div>
              <div class="widget-conflict__title">신호 충돌 감지</div>
              <ul class="widget-conflict__list" id="widget-conflict-list-${config.id}"></ul>
              <div class="widget-conflict__accuracy" id="widget-conflict-accuracy-${config.id}"></div>
              <button class="widget-conflict__dismiss" data-action="dismiss-conflict" title="닫기">확인</button>
            </div>
          </div>
        </div>
        <div class="widget-footer">
          <span class="widget-footer__time" id="widget-time-${config.id}">${formatTime(new Date())}</span>
          <span class="widget-footer__source ${sourceClass}">${sourceLabel}</span>
        </div>
      </div>`;
  }

  function renderBody(config) {
    const bodyEl = document.getElementById(`widget-body-${config.id}`);
    if (!bodyEl) return;

    switch (config.type) {
      case 'chart': renderChart(bodyEl, config); break;
      case 'scorecard': renderScorecard(bodyEl, config); break;
      case 'text': renderTextBriefing(bodyEl, config); break;
    }

    /* Signal conflict (random chance) */
    const conflict = MockData.generateConflict();
    if (conflict) showConflict(config.id, conflict);
  }

  /* ── Chart — TradingView Lightweight Charts ── */
  function renderChart(el, config) {
    const chartContainerId = `chart-container-${config.id}`;
    el.innerHTML = `<div id="${chartContainerId}" style="width:100%;height:100%"></div>`;

    requestAnimationFrame(() => {
      switch (config.chartType) {
        case 'candlestick':
        default: {
          const data = MockData.generateCandles(config.title);
          Charts.createCandlestick(chartContainerId, data);
          break;
        }
        case 'line': {
          const lineResult = MockData.generateLine(config.title);
          Charts.createLine(chartContainerId, lineResult.data);
          break;
        }
        case 'donut': {
          const donut = MockData.generateDonut();
          renderDonutFallback(el, donut);
          break;
        }
      }
    });
  }

  /* Donut fallback */
  function renderDonutFallback(el, data) {
    const total = data.series.reduce((a, b) => a + b, 0);
    const colors = ['#141413', '#6B6966', '#B5B1AE', '#D4D0CD', '#E8E5E2'];
    el.innerHTML = `<div class="donut-fallback">
      ${data.labels.map((l, i) => {
        const pct = ((data.series[i] / total) * 100).toFixed(1);
        return `<div class="donut-fallback__row">
          <div class="donut-fallback__bar-wrap">
            <div class="donut-fallback__label">${l}</div>
            <div class="donut-fallback__bar"><div class="donut-fallback__fill" style="width:${pct}%;background:${colors[i]}"></div></div>
          </div>
          <span class="donut-fallback__pct">${pct}%</span>
        </div>`;
      }).join('')}
    </div>`;
  }

  function renderScorecard(el, config) {
    const data = MockData.generateScorecard(config.indicatorName || config.title);
    const circumference = 2 * Math.PI * 48;
    const offset = circumference - (data.value / 100) * circumference;
    const color = data.signal === 'buy' ? '#2D8A56' : data.signal === 'sell' ? '#C0392B' : '#696969';

    el.innerHTML = `
      <div class="scorecard__gauge-ring">
        <svg viewBox="0 0 120 120">
          <circle class="scorecard__gauge-bg" cx="60" cy="60" r="48"/>
          <circle class="scorecard__gauge-fill" cx="60" cy="60" r="48" stroke="${color}" stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}" data-target-offset="${offset}"/>
        </svg>
        <div class="scorecard__gauge-text scorecard__value--${data.signal}">${data.value}</div>
      </div>
      <span class="scorecard__label scorecard__label--${data.signal}">${data.label}</span>
      <span class="scorecard__name">${data.name}</span>`;

    requestAnimationFrame(() => {
      const fill = el.querySelector('.scorecard__gauge-fill');
      if (fill) fill.style.strokeDashoffset = offset;
    });
  }

  function renderTextBriefing(el, config) {
    const items = MockData.generateBriefing(config.topic || 'market');
    el.innerHTML = `<ul class="briefing-list">${items.map(t => `<li class="briefing-item"><span class="briefing-item__dot"></span><span class="briefing-item__text">${t}</span></li>`).join('')}</ul>`;
  }

  function showConflict(widgetId, conflict) {
    const overlay = document.getElementById(`widget-conflict-${widgetId}`);
    const list = document.getElementById(`widget-conflict-list-${widgetId}`);
    const accuracy = document.getElementById(`widget-conflict-accuracy-${widgetId}`);
    if (!overlay || !list || !accuracy) return;
    list.innerHTML = conflict.indicators.map(ind => `<li>${ind}</li>`).join('');
    accuracy.textContent = `과거 적중률: ${conflict.accuracy}% | 보정 결과: ${conflict.corrected}`;
    setTimeout(() => overlay.classList.add('active'), 800);
  }

  function dismissConflict(widgetId) {
    const overlay = document.getElementById(`widget-conflict-${widgetId}`);
    if (overlay) overlay.classList.remove('active');
  }

  function refresh(widgetId) {
    const config = Store.getWidget(widgetId);
    if (!config) return;
    Charts.destroy(`chart-container-${widgetId}`);
    const bodyEl = document.getElementById(`widget-body-${widgetId}`);
    if (bodyEl) { bodyEl.innerHTML = ''; renderBody(config); }
    const timeEl = document.getElementById(`widget-time-${widgetId}`);
    if (timeEl) timeEl.textContent = formatTime(new Date());
    dismissConflict(widgetId);
    Store.updateWidget(widgetId, { updatedAt: new Date() });
  }

  function destroyWidget(widgetId) {
    Charts.destroy(`chart-container-${widgetId}`);
  }

  function handleAction(widgetId, action) {
    switch (action) {
      case 'refresh': refresh(widgetId); Toast.show('데이터를 새로고침했습니다.', 'info'); break;
      case 'expand': SmartFocus.open(widgetId); break;
      case 'close': Grid.removeWidget(widgetId); break;
      case 'dismiss-conflict': dismissConflict(widgetId); break;
    }
  }

  function formatTime(d) {
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  }

  return { createWidgetHTML, renderBody, refresh, destroyWidget, handleAction };
})();
