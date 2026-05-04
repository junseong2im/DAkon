/* ============================================================
   Prompt — Command Center Input & Parsing
   ============================================================ */

const Prompt = (() => {
  let isLoading = false;

  /* ── Command patterns (Korean NLP mock) ── */
  const patterns = [
    {
      regex: /(.+?)\s*(차트|캔들|캔들스틱|주가)/i,
      handler: (match) => ({
        type: 'chart',
        chartType: 'candlestick',
        title: match[1].trim(),
        source: 'realtime',
        gs: { w: 6, h: 4 },
      }),
    },
    {
      regex: /(라인|추세|트렌드)\s*(.+)/i,
      handler: (match) => ({
        type: 'chart',
        chartType: 'line',
        title: match[2].trim() + ' 추세',
        source: 'realtime',
        gs: { w: 6, h: 3 },
      }),
    },
    {
      regex: /(도넛|포트폴리오|구성|비중)/i,
      handler: () => ({
        type: 'chart',
        chartType: 'donut',
        title: '포트폴리오 구성',
        source: 'llm',
        gs: { w: 4, h: 3 },
      }),
    },
    {
      regex: /(히트맵|상관관계|상관|correlation)/i,
      handler: () => ({
        type: 'chart',
        chartType: 'heatmap',
        title: '종목 상관관계 히트맵',
        source: 'llm',
        gs: { w: 6, h: 4 },
      }),
    },
    {
      regex: /(비교|수익률)\s*(.+)/i,
      handler: (match) => ({
        type: 'chart',
        chartType: 'bar',
        title: match[2].trim() + ' 수익률 비교',
        source: 'llm',
        gs: { w: 6, h: 3 },
      }),
    },
    {
      regex: /(섹터|업종|산업)\s*(분석|비중|구성)?/i,
      handler: () => ({
        type: 'chart',
        chartType: 'donut',
        title: '섹터별 비중 분석',
        source: 'llm',
        gs: { w: 4, h: 3 },
      }),
    },
    {
      regex: /(RSI|MACD|볼린저|스토캐스틱|CCI|OBV|Williams)/i,
      handler: (match) => ({
        type: 'scorecard',
        title: match[1].toUpperCase() + ' 분석',
        indicatorName: match[1].toUpperCase(),
        source: 'llm',
        gs: { w: 4, h: 3 },
      }),
    },
    {
      regex: /리포트\s*(생성|만들어|작성)/i,
      handler: () => {
        /* Navigate to report view */
        setTimeout(() => {
          if (typeof GNB !== 'undefined') GNB.switchView('report');
        }, 300);
        return {
          type: 'text',
          title: '분석 리포트 생성됨',
          topic: 'report',
          source: 'llm',
          gs: { w: 4, h: 2 },
        };
      },
    },
    {
      regex: /(브리핑|요약|뉴스|인사이트)/i,
      handler: (match) => {
        let topic = 'market';
        if (/AI|인공지능/i.test(match.input)) topic = 'ai';
        else if (/종목|주식/i.test(match.input)) topic = 'stock';
        return {
          type: 'text',
          title: topic === 'ai' ? 'AI 인사이트' : topic === 'stock' ? '종목 브리핑' : '시장 브리핑',
          topic,
          source: 'llm',
          gs: { w: 4, h: 3 },
        };
      },
    },
    {
      regex: /(스코어|점수|지표)\s*(.+)/i,
      handler: (match) => ({
        type: 'scorecard',
        title: match[2].trim() + ' 스코어',
        indicatorName: match[2].trim(),
        source: 'llm',
        gs: { w: 4, h: 3 },
      }),
    },
  ];

  /* ── Server API call for parsing ── */
  async function parseCommand(input) {
    const trimmed = input.trim();
    if (!trimmed) return null;
    
    try {
      const apiKey = Store.getState().apiKey;
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers['X-LLM-Key'] = apiKey;

      const res = await fetch(`${Store.API_BASE}/api/v1/query`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompt: trimmed })
      });

      if (!res.ok) throw new Error('Query API failed');
      const data = await res.json();
      
      const config = data.data;
      
      // Transform backend config to frontend widget format
      const widgets = [];
      const hasIndicators = config.required_indicators && config.required_indicators.length > 0;
      const isChartRequested = config.type === 'chart' || !hasIndicators;

      // 항상 차트는 기본으로 띄우기 (사용자 요청 반영)
      widgets.push({
        type: 'chart',
        chartType: config.chart_type || 'candlestick',
        title: input,
        ticker: config.target_ticker,
        period: config.period || '3mo',
        source: 'realtime',
        gs: { w: 6, h: 4 },
      });

      // 지표 분석(RSI 등) 요청이 있었으면 분석 카드도 같이 띄우기
      if (hasIndicators) {
        widgets.push({
          type: 'scorecard',
          title: `${config.target_ticker} 분석`,
          ticker: config.target_ticker,
          period: config.period || '3mo',
          indicators: config.required_indicators,
          source: 'realtime',
          gs: { w: 4, h: 4 },
        });
      }

      return widgets;
    } catch (e) {
      console.error(e);
      // Fallback
      return [{
        type: 'chart',
        chartType: 'candlestick',
        title: trimmed,
        ticker: 'AAPL',
        source: 'realtime',
        gs: { w: 6, h: 4 },
      }];
    }
  }

  /* ── Init ── */
  function init() {
    const inputEl = document.getElementById('prompt-input');
    const sendBtn = document.getElementById('prompt-send');
    const promptEl = document.querySelector('.prompt');

    if (!inputEl || !sendBtn) return;

    /* Send on button click */
    sendBtn.addEventListener('click', () => submit(inputEl, promptEl));

    /* Send on Enter (Shift+Enter for newline) */
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submit(inputEl, promptEl);
      }
    });

    /* Focus suggestions */
    inputEl.addEventListener('focus', () => showSuggestions(true));
    inputEl.addEventListener('blur', () => {
      setTimeout(() => showSuggestions(false), 200);
    });

    setupSuggestions(inputEl);
  }

  async function submit(inputEl, promptEl) {
    if (isLoading) return;

    const value = inputEl.value.trim();
    if (!value) return;

    /* Show loading state */
    isLoading = true;
    if (promptEl) promptEl.classList.add('loading');
    inputEl.value = '';

    const configs = await parseCommand(value);
    
    if (!configs || configs.length === 0) {
      Toast.show('명령을 이해하지 못했습니다. 다시 입력해주세요.', 'warning');
      isLoading = false;
      if (promptEl) promptEl.classList.remove('loading');
      return;
    }

    configs.forEach(config => {
      Grid.addWidget(config);
    });
    
    isLoading = false;
    if (promptEl) promptEl.classList.remove('loading');
    Toast.show(`위젯이 생성되었습니다.`, 'success');
  }

  /* ── Suggestions ── */
  function setupSuggestions(inputEl) {
    const container = document.getElementById('prompt-suggestions');
    if (!container) return;

    const suggestions = [
      { icon: '📊', text: '삼성전자 차트' },
      { icon: '📈', text: 'RSI 분석' },
      { icon: '📋', text: '시장 브리핑' },
      { icon: '🍩', text: '포트폴리오 구성' },
      { icon: '📉', text: '라인 NVDA 추세' },
    ];

    container.innerHTML = suggestions.map(s => `
      <button class="prompt__suggestion-item" data-suggestion="${s.text}">
        <span class="prompt__suggestion-icon">${s.icon}</span>
        <span>${s.text}</span>
      </button>
    `).join('');

    container.addEventListener('click', (e) => {
      const item = e.target.closest('.prompt__suggestion-item');
      if (item) {
        inputEl.value = item.dataset.suggestion;
        inputEl.focus();
        showSuggestions(false);
      }
    });
  }

  function showSuggestions(show) {
    const container = document.getElementById('prompt-suggestions');
    if (container) {
      container.classList.toggle('open', show);
    }
  }

  return { init };
})();
