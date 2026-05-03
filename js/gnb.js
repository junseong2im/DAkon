/* GNB — Navigation Bar Logic */
const GNB = (() => {
  let dropdownOpen = false;

  function init() {
    setupTabs();
    setupTemplateSelector();
    setupShareButton();
    setupSettingsButton();
    setupWsStatusBadge();
  }

  /* ── Tab Navigation ── */
  function setupTabs() {
    const tabs = document.querySelectorAll('.gnb__tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const view = tab.dataset.view;
        switchView(view);
      });
    });
  }

  function switchView(viewName) {
    /* Update tabs */
    document.querySelectorAll('.gnb__tab').forEach(t => t.classList.remove('active'));
    const activeTab = document.querySelector(`.gnb__tab[data-view="${viewName}"]`);
    if (activeTab) activeTab.classList.add('active');

    /* Update views */
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const activeView = document.getElementById(`view-${viewName}`);
    if (activeView) activeView.classList.add('active');

    /* Show/hide template selector */
    const templateWrapper = document.getElementById('gnb-template-wrapper');
    if (templateWrapper) {
      templateWrapper.style.display = viewName === 'dashboard' ? 'block' : 'none';
    }

    /* Initialize landing if switching to it */
    if (viewName === 'landing') {
      Landing.init();
    }
    /* Initialize report if switching to it */
    if (viewName === 'report') {
      Report.render();
    }
  }

  /* ── Template Selector ── */
  function setupTemplateSelector() {
    const btn = document.getElementById('gnb-template-btn');
    const dropdown = document.getElementById('gnb-template-dropdown');
    const nameEl = document.getElementById('gnb-template-name');
    if (!btn || !dropdown) return;

    const presets = Templates.getPresetList();
    dropdown.innerHTML = presets.map(p => `
      <button class="gnb__template-option ${p.key === 'custom' ? 'active' : ''}" data-template="${p.key}" title="${p.description}">${p.name}</button>
    `).join('');

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdownOpen = !dropdownOpen;
      dropdown.classList.toggle('open', dropdownOpen);
      btn.classList.toggle('open', dropdownOpen);
    });

    dropdown.addEventListener('click', (e) => {
      const option = e.target.closest('.gnb__template-option');
      if (!option) return;
      const key = option.dataset.template;
      const preset = presets.find(p => p.key === key);
      dropdown.querySelectorAll('.gnb__template-option').forEach(o => o.classList.remove('active'));
      option.classList.add('active');
      if (nameEl) nameEl.textContent = preset.name;
      Grid.loadTemplate(key);
      Toast.show(`"${preset.name}" 템플릿이 적용되었습니다.`, 'success');
      dropdownOpen = false;
      dropdown.classList.remove('open');
      btn.classList.remove('open');
    });

    document.addEventListener('click', () => {
      if (dropdownOpen) {
        dropdownOpen = false;
        dropdown.classList.remove('open');
        btn.classList.remove('open');
      }
    });
  }

  function setupShareButton() {
    const btn = document.getElementById('gnb-share-btn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      try {
        const state = Grid.serializeState();
        const json = JSON.stringify(state);
        const encoded = btoa(unescape(encodeURIComponent(json)));
        const url = `${window.location.origin}${window.location.pathname}?state=${encoded}`;
        await navigator.clipboard.writeText(url);
        Toast.show('대시보드 링크가 클립보드에 복사되었습니다.', 'success');
      } catch (err) {
        Toast.show('클립보드 복사에 실패했습니다.', 'error');
      }
    });
  }

  function setupSettingsButton() {
    const btn = document.getElementById('gnb-settings-btn');
    if (!btn) return;
    btn.addEventListener('click', () => SettingsModal.open());
  }

  /* ── Settings Modal (BYOK) ── */
  const SettingsModal = {
    open() {
      const modal = document.getElementById('settings-modal');
      if (!modal) return;
      modal.classList.add('open');
      this._loadSaved();
      this._bindClose();
      this._bindSave();
    },
    close() {
      const modal = document.getElementById('settings-modal');
      if (modal) modal.classList.remove('open');
    },
    _loadSaved() {
      const saved = JSON.parse(localStorage.getItem('deepsr_settings') || '{}');
      const fields = {
        'settings-llm-provider': saved.llmProvider || 'openai',
        'settings-llm-model': saved.llmModel || 'gpt-4o',
        'settings-llm-key': saved.llmKey || '',
        'settings-market-provider': saved.marketProvider || 'alpha_vantage',
        'settings-market-key': saved.marketKey || '',
      };
      for (const [id, value] of Object.entries(fields)) {
        const el = document.getElementById(id);
        if (el) el.value = value;
      }
    },
    _bindClose() {
      const closeBtn = document.getElementById('settings-close');
      const backdrop = document.getElementById('settings-backdrop');
      if (closeBtn) closeBtn.onclick = () => this.close();
      if (backdrop) backdrop.onclick = () => this.close();
    },
    _bindSave() {
      const saveBtn = document.getElementById('settings-save');
      if (!saveBtn) return;
      saveBtn.onclick = () => {
        const settings = {
          llmProvider: document.getElementById('settings-llm-provider')?.value,
          llmModel: document.getElementById('settings-llm-model')?.value,
          llmKey: document.getElementById('settings-llm-key')?.value,
          marketProvider: document.getElementById('settings-market-provider')?.value,
          marketKey: document.getElementById('settings-market-key')?.value,
        };
        localStorage.setItem('deepsr_settings', JSON.stringify(settings));
        Toast.show('설정이 저장되었습니다.', 'success');
        this.close();
      };
    },
  };

  function setupWsStatusBadge() {
    Store.on('ws:status', (status) => updateWsBadge(status));
    updateWsBadge(Store.getState().wsStatus);
  }

  function updateWsBadge(status) {
    const badge = document.getElementById('gnb-ws-badge');
    const text = document.getElementById('gnb-ws-text');
    if (!badge || !text) return;
    badge.className = 'gnb__ws-badge';
    if (status === 'connected') {
      badge.classList.add('gnb__ws-badge--connected');
      text.textContent = '연결됨';
    } else {
      badge.classList.add('gnb__ws-badge--disconnected');
      text.textContent = '끊김';
    }
  }

  return { init, switchView };
})();
