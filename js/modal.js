/* ============================================================
   Modal — Smart Focus, Settings Modal, Toast System
   ============================================================ */

/* ── Toast System ── */
const Toast = (() => {
  const icons = {
    success: `<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error: `<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info: `<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  };

  function show(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
      ${icons[type] || icons.info}
      <span class="toast__text">${message}</span>
      <button class="toast__close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => { toast.classList.add('show'); });

    toast.querySelector('.toast__close').addEventListener('click', () => removeToast(toast));
    setTimeout(() => removeToast(toast), duration);
  }

  function removeToast(toast) {
    if (!toast.parentNode) return;
    toast.classList.remove('show');
    toast.classList.add('removing');
    setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 500);
  }

  return { show };
})();


/* ── Smart Focus ── */
const SmartFocus = (() => {
  let currentWidgetId = null;
  let contentClickHandler = null;

  function open(widgetId) {
    const config = Store.getWidget(widgetId);
    if (!config) return;

    currentWidgetId = widgetId;

    const overlay = document.getElementById('smart-focus');
    const content = document.getElementById('smart-focus-content');
    if (!overlay || !content) return;

    const focusId = 'focus-' + config.id;

    /* Build content with close button */
    content.innerHTML = `
      <button class="smart-focus__close" id="sf-close-btn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      ${Widget.createWidgetHTML({ ...config, id: focusId })}
    `;

    overlay.classList.add('active');

    /* Bind close button */
    document.getElementById('sf-close-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      close();
    });

    /* Remove previous listener if any */
    if (contentClickHandler) content.removeEventListener('click', contentClickHandler);

    /* Bind all widget action buttons inside focus */
    contentClickHandler = (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      e.stopPropagation();
      const action = btn.dataset.action;
      if (action === 'close' || action === 'expand') {
        close();
      } else if (action === 'refresh') {
        const bodyEl = document.getElementById(`widget-body-${focusId}`);
        if (bodyEl) {
          bodyEl.innerHTML = '';
          Charts.destroy(`chart-container-${focusId}`);
          Widget.renderBody({ ...config, id: focusId });
        }
        const timeEl = document.getElementById(`widget-time-${focusId}`);
        if (timeEl) timeEl.textContent = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        Toast.show('데이터를 새로고침했습니다.', 'info');
      } else if (action === 'dismiss-conflict') {
        const conflictEl = document.getElementById(`widget-conflict-${focusId}`);
        if (conflictEl) conflictEl.classList.remove('active');
      }
    };
    content.addEventListener('click', contentClickHandler);

    /* Render body after transition completes so container has final dimensions */
    setTimeout(() => {
      Widget.renderBody({ ...config, id: focusId });
    }, 350);

    document.body.style.overflow = 'hidden';
  }

  function close() {
    const overlay = document.getElementById('smart-focus');
    if (overlay) overlay.classList.remove('active');

    if (currentWidgetId) {
      Charts.destroy(`chart-container-focus-${currentWidgetId}`);
    }

    currentWidgetId = null;
    document.body.style.overflow = '';
  }

  function init() {
    /* Backdrop click to close */
    const backdrop = document.getElementById('smart-focus-backdrop');
    if (backdrop) backdrop.addEventListener('click', close);

    /* Static close button (initial, before first open replaces content) */
    const closeBtn = document.getElementById('smart-focus-close');
    if (closeBtn) closeBtn.addEventListener('click', close);

    /* ESC key */
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const overlay = document.getElementById('smart-focus');
        if (overlay && overlay.classList.contains('active')) {
          close();
        }
        /* Settings modal uses .open class (managed by GNB SettingsModal) */
        const settings = document.getElementById('settings-modal');
        if (settings && (settings.classList.contains('active') || settings.classList.contains('open'))) {
          settings.classList.remove('active');
          settings.classList.remove('open');
        }
      }
    });
  }

  return { open, close, init };
})();
