/* ============================================================
   Grid — Gridstack Management + Widget CRUD
   ============================================================ */

const Grid = (() => {
  let grid = null;

  function init() {
    grid = GridStack.init({
      column: 12,
      cellHeight: 80,
      margin: 8,
      animate: true,
      float: false,
      removable: false,
      handle: '.widget-header',
      resizable: { handles: 'se' },
      draggable: { handle: '.widget-header' },
    }, '.grid-stack');

    /* Re-render charts on resize */
    grid.on('resizestop', (event, el) => {
      const widgetId = el.getAttribute('gs-id');
      if (widgetId) {
        setTimeout(() => Widget.refresh(widgetId), 50);
      }
    });

    updateEmptyState();
  }

  function addWidget(config) {
    if (!grid) return;

    const storeWidget = Store.addWidget(config);
    const htmlContent = Widget.createWidgetHTML(storeWidget);
    const gs = config.gs || { w: 4, h: 3 };

    const el = grid.addWidget({
      id: storeWidget.id,
      w: gs.w || 4,
      h: gs.h || 3,
      x: gs.x,
      y: gs.y,
      content: htmlContent,
    });

    /* Event delegation for widget actions */
    attachWidgetEvents(el, storeWidget.id);

    /* Render body after DOM ready */
    requestAnimationFrame(() => {
      Widget.renderBody(storeWidget);
    });

    updateEmptyState();
    return storeWidget;
  }

  function removeWidget(widgetId) {
    if (!grid) return;
    Widget.destroyWidget(widgetId);
    const el = document.querySelector(`[gs-id="${widgetId}"]`);
    if (el) grid.removeWidget(el, true);
    Store.removeWidget(widgetId);
    updateEmptyState();
  }

  function clearAll() {
    if (!grid) return;
    const state = Store.getState();
    state.widgets.forEach(w => Widget.destroyWidget(w.id));
    grid.removeAll(true);
    Store.clearWidgets();
    updateEmptyState();
  }

  function loadTemplate(templateKey) {
    clearAll();
    const preset = Templates.getPreset(templateKey);
    Store.setTemplate(templateKey);
    if (preset.widgets.length === 0) { updateEmptyState(); return; }
    preset.widgets.forEach((wConfig, index) => {
      setTimeout(() => addWidget(wConfig), index * 150);
    });
  }

  function getLayout() {
    if (!grid) return [];
    return grid.save(false);
  }

  function serializeState() {
    const state = Store.getState();
    const layout = getLayout();
    return {
      template: state.activeTemplate,
      widgets: state.widgets.map(w => ({
        type: w.type, chartType: w.chartType, title: w.title,
        topic: w.topic, indicatorName: w.indicatorName, source: w.source,
      })),
      layout,
    };
  }

  /* ── Event Delegation ── */
  function attachWidgetEvents(el, widgetId) {
    el.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action]');
      if (btn) {
        e.stopPropagation();
        e.preventDefault();
        Widget.handleAction(widgetId, btn.dataset.action);
      }
    });

    /* Double-click for Smart Focus */
    el.addEventListener('dblclick', (e) => {
      if (!e.target.closest('.widget-header__actions')) {
        SmartFocus.open(widgetId);
      }
    });
  }

  /* ── Empty State ── */
  function updateEmptyState() {
    const empty = document.querySelector('.grid-canvas__empty');
    if (!empty) return;
    const widgetCount = Store.getState().widgets.length;
    empty.classList.toggle('hidden', widgetCount > 0);
  }

  return { init, addWidget, removeWidget, clearAll, loadTemplate, getLayout, serializeState };
})();
