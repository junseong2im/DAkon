# DeepSR — Backend API Specification v1.0

> **프론트엔드 ↔ 백엔드 연동 명세서**
> 
> 최종 업데이트: 2026-05-03
> 
> 이 문서는 프론트엔드에서 필요한 모든 API 엔드포인트를 정의합니다.
> 백엔드 팀은 이 스펙에 맞춰 REST API를 구현해 주세요.

---

## 0. 공통 사항

### Base URL
```
Production: https://api.deepsr.com/v1
Development: http://localhost:8000/v1
```

### 인증 방식
```
Authorization: Bearer <JWT_TOKEN>
```
- 프론트엔드에서 BYOK(Bring Your Own Key) 방식으로 LLM/Market API 키를 localStorage에 저장합니다.
- 서버로 전달이 필요한 경우, 요청 헤더의 `X-LLM-Key` / `X-Market-Key` 커스텀 헤더를 사용합니다.

### 공통 응답 형식
```json
{
  "status": "success" | "error",
  "data": { ... },
  "message": "설명 메시지 (에러 시)",
  "timestamp": "2026-05-03T14:00:00+09:00"
}
```

### 에러 코드
| HTTP 코드 | 의미 | 설명 |
|-----------|------|------|
| 200 | OK | 정상 응답 |
| 400 | Bad Request | 잘못된 파라미터 |
| 401 | Unauthorized | 인증 실패 / API 키 누락 |
| 404 | Not Found | 리소스 없음 |
| 429 | Too Many Requests | API 호출 한도 초과 |
| 500 | Internal Server Error | 서버 내부 오류 |

---

## 1. 시장 데이터 API

### 1.1 OHLCV (캔들스틱 데이터)

프론트엔드 사용처: `Charts.createCandlestick()`, `Widget.renderChart()`

```
GET /market/ohlcv
```

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|----------|------|------|------|------|
| `symbol` | string | ✅ | 종목 심볼 | `005930` (삼성전자), `AAPL` |
| `market` | string | ✅ | 시장 코드 | `KR`, `US`, `JP`, `HK` |
| `interval` | string | | 캔들 간격 | `5m`, `15m`, `1h`, `1d` (기본값: `1d`) |
| `count` | number | | 데이터 포인트 수 | 60 (기본값) |
| `from` | string | | 시작일 (ISO 8601) | `2026-01-01` |
| `to` | string | | 종료일 (ISO 8601) | `2026-05-03` |

**Response**
```json
{
  "status": "success",
  "data": {
    "symbol": "005930",
    "market": "KR",
    "name": "삼성전자",
    "currency": "KRW",
    "candles": [
      {
        "time": "2026-04-01",
        "open": 72000,
        "high": 73500,
        "low": 71800,
        "close": 73200,
        "volume": 12500000
      }
    ]
  }
}
```

> **프론트 매핑**: `data.candles` → `Charts.createCandlestick(id, candles)`
> TradingView Lightweight Charts v5 포맷과 동일합니다. `time`은 `YYYY-MM-DD` 문자열.

---

### 1.2 실시간 시세 (글로벌 지수)

프론트엔드 사용처: `Landing.renderIndices()`, `Landing.renderFX()`

```
GET /market/indices
```

**Response**
```json
{
  "status": "success",
  "data": {
    "indices": [
      {
        "key": "kospi",
        "name": "KOSPI",
        "country": "KR",
        "value": 2665.42,
        "change": 15.28,
        "changePct": 0.58,
        "direction": "up",
        "sparkline": [
          { "time": "2026-04-01", "value": 2630.5 },
          { "time": "2026-04-02", "value": 2645.2 }
        ]
      }
    ],
    "fx": [
      {
        "pair": "USD/KRW",
        "rate": 1380.50,
        "change": -2.30,
        "changePct": -0.17,
        "direction": "down"
      }
    ]
  }
}
```

---

### 1.3 시가총액 Top N

프론트엔드 사용처: `Landing.renderTop5Tables()`

```
GET /market/top
```

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|----------|------|------|------|------|
| `market` | string | ✅ | 시장 코드 | `kospi`, `kosdaq`, `nasdaq`, `sp500` |
| `limit` | number | | 상위 N개 | 5 (기본값) |

**Response**
```json
{
  "status": "success",
  "data": {
    "market": "kospi",
    "stocks": [
      {
        "rank": 1,
        "name": "삼성전자",
        "symbol": "005930",
        "price": 61200,
        "changePct": -1.28,
        "marketCap": "364.5조",
        "volume": "1.2조"
      }
    ]
  }
}
```

---

## 2. LLM 분석 API

### 2.1 기술적 지표 분석

프론트엔드 사용처: `Report.generateIndicatorData()`, `Widget.renderScorecard()`

