/* App — Entry Point */
document.addEventListener('DOMContentLoaded', () => {
  Grid.init();
  GNB.init();
  Prompt.init();
  SmartFocus.init();
  WebSocketSim.start();
  Landing.init();

  loadSharedState();

  setTimeout(() => {
    Toast.show('DeepSR 대시보드에 오신 것을 환영합니다.', 'info');
  }, 600);
});

function loadSharedState() {
  try {
    const params = new URLSearchParams(window.location.search);
    const encoded = params.get('state');
    if (!encoded) return;
    const json = decodeURIComponent(escape(atob(encoded)));
    const state = JSON.parse(json);
    /* Switch to dashboard view */
    GNB.switchView('dashboard');
    if (state.template && state.template !== 'custom') {
      Grid.loadTemplate(state.template);
    } else if (state.widgets && state.widgets.length > 0) {
      state.widgets.forEach((w, i) => {
        const gs = state.layout?.[i] ? { x: state.layout[i].x, y: state.layout[i].y, w: state.layout[i].w, h: state.layout[i].h } : {};
        setTimeout(() => Grid.addWidget({ ...w, gs }), i * 150);
      });
    }
    window.history.replaceState({}, '', window.location.pathname);
  } catch (e) {
    console.warn('Failed to load shared state:', e);
  }
}
