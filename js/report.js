/* ============================================================
   Report — Analysis Report View Logic
   ============================================================ */

const Report = (() => {

  /* ── Skills.md 기반 지표 정의 ── */
  const INDICATORS = {
    RSI:        { name: 'RSI (14)',           weight: 0.25 },
    MACD:       { name: 'MACD (12,26,9)',     weight: 0.25 },
    Bollinger:  { name: '볼린저 밴드 (20,2)', weight: 0.20 },
    Volume:     { name: '거래량 추세',        weight: 0.15 },
    MA:         { name: '이동평균 (20/60)',   weight: 0.15 },
  };

  /* ── Mock Indicator Generator (Skills.md §2 기반) ── */
  function generateIndicatorData() {
    const results = {};
    for (const [key, meta] of Object.entries(INDICATORS)) {
      let value, signal, desc;
      switch (key) {
        case 'RSI':
          value = Math.round(30 + Math.random() * 50);
          signal = value >= 70 ? 'sell' : value <= 30 ? 'buy' : 'hold';
          desc = value >= 70 ? '과매수 구간 — 차익실현 매물 출회 가능' :
                 value <= 30 ? '과매도 구간 — 반등 가능성' :
                 '중립 구간 — 추세 관찰 필요';
          break;
        case 'MACD':
          value = (Math.random() * 4 - 2).toFixed(2);
          signal = value > 0 ? 'buy' : 'sell';
          desc = value > 0 ? '골든크로스 — MACD가 시그널선 상회' :
                 '데드크로스 — MACD가 시그널선 하회';
          break;
        case 'Bollinger':
          const pos = ['상단 돌파', '중심선 부근', '하단 접근'][Math.floor(Math.random() * 3)];
          value = pos;
          signal = pos === '상단 돌파' ? 'sell' : pos === '하단 접근' ? 'buy' : 'hold';
          desc = pos === '상단 돌파' ? '밴드 상단 이탈 — 변동성 확대 주의' :
                 pos === '하단 접근' ? '밴드 하단 지지 — 반등 기대' :
                 '밴드 중심선 — 방향성 미확정';
          break;
        case 'Volume':
          value = (80 + Math.random() * 60).toFixed(0) + '%';
          signal = parseInt(value) > 120 ? 'buy' : parseInt(value) < 80 ? 'sell' : 'hold';
          desc = parseInt(value) > 120 ? '거래량 급증 — 세력 유입 가능성' :
                 parseInt(value) < 80 ? '거래량 감소 — 관심도 하락' :
                 '평균 수준의 거래량';
          break;
        case 'MA':
          const maPos = ['정배열', '역배열', '수렴'][Math.floor(Math.random() * 3)];
          value = maPos;
          signal = maPos === '정배열' ? 'buy' : maPos === '역배열' ? 'sell' : 'hold';
          desc = maPos === '정배열' ? '단기 > 중기 > 장기 — 상승 추세' :
                 maPos === '역배열' ? '장기 > 중기 > 단기 — 하락 추세' :
                 '이동평균 수렴 — 변곡점 임박';
          break;
      }
      results[key] = { ...meta, value, signal, desc };
    }
    return results;
  }

  /* ── Skills.md §2.2 투자 점수 환산 ── */
  function calculateScore(indicators) {
    const signalToScore = { buy: 80, sell: 20, hold: 50 };
    let totalWeighted = 0;
    let totalWeight = 0;
    for (const [, data] of Object.entries(indicators)) {
      totalWeighted += signalToScore[data.signal] * data.weight;
      totalWeight += data.weight;
    }
    return Math.round(totalWeighted / totalWeight);
  }

  /* ── Skills.md §2.3 점수 → 신호 변환 ── */
  function scoreToSignal(score) {
    if (score >= 80) return { signal: 'strong_buy', label: '적극 매수', color: '#16a34a' };
    if (score >= 60) return { signal: 'buy', label: '매수', color: '#22c55e' };
    if (score >= 40) return { signal: 'hold', label: '관망', color: '#eab308' };
    if (score >= 20) return { signal: 'sell', label: '매도', color: '#f97316' };
    return { signal: 'strong_sell', label: '적극 매도', color: '#ef4444' };
  }

  /* ── Skills.md §5.1 3줄 브리핑 생성 ── */
  function generateInsights(symbol, score, signalInfo) {
    const insights = [
      `${symbol} 종합 투자 점수 ${score}점으로 "${signalInfo.label}" 판단. 기술적 지표 기반 분석 결과입니다.`,
      `현재 주요 지표 중 다수가 ${score >= 50 ? '긍정적 신호' : '부정적 신호'}를 나타내고 있으며, 시장 전반의 흐름과 함께 해석할 필요가 있습니다.`,
      `단기적으로 ${score >= 60 ? '추가 상승 여력이 존재하나 과매수 구간 진입 시 주의' : score >= 40 ? '방향성 확인 후 포지션 진입 권장' : '하방 리스크 관리에 집중'}이 필요합니다.`,
    ];
    return insights;
  }

  /* ── 충돌 감지 (Skills.md §5.3) ── */
  function detectConflict(indicators) {
    const signals = Object.values(indicators).map(i => i.signal);
    const hasBuy = signals.includes('buy');
    const hasSell = signals.includes('sell');
    if (!hasBuy || !hasSell) return null;

    const buyIndicators = Object.entries(indicators).filter(([, d]) => d.signal === 'buy').map(([, d]) => d.name);
    const sellIndicators = Object.entries(indicators).filter(([, d]) => d.signal === 'sell').map(([, d]) => d.name);
    const accuracy = 60 + Math.floor(Math.random() * 25);

    return {
      conflict: true,
      buyIndicators,
      sellIndicators,
      accuracy,
      corrected: accuracy > 70 ? '매수 유지' : '관망 전환',
      reasoning: `과거 유사 패턴 분석 결과, 현재 조합에서 ${accuracy}% 확률로 ${accuracy > 70 ? '상승' : '횡보'} 추세가 확인됩니다.`,
    };
  }

  /* ── SVG Gauge (점수 시각화) ── */
  function renderGauge(score, signalInfo) {
    const radius = 52;
    const circumference = 2 * Math.PI * radius;
    const pct = score / 100;
    const dashOffset = circumference * (1 - pct * 0.75); // 270° arc

    return `
      <svg width="140" height="140" viewBox="0 0 140 140" class="report__score-gauge">
        <circle cx="70" cy="70" r="${radius}" fill="none" stroke="rgba(209,205,199,0.2)" stroke-width="10"
                stroke-dasharray="${circumference * 0.75} ${circumference * 0.25}"
                transform="rotate(135 70 70)" stroke-linecap="round"/>
        <circle cx="70" cy="70" r="${radius}" fill="none" stroke="${signalInfo.color}" stroke-width="10"
                stroke-dasharray="${circumference * 0.75 - dashOffset} ${circumference - (circumference * 0.75 - dashOffset)}"
                transform="rotate(135 70 70)" stroke-linecap="round"
                style="transition: stroke-dasharray 1s ease"/>
        <text x="70" y="65" text-anchor="middle" fill="${signalInfo.color}" font-size="28" font-weight="700"
              font-family="Sofia Sans, sans-serif">${score}</text>
        <text x="70" y="85" text-anchor="middle" fill="${signalInfo.color}" font-size="12" font-weight="600"
              font-family="Sofia Sans, sans-serif">${signalInfo.label}</text>
      </svg>`;
  }

  /* ── Main Render ── */
  function render() {
    const container = document.getElementById('report-content');
    if (!container) return;

    /* Check if dashboard has any active widgets */
    const widgetState = typeof Grid !== 'undefined' ? Grid.serializeState() : null;
    const hasWidgets = widgetState && widgetState.widgets && widgetState.widgets.length > 0;

    if (!hasWidgets) {
      container.innerHTML = `
        <div class="report__empty">
          <div class="report__empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <div class="report__empty-title">분석 리포트가 없습니다</div>
          <div class="report__empty-subtitle">
            대시보드에서 위젯을 추가한 후<br>리포트 탭을 다시 확인하세요
          </div>
        </div>`;
      return;
    }

    /* Generate analysis data (Skills.md based) */
    const symbol = widgetState.widgets[0]?.title || '종합 분석';
    const now = new Date();
    const dateStr = now.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
    const timeStr = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

    const indicators = generateIndicatorData();
    const score = calculateScore(indicators);
    const signalInfo = scoreToSignal(score);
    const insights = generateInsights(symbol, score, signalInfo);
    const conflict = detectConflict(indicators);

    /* Market overview data (from Landing INDICES) */
    const marketData = [
      { name: 'KOSPI', value: '2,665', change: '+0.58%', dir: 'up' },
      { name: 'KOSDAQ', value: '873', change: '-0.32%', dir: 'down' },
      { name: 'NASDAQ', value: '18,245', change: '+1.12%', dir: 'up' },
      { name: 'S&P 500', value: '5,842', change: '+0.45%', dir: 'up' },
      { name: 'DOW', value: '42,580', change: '-0.18%', dir: 'down' },
      { name: 'USD/KRW', value: '1,380.50', change: '-0.17%', dir: 'down' },
    ];

    container.innerHTML = `
      <!-- Report Header -->
      <div class="report__header">
        <div class="report__header-top">
          <div>
            <h1 class="report__title">${symbol} 분석 리포트</h1>
            <div class="report__meta">
              <span>📅 ${dateStr} ${timeStr}</span>
              <span>📊 위젯 ${widgetState.widgets.length}개 분석</span>
              <span class="report__badge report__badge--ai">🤖 AI 생성</span>
            </div>
          </div>
          <button class="report__export-btn" onclick="Report.exportPrint()">📄 인쇄/PDF</button>
        </div>
      </div>

      <!-- Market Overview -->
      <div class="report__section">
        <h2 class="report__section-title">시장 개요</h2>
        <div class="report__market-grid">
          ${marketData.map(m => `
            <div class="report__market-item">
              <div class="report__market-name">${m.name}</div>
              <div class="report__market-value">${m.value}</div>
              <div class="report__market-change ${m.dir}">${m.change}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Indicator Analysis -->
      <div class="report__section">
        <h2 class="report__section-title">기술적 지표 분석</h2>
        <div class="report__indicators">
          ${Object.entries(indicators).map(([key, data]) => `
            <div class="report__indicator-card">
              <div class="report__indicator-name">${data.name}</div>
              <div class="report__indicator-row">
                <span class="report__indicator-value">${data.value}</span>
                <span class="report__indicator-signal ${data.signal}">${
                  data.signal === 'buy' ? '매수' : data.signal === 'sell' ? '매도' : '관망'
                }</span>
              </div>
              <div class="report__indicator-desc">${data.desc}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Investment Score -->
      <div class="report__section">
        <h2 class="report__section-title">종합 투자 점수</h2>
        <div class="report__score-container">
          ${renderGauge(score, signalInfo)}
          <div class="report__score-info">
            <div class="report__score-value" style="color:${signalInfo.color}">${score}<span style="font-size:20px;color:var(--text-muted)">/100</span></div>
            <div class="report__score-label" style="color:${signalInfo.color}">${signalInfo.label}</div>
            <div class="report__score-desc">
              RSI(${indicators.RSI.weight * 100}%), MACD(${indicators.MACD.weight * 100}%),
              볼린저(${indicators.Bollinger.weight * 100}%), 거래량(${indicators.Volume.weight * 100}%),
              이동평균(${indicators.MA.weight * 100}%) 가중 합산
            </div>
          </div>
        </div>
      </div>

      <!-- AI Insights -->
      <div class="report__section">
        <h2 class="report__section-title">AI 인사이트</h2>
        <div class="report__insights">
          ${insights.map((text, i) => `
            <div class="report__insight-item">
              <span class="report__insight-bullet">${i + 1}</span>
              <span>${text}</span>
            </div>
          `).join('')}
        </div>
      </div>

      ${conflict ? `
      <!-- Conflict Watchdog -->
      <div class="report__section report__conflict">
        <div class="report__conflict-header">
          ⚠️ 신호 충돌 감지 (Conflict Watchdog)
        </div>
        <div class="report__conflict-items">
          <div>📈 매수 신호: ${conflict.buyIndicators.join(', ')}</div>
          <div>📉 매도 신호: ${conflict.sellIndicators.join(', ')}</div>
        </div>
        <div class="report__conflict-result">
          🎯 AI 보정 결과: <strong>${conflict.corrected}</strong> (적중률 ${conflict.accuracy}%)<br>
          <span style="font-weight:400;font-size:13px;color:var(--text-secondary)">${conflict.reasoning}</span>
        </div>
      </div>
      ` : ''}

      <!-- Disclaimer -->
      <div class="report__disclaimer">
        ⚖️ 본 분석은 AI 기반 자동 생성 결과이며, 투자 자문이 아닙니다. 투자 판단의 책임은 투자자 본인에게 있습니다.
      </div>
    `;
  }

  function exportPrint() {
    window.print();
  }

  return { render, exportPrint };
})();