```
POST /analysis/indicators
```

**Request Body**
```json
{
  "symbol": "005930",
  "market": "KR",
  "indicators": ["RSI", "MACD", "Bollinger", "Volume", "MA"],
  "period": "3M"
}
```

**Response**
```json
{
  "status": "success",
  "data": {
    "symbol": "005930",
    "name": "삼성전자",
    "indicators": {
      "RSI": {
        "name": "RSI (14)",
        "value": 48,
        "signal": "hold",
        "weight": 0.25,
        "description": "중립 구간 — 추세 관찰 필요"
      },
      "MACD": {
        "name": "MACD (12,26,9)",
        "value": -0.59,
        "signal": "sell",
        "weight": 0.25,
        "description": "데드크로스 — MACD가 시그널선 하회"
      },
      "Bollinger": {
        "name": "볼린저 밴드 (20,2)",
        "value": "하단 접근",
        "signal": "buy",
        "weight": 0.20,
        "description": "밴드 하단 지지 — 반등 기대"
      },
      "Volume": {
        "name": "거래량 추세",
        "value": "83%",
        "signal": "hold",
        "weight": 0.15,
        "description": "평균 수준의 거래량"
      },
      "MA": {
        "name": "이동평균 (20/60)",
        "value": "수렴",
        "signal": "hold",
        "weight": 0.15,
        "description": "이동평균 수렴 — 변곡점 임박"
      }
    },
    "compositeScore": 49,
    "compositeSignal": "hold",
    "compositeLabel": "관망"
  }
}
```

> **프론트 매핑**: `data.indicators` → `Report` 뷰의 기술적 지표 카드에 직접 매핑.
> `data.compositeScore` → SVG 게이지 점수.

---

### 2.2 AI 인사이트 생성

프론트엔드 사용처: `Report.generateInsights()`, `Widget.renderTextBriefing()`

```
POST /analysis/insights
```

**Request Body**
```json
{
  "symbol": "005930",
  "market": "KR",
  "topic": "market",
  "compositeScore": 49,
  "indicators": { "RSI": "hold", "MACD": "sell", "Bollinger": "buy" }
}
```

**Response**
```json
{
  "status": "success",
  "data": {
    "insights": [
      "삼성전자 종합 투자 점수 49점으로 \"관망\" 판단. 기술적 지표 기반 분석 결과입니다.",
      "현재 주요 지표 중 다수가 부정적 신호를 나타내고 있으며, 시장 전반의 흐름과 함께 해석할 필요가 있습니다.",
      "단기적으로 방향성 확인 후 포지션 진입 권장이 필요합니다."
    ],
    "conflict": {
      "detected": true,
      "buyIndicators": ["볼린저 밴드 (20,2)"],
      "sellIndicators": ["MACD (12,26,9)"],
      "accuracy": 86,
      "corrected": "관망 전환",
      "reasoning": "과거 유사 패턴 분석 결과, 현재 조합에서 86% 확률로 횡보 추세가 확인됩니다."
    }
  }
}
```

> **프론트 매핑**: `data.insights` → 3줄 브리핑 출력.
> `data.conflict` → Conflict Watchdog 섹션 표시 (null이면 숨김).

---

### 2.3 자연어 프롬프트 분석

프론트엔드 사용처: `Prompt.parseCommand()` — 현재 프론트 로컬 파싱, 향후 서버 위임 가능

```
POST /analysis/prompt
```

**Request Body**
```json
{
  "input": "삼성전자 차트 보여줘",
  "context": {
    "activeWidgets": ["widget-1", "widget-2"],
    "template": "custom"
  }
}
```

**Response**
```json
{
  "status": "success",
  "data": {
    "widgetConfig": {
      "type": "chart",
      "chartType": "candlestick",
      "title": "삼성전자",
      "symbol": "005930",
      "market": "KR",
      "source": "realtime",
      "gs": { "w": 6, "h": 4 }
    },
    "suggestedFollowups": [
      "RSI 분석",
      "시장 브리핑",
      "포트폴리오 구성"
    ]
  }
}
```

---

## 3. 포트폴리오 API

### 3.1 섹터별 비중 (도넛 차트)

프론트엔드 사용처: `MockData.generateDonut()` → `Widget.renderDonutFallback()`

```
GET /portfolio/sectors
```

**Response**
```json
{
  "status": "success",
  "data": {
    "labels": ["기술주", "금융주", "소비재", "에너지", "헬스케어"],
    "series": [35, 22, 18, 15, 10]
  }
}
```

---

### 3.2 종목 비교 (바 차트)

프론트엔드 사용처: `Prompt` 파싱 — `비교/수익률` 패턴

```
POST /portfolio/compare
```

