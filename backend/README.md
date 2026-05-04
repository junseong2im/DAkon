# DeepSR Backend

## 실행 방법

```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

접속: http://127.0.0.1:8000/docs

## Render 배포

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Root Directory**: `backend`

## API 목록

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 서버 상태 확인 |
| GET | `/api/v1/market/ohlcv?symbol=AAPL` | OHLCV 캔들 데이터 |
| POST | `/api/v1/query` | 자연어 질의 파싱 |
| POST | `/api/v1/analysis/indicators` | 6종 기술적 지표 + 스코어링 |
| POST | `/api/v1/analysis/insights` | LLM 투자 인사이트 |
| WS | `/ws/market/{ticker}` | 실시간 시세 스트리밍 |

## AI 사용 방법

Header에 API 키 추가:
```
X-LLM-Key: sk-본인키
```
