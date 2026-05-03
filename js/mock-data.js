/* Mock Data — Financial & Analytics Generators */
const MockData = (() => {

  /* ── OHLC Candle Data (TradingView format) ── */
  function generateCandles(symbol, count = 60) {
    const candles = [];
    let basePrice = getBasePrice(symbol);
    const now = new Date();

    for (let i = count; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split('T')[0]; /* YYYY-MM-DD */

      const open = basePrice + (Math.random() - 0.5) * basePrice * 0.02;
      const close = open + (Math.random() - 0.5) * basePrice * 0.03;
      const high = Math.max(open, close) + Math.random() * basePrice * 0.01;
      const low = Math.min(open, close) - Math.random() * basePrice * 0.01;

      candles.push({
        time: dateStr,
        open: Math.round(open * 100) / 100,
        high: Math.round(high * 100) / 100,
        low: Math.round(low * 100) / 100,
        close: Math.round(close * 100) / 100,
      });

      basePrice = close;
    }
    return candles;
  }

  /* ── Line Data (TradingView format) ── */
  function generateLine(label, count = 30) {
    const data = [];
    let value = 50 + Math.random() * 50;
    const now = new Date();

    for (let i = count; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      value += (Math.random() - 0.48) * 5;
      value = Math.max(0, Math.min(100, value));
      data.push({
        time: d.toISOString().split('T')[0],
        value: Math.round(value * 100) / 100,
      });
    }
    return { name: label, data };
  }

  /* ── Sparkline (TradingView format) ── */
  function generateSparkline(count = 30, base = 100, vol = 5) {
    const data = [];
    let value = base;
    const now = new Date();

    for (let i = count; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      value += (Math.random() - 0.48) * vol;
      data.push({
        time: d.toISOString().split('T')[0],
        value: Math.round(value * 100) / 100,
      });
    }
    return data;
  }

  /* ── Donut Data ── */
  function generateDonut() {
    const labels = ['기술주', '금융주', '소비재', '에너지', '헬스케어'];
    const values = labels.map(() => Math.round(Math.random() * 40 + 10));
    return { labels, series: values };
  }

  /* ── Scorecard ── */
  function generateScorecard(name) {
    const value = Math.round(Math.random() * 100);
    let signal, label;
    if (value >= 70) { signal = 'buy'; label = '매수'; }
    else if (value <= 30) { signal = 'sell'; label = '매도'; }
    else { signal = 'neutral'; label = '중립'; }
    return { name, value, signal, label };
  }

  /* ── Text Briefing ── */
  function generateBriefing(topic) {
    const briefings = {
      market: [
        '코스피 지수가 전일 대비 0.8% 상승하며 2,750선을 돌파했습니다.',
        '외국인 순매수세가 3거래일 연속 이어지고 있습니다.',
        'IT/반도체 섹터가 강세를 보이며 시장을 주도하고 있습니다.',
        '미 연준의 금리 동결 기조에 글로벌 증시 전반 안도 랠리.',
        '원/달러 환율 1,320원대로 하락하며 외국인 투자심리 개선.',
      ],
      stock: [
        '삼성전자, 3nm GAA 공정 양산 가속화 소식에 강세 흐름 지속.',
        '기관 매수세 유입으로 거래량 전일 대비 150% 증가.',
        '목표가 상향 리포트 3건 발행, 평균 목표가 85,000원 제시.',
        '4분기 실적 컨센서스 영업이익 8.2조원으로 상향 조정.',
        'AI 반도체 수요 증가로 HBM 관련 매출 기대감 확대.',
      ],
      ai: [
        'GPT-5 출시 이후 AI 관련 종목 평균 12% 상승.',
        'HBM4 양산 일정 앞당겨지며 관련 소재주 급등.',
        '국내 AI 데이터센터 투자 규모 전년 대비 3배 확대.',
        'AI 에이전트 도입 기업 수 전 분기 대비 40% 증가.',
        '자율주행 Level 4 상용화 임박으로 관련 센서 업체 주목.',
      ],
    };
    const items = briefings[topic] || briefings.market;
    const count = Math.floor(Math.random() * 2) + 3;
    return shuffleArray([...items]).slice(0, count);
  }

  /* ── Conflict Data ── */
  function generateConflict() {
    if (Math.random() > 0.3) return null;
    return {
      indicators: ['RSI 과매수', 'MACD 데드크로스', '볼린저 밴드 상단 이탈'],
      accuracy: Math.round(60 + Math.random() * 30),
      corrected: Math.random() > 0.5 ? '매수 유지' : '관망 전환',
    };
  }

  /* ── Helpers ── */
  function getBasePrice(symbol) {
    const prices = {
      '삼성전자': 72000, 'SK하이닉스': 185000, 'NAVER': 210000,
      '카카오': 48000, 'LG에너지솔루션': 380000,
      'AAPL': 195, 'NVDA': 880, 'MSFT': 420, 'default': 50000,
    };
    return prices[symbol] || prices.default;
  }

  function shuffleArray(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  const stockNames = ['삼성전자', 'SK하이닉스', 'NAVER', '카카오', 'LG에너지솔루션', 'NVDA', 'AAPL'];
  const indicatorNames = ['RSI', 'MACD', '볼린저밴드', 'OBV', '스토캐스틱', 'CCI', 'Williams %R'];
  function randomStock() { return stockNames[Math.floor(Math.random() * stockNames.length)]; }
  function randomIndicator() { return indicatorNames[Math.floor(Math.random() * indicatorNames.length)]; }

  return { generateCandles, generateLine, generateSparkline, generateDonut, generateScorecard, generateBriefing, generateConflict, randomStock, randomIndicator };
})();
