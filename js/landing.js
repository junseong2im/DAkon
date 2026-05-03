/* Landing — Market Overview Page Logic */
const Landing = (() => {
  let clockInterval = null;

  const INDICES = [
    { key: 'kospi', name: 'KOSPI', flag: '🇰🇷', base: 2650, vol: 40 },
    { key: 'kosdaq', name: 'KOSDAQ', flag: '🇰🇷', base: 870, vol: 20 },
    { key: 'nasdaq', name: 'NASDAQ', flag: '🇺🇸', base: 18200, vol: 300 },
    { key: 'sp500', name: 'S&P 500', flag: '🇺🇸', base: 5800, vol: 80 },
    { key: 'dji', name: 'DOW', flag: '🇺🇸', base: 42500, vol: 500 },
    { key: 'nikkei', name: 'Nikkei 225', flag: '🇯🇵', base: 38000, vol: 600 },
    { key: 'hsi', name: 'Hang Seng', flag: '🇭🇰', base: 22000, vol: 400 },
    { key: 'dax', name: 'DAX', flag: '🇩🇪', base: 22500, vol: 300 },
  ];

  const FX = [
    { pair: 'USD/KRW', flag: '🇺🇸', base: 1380, vol: 15 },
    { pair: 'EUR/KRW', flag: '🇪🇺', base: 1520, vol: 18 },
    { pair: 'JPY/KRW', flag: '🇯🇵', base: 9.15, vol: 0.12, dec: 2 },
    { pair: 'CNY/KRW', flag: '🇨🇳', base: 190, vol: 3 },
    { pair: 'EUR/USD', flag: '🇪🇺', base: 1.085, vol: 0.015, dec: 4 },
    { pair: 'GBP/USD', flag: '🇬🇧', base: 1.265, vol: 0.012, dec: 4 },
  ];

  const TOP5 = {
    kospi: [
      { name: '삼성전자', price: 61200, cap: '364.5조', pct: -1.28, volume: 1.2 },
      { name: 'SK하이닉스', price: 178000, cap: '129.5조', pct: 2.45, volume: 0.9 },
      { name: 'LG에너지솔루션', price: 365000, cap: '85.4조', pct: -0.54, volume: 0.3 },
      { name: '삼성바이오로직스', price: 812000, cap: '57.8조', pct: 0.87, volume: 0.15 },
      { name: '현대자동차', price: 235500, cap: '50.2조', pct: 1.12, volume: 0.45 },
    ],
    kosdaq: [
      { name: '에코프로비엠', price: 185000, cap: '16.2조', pct: 3.21, volume: 0.85 },
      { name: '에코프로', price: 62300, cap: '12.8조', pct: -2.15, volume: 0.72 },
      { name: '알테오젠', price: 285000, cap: '10.5조', pct: 1.78, volume: 0.55 },
      { name: '셀트리온제약', price: 78500, cap: '7.2조', pct: -0.64, volume: 0.3 },
      { name: 'HLB', price: 62800, cap: '6.8조', pct: 4.52, volume: 0.9 },
    ],
    nasdaq: [
      { name: 'Apple', price: 228.5, cap: '$3.52T', pct: -0.35, volume: 48.2, usd: true },
      { name: 'Microsoft', price: 442.8, cap: '$3.29T', pct: 1.12, volume: 22.5, usd: true },
      { name: 'NVIDIA', price: 118.2, cap: '$2.89T', pct: 3.45, volume: 65.8, usd: true },
      { name: 'Amazon', price: 198.3, cap: '$2.07T', pct: 0.78, volume: 35.4, usd: true },
      { name: 'Alphabet', price: 178.9, cap: '$2.19T', pct: -1.23, volume: 18.6, usd: true },
    ],
    sp500: [
      { name: 'Apple', price: 228.5, cap: '$3.52T', pct: -0.35, volume: 48.2, usd: true },
      { name: 'Microsoft', price: 442.8, cap: '$3.29T', pct: 1.12, volume: 22.5, usd: true },
      { name: 'NVIDIA', price: 118.2, cap: '$2.89T', pct: 3.45, volume: 65.8, usd: true },
      { name: 'Berkshire', price: 525.1, cap: '$1.15T', pct: 0.22, volume: 3.2, usd: true },
      { name: 'Meta', price: 568.3, cap: '$1.43T', pct: 2.10, volume: 15.7, usd: true },
    ],
  };

  function init() {
    renderIndices();
    renderFX();
    renderTop5Tables();
    startClock();
    updateMarketStatus();
  }

  /* ── Clock ── */
  function startClock() {
    const el = document.getElementById('landing-clock');
    if (!el) return;
    function tick() {
      const now = new Date();
      const kr = now.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
      el.textContent = '🕐 ' + kr;
    }
    tick();
    clockInterval = setInterval(tick, 1000);
  }

  function updateMarketStatus() {
    const now = new Date();
    const krHour = parseInt(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul', hour: 'numeric', hour12: false }));
    const krOpen = krHour >= 9 && krHour < 15;
    const etHour = parseInt(now.toLocaleString('en-US', { timeZone: 'America/New_York', hour: 'numeric', hour12: false }));
    const usOpen = etHour >= 9 && etHour < 16;

    const krDot = document.getElementById('landing-kr-dot');
    const usDot = document.getElementById('landing-us-dot');
    const krText = document.getElementById('landing-kr-status');
    const usText = document.getElementById('landing-us-status');

    if (krDot) { krDot.className = 'landing__status-dot ' + (krOpen ? 'open' : 'closed'); }
    if (usDot) { usDot.className = 'landing__status-dot ' + (usOpen ? 'open' : 'closed'); }
    if (krText) krText.textContent = krOpen ? 'KR 장 운영중' : 'KR 장 마감';
    if (usText) usText.textContent = usOpen ? 'US 장 운영중' : 'US 장 마감';
  }

  /* ── Indices ── */
  function renderIndices() {
    const container = document.getElementById('landing-indices');
    if (!container) return;

    container.innerHTML = INDICES.map((idx, i) => {
      const change = (Math.random() - 0.45) * idx.vol;
      const pct = (change / idx.base) * 100;
      const value = idx.base + change;
      const dir = change >= 0 ? 'up' : 'down';
      const sign = change >= 0 ? '+' : '';
      const sparkId = `spark-idx-${i}`;
      return `
        <div class="index-card index-card--${dir}">
          <div class="index-card__info">
            <div class="index-card__name">${idx.flag} ${idx.name}</div>
            <div class="index-card__row">
              <span class="index-card__value">${value.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</span>
              <span class="index-card__change">${sign}${change.toFixed(2)}</span>
            </div>
            <div class="index-card__pct">${sign}${pct.toFixed(2)}%</div>
          </div>
          <div class="index-card__chart" id="${sparkId}"></div>
        </div>`;
    }).join('');

    /* Render sparklines */
    requestAnimationFrame(() => {
      INDICES.forEach((idx, i) => {
        const sparkData = MockData.generateSparkline(30, idx.base, idx.vol * 0.3);
        const isUp = document.querySelector(`#spark-idx-${i}`)?.closest('.index-card')?.classList.contains('index-card--up');
        Charts.createSparkline(`spark-idx-${i}`, sparkData, {
          color: isUp ? '#dc2626' : '#2563eb',
          topColor: isUp ? 'rgba(220,38,38,0.1)' : 'rgba(37,99,235,0.1)',
        });
      });
    });
  }

  /* ── FX ── */
  function renderFX() {
    const container = document.getElementById('landing-fx');
    if (!container) return;

    container.innerHTML = FX.map(fx => {
      const change = (Math.random() - 0.45) * fx.vol;
      const rate = fx.base + change;
      const pct = (change / fx.base) * 100;
      const dir = change >= 0 ? 'up' : 'down';
      const sign = change >= 0 ? '+' : '';
      const dec = fx.dec || 2;
      return `
        <div class="fx-card fx-card--${dir}">
          <div><span class="fx-card__flag">${fx.flag}</span><span class="fx-card__pair">${fx.pair}</span></div>
          <div class="fx-card__right">
            <div class="fx-card__rate">${rate.toLocaleString('ko-KR', { minimumFractionDigits: dec, maximumFractionDigits: dec })}</div>
            <div class="fx-card__change">${sign}${pct.toFixed(2)}%</div>
          </div>
        </div>`;
    }).join('');
  }

  /* ── Top 5 Tables ── */
  function renderTop5Tables() {
    ['kospi', 'kosdaq', 'nasdaq', 'sp500'].forEach(market => {
      const table = document.querySelector(`#landing-table-${market} tbody`);
      if (!table) return;
      const stocks = TOP5[market] || [];
      const maxVol = Math.max(...stocks.map(s => s.volume));

      table.innerHTML = stocks.map((s, i) => {
        const dir = s.pct >= 0 ? 'up' : 'down';
        const sign = s.pct >= 0 ? '+' : '';
        const priceStr = s.usd
          ? '$' + s.price.toLocaleString('en-US', { minimumFractionDigits: 1 })
          : s.price.toLocaleString('ko-KR') + '원';
        const volPct = Math.round((s.volume / maxVol) * 100);
        const volStr = s.usd
          ? '$' + s.volume.toFixed(1) + 'B'
          : s.volume.toFixed(1) + '조';
        return `<tr>
          <td>${i + 1}</td>
          <td>${s.name}</td>
          <td>${priceStr}</td>
          <td class="td--${dir}">${sign}${s.pct.toFixed(2)}%</td>
          <td>${s.cap}</td>
          <td><div class="volume-bar"><div class="volume-bar__fill" style="width:${volPct}%"></div><span class="volume-bar__text">${volStr}</span></div></td>
        </tr>`;
      }).join('');
    });
  }

  function destroy() {
    if (clockInterval) { clearInterval(clockInterval); clockInterval = null; }
  }

  return { init, destroy };
})();
