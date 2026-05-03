/* ============================================================
   Templates — Preset Layout Definitions
   ============================================================ */

const Templates = (() => {

  const presets = {
    custom: {
      name: '사용자 지정',
      description: '프롬프트로 직접 위젯 추가',
      widgets: [],
    },

    basic: {
      name: '기본 분석',
      description: '캔들스틱 + RSI + 시장 브리핑',
      widgets: [
        {
          type: 'chart',
          chartType: 'candlestick',
          title: '삼성전자',
          source: 'realtime',
          gs: { x: 0, y: 0, w: 8, h: 4 },
        },
        {
          type: 'scorecard',
          title: 'RSI 지수',
          indicatorName: 'RSI',
          source: 'llm',
          gs: { x: 8, y: 0, w: 4, h: 2 },
        },
        {
          type: 'text',
          title: '시장 브리핑',
          topic: 'market',
          source: 'llm',
          gs: { x: 8, y: 2, w: 4, h: 2 },
        },
      ],
    },

    comprehensive: {
      name: '종합 대시보드',
      description: '4개 위젯 다양한 유형',
      widgets: [
        {
          type: 'chart',
          chartType: 'candlestick',
          title: 'SK하이닉스',
          source: 'realtime',
          gs: { x: 0, y: 0, w: 6, h: 3 },
        },
        {
          type: 'chart',
          chartType: 'donut',
          title: '포트폴리오 구성',
          source: 'llm',
          gs: { x: 6, y: 0, w: 6, h: 3 },
        },
        {
          type: 'scorecard',
          title: 'MACD 시그널',
          indicatorName: 'MACD',
          source: 'realtime',
          gs: { x: 0, y: 3, w: 4, h: 2 },
        },
        {
          type: 'text',
          title: 'AI 인사이트',
          topic: 'ai',
          source: 'llm',
          gs: { x: 4, y: 3, w: 8, h: 2 },
        },
      ],
    },

    trading: {
      name: '트레이딩 뷰',
      description: '대형 차트 + 스코어카드',
      widgets: [
        {
          type: 'chart',
          chartType: 'candlestick',
          title: 'NVDA',
          source: 'realtime',
          gs: { x: 0, y: 0, w: 9, h: 5 },
        },
        {
          type: 'scorecard',
          title: 'RSI',
          indicatorName: 'RSI',
          source: 'realtime',
          gs: { x: 9, y: 0, w: 3, h: 2 },
        },
        {
          type: 'scorecard',
          title: '볼린저밴드',
          indicatorName: '볼린저밴드',
          source: 'llm',
          gs: { x: 9, y: 2, w: 3, h: 2 },
        },
        {
          type: 'chart',
          chartType: 'line',
          title: 'NVDA 추세선',
          source: 'realtime',
          gs: { x: 9, y: 4, w: 3, h: 1 },
        },
      ],
    },
  };

  function getPreset(name) {
    return presets[name] || presets.custom;
  }

  function getPresetList() {
    return Object.entries(presets).map(([key, val]) => ({
      key,
      name: val.name,
      description: val.description,
    }));
  }

  return { getPreset, getPresetList };
})();