**Request Body**
```json
{
  "symbols": ["005930", "000660", "AAPL"],
  "period": "3M",
  "metric": "return"
}
```

**Response**
```json
{
  "status": "success",
  "data": {
    "comparisons": [
      { "symbol": "005930", "name": "삼성전자", "return": -2.5, "color": "#ef4444" },
      { "symbol": "000660", "name": "SK하이닉스", "return": 8.3, "color": "#22c55e" },
      { "symbol": "AAPL", "name": "Apple", "return": 5.1, "color": "#22c55e" }
    ]
  }
}
```

---

## 4. WebSocket (실시간)

### 4.1 실시간 시세 스트림

프론트엔드 사용처: `WebSocketSim` → 향후 실제 WS 연결

```
WS /ws/realtime
```

**Subscribe Message**
```json
{
  "action": "subscribe",
  "channels": ["kospi", "kosdaq", "nasdaq"],
  "symbols": ["005930", "AAPL"]
}
```

**Server Push**
```json
{
  "type": "tick",
  "symbol": "005930",
  "data": {
    "time": "2026-05-03T14:30:00+09:00",
    "price": 61250,
    "change": 50,
    "changePct": 0.08,
    "volume": 125000
  }
}
```

**Connection Status**
```json
{ "type": "status", "status": "connected" }
{ "type": "status", "status": "disconnected", "reason": "heartbeat_timeout" }
```

> **프론트 매핑**: `Charts.appendPoint(id, { time, value })` 로 실시간 업데이트.
> `Store.setWsStatus(status)` 로 GNB 연결 상태 배지 업데이트.

---

## 5. 사용자 설정 API

### 5.1 설정 저장/조회

프론트엔드 사용처: `GNB > SettingsModal` — 현재 localStorage, 향후 서버 동기화

```
GET  /user/settings
POST /user/settings
```

**Request/Response Body**
```json
{
  "llmProvider": "openai",
  "llmModel": "gpt-4o",
  "marketProvider": "alpha_vantage",
  "theme": "light",
  "defaultMarket": "KR",
  "defaultPeriod": "3M"
}
```

> **참고**: API 키는 BYOK 정책상 서버에 저장하지 않습니다.
> 프론트엔드 localStorage에만 암호화 저장됩니다.

---

## 6. 프론트엔드 → 백엔드 교체 가이드

현재 프론트엔드는 `mock-data.js`로 모든 데이터를 로컬 생성합니다.
백엔드 API가 준비되면 아래 함수들을 교체하세요:

| 현재 Mock 함수 | 교체할 API | 파일 |
|----------------|-----------|------|
| `MockData.generateCandles(symbol)` | `GET /market/ohlcv?symbol=...` | `widget.js` L74 |
| `MockData.generateLine(label)` | `GET /market/ohlcv?interval=1d` | `widget.js` L79 |
| `MockData.generateDonut()` | `GET /portfolio/sectors` | `widget.js` L84 |
| `MockData.generateScorecard(name)` | `POST /analysis/indicators` | `widget.js` L111 |
| `MockData.generateBriefing(topic)` | `POST /analysis/insights` | `widget.js` L134 |
| `MockData.generateConflict()` | `POST /analysis/insights` (conflict 필드) | `widget.js` L61 |
| `Landing` 지수/환율/Top5 (하드코딩) | `GET /market/indices`, `GET /market/top` | `landing.js` |
| `Report` 지표 생성 (로컬) | `POST /analysis/indicators` | `report.js` L17 |
| `Prompt.parseCommand()` (로컬 regex) | `POST /analysis/prompt` (선택사항) | `prompt.js` L124 |
| `WebSocketSim` (시뮬레이터) | `WS /ws/realtime` | `websocket.js` |

---

## 7. 환경 변수

### 백엔드 서버

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `PORT` | 서버 포트 | `8000` |
| `DATABASE_URL` | DB 연결 문자열 | `postgresql://...` |
| `REDIS_URL` | 캐시 서버 | `redis://localhost:6379` |
| `OPENAI_API_KEY` | OpenAI (서버 프록시 시) | `sk-...` |
| `ALPHA_VANTAGE_KEY` | 시장 데이터 | `...` |
| `CORS_ORIGINS` | 허용 도메인 | `http://localhost:3456` |

### 프론트엔드 (localStorage)

| 키 | 설명 |
|----|------|
| `deepsr_settings` | JSON: llmProvider, llmModel, llmKey, marketProvider, marketKey |
| `deepsr_api_key` | 레거시 단일키 (하위호환) |

---

> **이 문서는 프론트엔드 팀이 작성했습니다.**
> 백엔드 팀은 위 스펙에 맞춰 API를 구현한 뒤, 프론트의 `mock-data.js` 호출부를 `fetch()` 호출로 교체하면 됩니다.
