"""
WebSocket 실시간 시세 스트리밍
─────────────────────────────
yfinance에서 최신 가격을 가져와 1초 간격으로 전송합니다.
완전 랜덤이 아닌 실제 종가 기반 + 미세 변동 시뮬레이션.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import random
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_current_price(ticker: str) -> tuple[float, float]:
    """yfinance에서 최신 종가와 전일대비 변동률을 가져옵니다."""
    try:
        info = yf.Ticker(ticker)
        hist = info.history(period="2d")
        if hist.empty or len(hist) < 1:
            return 100.0, 0.0
        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current
        change_pct = ((current - prev) / prev) * 100 if prev else 0.0
        return current, change_pct
    except Exception as e:
        logger.warning(f"yfinance fetch failed for {ticker}: {e}")
        return 100.0, 0.0


@router.websocket("/ws/market/{ticker}")
async def ws_market(ws: WebSocket, ticker: str):
    await ws.accept()

    # 실제 가격 기준점 가져오기
    base_price, change_pct = _get_current_price(ticker)
    price = base_price

    try:
        while True:
            # 실제 종가 기반 미세 변동 (±0.15% 범위)
            fluctuation = price * random.uniform(-0.0015, 0.0015)
            price += fluctuation
            current_change = ((price - base_price) / base_price) * 100

            await ws.send_json({
                "ticker": ticker.upper(),
                "price": round(price, 2),
                "change_percent": round(current_change, 2),
                "base_price": round(base_price, 2),
            })

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {ticker}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")