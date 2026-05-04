/* ============================================================
   Store — Global State Management
   ============================================================ */

const Store = (() => {
  const state = {
    widgets: [],
    activeTemplate: 'custom',
    apiKey: localStorage.getItem('deepsr_api_key') || '',
    wsStatus: 'connected',
    nextWidgetId: 1,
  };

  const API_BASE = 'https://dakon.onrender.com';
  const WS_BASE = 'wss://dakon.onrender.com';

  const listeners = {};

  function on(event, callback) {
    if (!listeners[event]) listeners[event] = [];
    listeners[event].push(callback);
  }

  function emit(event, data) {
    (listeners[event] || []).forEach(cb => cb(data));
  }

  function getState() {
    return { ...state };
  }

  function addWidget(config) {
    const widget = {
      id: `widget-${state.nextWidgetId++}`,
      ...config,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    state.widgets.push(widget);
    emit('widget:added', widget);
    emit('widgets:changed', state.widgets);
    return widget;
  }

  function removeWidget(id) {
    state.widgets = state.widgets.filter(w => w.id !== id);
    emit('widget:removed', { id });
    emit('widgets:changed', state.widgets);
  }

  function updateWidget(id, updates) {
    const widget = state.widgets.find(w => w.id === id);
    if (widget) {
      Object.assign(widget, updates, { updatedAt: new Date() });
      emit('widget:updated', widget);
    }
  }

  function getWidget(id) {
    return state.widgets.find(w => w.id === id);
  }

  function clearWidgets() {
    state.widgets = [];
    emit('widgets:cleared');
    emit('widgets:changed', state.widgets);
  }

  function setTemplate(name) {
    state.activeTemplate = name;
    emit('template:changed', name);
  }

  function setApiKey(key) {
    state.apiKey = key;
    localStorage.setItem('deepsr_api_key', key);
    emit('apikey:changed', key);
  }

  function setWsStatus(status) {
    state.wsStatus = status;
    emit('ws:status', status);
  }

  return {
    on,
    emit,
    getState,
    addWidget,
    removeWidget,
    updateWidget,
    getWidget,
    clearWidgets,
    setTemplate,
    setApiKey,
    setWsStatus,
    API_BASE,
    WS_BASE,
  };
})();
