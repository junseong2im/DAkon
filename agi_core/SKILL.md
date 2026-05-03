---
name: agi-finance-analysis
description: >
  AGI 기반 금융 종목 분석 엔진. 자연어 질의를 파싱하여 종목(Ticker), 기간(Period), 차트 타입을 추출하고,
  기술적 지표(RSI, MACD, SMA, EMA, 볼린저밴드, 스토캐스틱)를 계산하며,
  지표 간 신호 충돌을 백테스트 적중률 기반 가중치로 중재하고,
  4-카테고리(기술적/재무/수급/거시) 스코어링을 통해 0~100점 투자 판단을 생성합니다.
  Use when analyzing stocks or crypto, scoring investments, parsing financial queries,
  resolving indicator conflicts, or generating buy/sell/hold signals.
license: MIT
compatibility: Requires Python 3.10+, pandas, numpy, httpx. OpenAI-compatible API key required for LLM features.
metadata:
  author: fin-dashboard-team
  version: "1.0"
  category: finance
---

# AGI Finance Analysis Skill

금융 종목 분석을 위한 AGI 코어 엔진입니다. 아래 3단계 파이프라인을 순서대로 수행합니다.

## 1. 자연어 질의 파싱

사용자의 자연어 입력을 구조화된 JSON으로 변환합니다.

### 사용법

```python
from agi_core.parser.nl_parser import parse_query_safe

# LLM 파싱 (API Key 있을 때) + 규칙 기반 폴백
result = await parse_query_safe("애플 주가 3개월치 캔들차트로 띄워줘", api_key="sk-...")

# 폴백 전용 (LLM 없이)
from agi_core.parser.nl_parser import parse_query_fallback
result = parse_query_fallback("비트코인 1년 라인차트 RSI MACD")
```

### 출력 형식

```json
{
  "target_ticker": "AAPL",
  "chart_type": "candlestick",
  "period": "3mo",
  "required_indicators": ["volume"],
  "asset_type": "stock"
}
```

### 지원 매핑

- **종목**: 한국어 → 티커 자동 변환 ("애플" → `AAPL`, "삼성전자" → `005930.KS`, "비트코인" → `BTC/USDT`)
- **기간**: "1일"→`1d`, "1주"→`5d`, "1개월"→`1mo`, "3개월"→`3mo`, "6개월"→`6mo`, "1년"→`1y`, "5년"→`5y`
- **차트**: "캔들"→`candlestick`, "라인"→`line`, "바"→`bar`, "영역"→`area`
- **지표**: "RSI", "MACD", "볼린저", "이동평균", "스토캐스틱", "거래량"

---

## 2. 기술적 지표 계산 및 충돌 분석

OHLCV DataFrame을 입력받아 지표를 계산하고, 신호 충돌을 중재합니다.

### 사용법

```python
import pandas as pd
from agi_core.engine.indicators import calculate_all_indicators
from agi_core.engine.conflict_watchdog import analyze_conflicts

# ohlcv_df는 컬럼: open, high, low, close, volume 을 가진 DataFrame
signals = calculate_all_indicators(ohlcv_df)
conflict_report = analyze_conflicts(signals)

print(conflict_report.weighted_signal)      # "BUY" / "SELL" / "HOLD"
print(conflict_report.weighted_confidence)  # 0.0 ~ 1.0
print(conflict_report.conflicts_detected)   # True / False
```

### 지원 지표 (6종)

| 지표 | 함수 | 신호 기준 |
|------|------|-----------|
| SMA | `calc_sma()` | 골든크로스 / 데드크로스 |
| EMA | `calc_ema()` | 단기 vs 장기 EMA 교차 |
| RSI | `calc_rsi()` | <30 과매도(BUY), >70 과매수(SELL) |
| MACD | `calc_macd()` | MACD-Signal 교차 |
| Bollinger | `calc_bollinger()` | %B 위치, 밴드 이탈 |
| Stochastic | `calc_stochastic()` | %K-%D 교차 + 20/80 구간 |

### 충돌 중재 로직

BUY와 SELL 신호가 동시에 존재하면 충돌로 판단합니다.
충돌 시 시장 조건(상승/하락/횡보)을 자동 감지하고, 각 지표의 **백테스트 적중률 × 신뢰도** 가중 평균으로 최종 신호를 결정합니다.

충돌 분석 결과에는 한국어 근거 텍스트가 자동 생성됩니다:

```
[시장 조건: 횡보]
총 6개 지표 분석 완료.
  매수(BUY): 2개 | 매도(SELL): 1개 | 관망(HOLD): 3개

⚠ 지표 간 신호 충돌 감지!
  → 백테스트 적중률 가중치(횡보 조건)를 적용하여 중재합니다.

▶ 최종 판단: 관망(HOLD)
  가중 신뢰도: 49.0%
```

---

## 3. 4-카테고리 스코어링

4개 카테고리(각 25점)를 합산하여 0~100점의 TotalScore를 반환합니다.

### 사용법

```python
from agi_core.engine.scoring import calculate_total_score, score_local

# LLM 종합 분석 (API Key 필요) + 로컬 폴백
result = await calculate_total_score(
    ticker="AAPL",
    indicator_signals=signals,
    api_key="sk-...",
    financial_data={"per": 15.2, "roe": 25.3, "debt_ratio": 45},
    macro_data={"vix": 18, "interest_rate_trend": "falling"},
)

# 로컬 전용 (LLM 불필요)
result = score_local("AAPL", signals)
```

### 카테고리 구성

| 카테고리 | 점수 | 데이터 소스 |
|----------|------|-------------|
| 기술적 (technical) | 0~25 | indicators + conflict_watchdog 결과 |
| 재무 (financial) | 0~25 | PER, ROE, 부채비율, 매출성장률 |
| 수급 (supply_demand) | 0~25 | 외국인/기관 순매수, 공매도, 거래량 추세 |
| 거시 (macro) | 0~25 | 금리 추세, 인플레이션, GDP, VIX |

### 최종 신호 기준

| 점수 구간 | 신호 |
|-----------|------|
| 80~100 | STRONG_BUY |
| 60~79 | BUY |
| 40~59 | HOLD |
| 20~39 | SELL |
| 0~19 | STRONG_SELL |

### 출력 형식

```json
{
  "ticker": "AAPL",
  "total_score": 60.11,
  "categories": [
    {"category": "technical", "score": 6.1, "details": "..."},
    {"category": "financial", "score": 20.0, "details": "..."},
    {"category": "supply_demand", "score": 17.0, "details": "..."},
    {"category": "macro", "score": 17.0, "details": "..."}
  ],
  "final_signal": "BUY",
  "conflict_report": "..."
}
```

---

## 전체 파이프라인 예시

아래는 자연어 입력부터 최종 스코어링까지의 E2E 흐름입니다:

```python
import pandas as pd
from agi_core.parser.nl_parser import parse_query_safe
from agi_core.engine.indicators import calculate_all_indicators
from agi_core.engine.conflict_watchdog import analyze_conflicts
from agi_core.engine.scoring import calculate_total_score

# Step 1: 자연어 파싱
parsed = await parse_query_safe("테슬라 6개월 볼린저밴드", api_key="sk-...")
# → ParsedQuery(target_ticker="TSLA", chart_type="candlestick", period="6mo", ...)

# Step 2: OHLCV 데이터 로드 (백엔드 모듈에서 제공)
ohlcv_df = pd.DataFrame(...)  # open, high, low, close, volume 컬럼

# Step 3: 지표 계산
signals = calculate_all_indicators(ohlcv_df)

# Step 4: 충돌 분석
conflict = analyze_conflicts(signals)

# Step 5: 스코어링
score = await calculate_total_score("TSLA", signals, api_key="sk-...")
print(score.to_dict())
```

---

## 파일 구조

```
agi_core/
├── SKILL.md                          # 이 파일
├── requirements.txt                  # 의존성 (httpx, numpy, pandas)
├── __init__.py
├── prompts/
│   └── system_prompts.py             # LLM System Prompt 3종
├── parser/
│   └── nl_parser.py                  # 자연어 파서 (LLM + 규칙 기반 폴백)
└── engine/
    ├── indicators.py                 # 기술적 지표 6종
    ├── conflict_watchdog.py          # 충돌 중재 엔진
    └── scoring.py                    # 4-카테고리 스코어링
```

## 주의사항

- 외부 데이터(재무/수급/거시)가 없으면 해당 카테고리는 **기본값 12.5점**(중립)으로 처리됩니다.
- LLM 기능은 **OpenAI 호환 API**(gpt-4o 기본)를 사용하며, API Key는 BYOK 방식으로 런타임에 전달합니다.
- 이 모듈은 데이터 수집(yfinance/ccxt)을 직접 수행하지 않습니다. OHLCV DataFrame은 백엔드 모듈에서 제공받습니다.
- 모듈 간 결합은 **JSON 규격**(`to_dict()` 메서드)으로만 수행합니다.
