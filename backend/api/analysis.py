"""
종합 분석 API
─────────────
agi_core 엔진 연동:
  - indicators.py: 6종 기술적 지표 (SMA, EMA, RSI, MACD, Bollinger, Stochastic)
  - conflict_watchdog.py: 지표 간 충돌 중재
  - scoring.py: 4-카테고리 스코어링 (기술/재무/수급/거시)
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import yfinance as yf
import json
from openai import OpenAI

from agi_core.engine.indicators import (
    calc_sma, calc_ema, calc_rsi, calc_macd, calc_bollinger, calc_stochastic,
    calculate_all_indicators,
)
from agi_core.engine.conflict_watchdog import analyze_conflicts
from agi_core.engine.scoring import score_local

router = APIRouter()


class IndicatorRequest(BaseModel):
    symbol: str
    market: str = "US"
    indicators: list[str] = ["RSI"]
    period: str = "3mo"


class InsightRequest(BaseModel):
    symbol: str
    market: str = "US"
    topic: str = "market"
    compositeScore: int
    indicators: dict


# ─── 지표 계산 맵 ───
INDICATOR_FUNCTIONS = {
    "SMA": calc_sma,
    "EMA": calc_ema,
    "RSI": calc_rsi,
    "MACD": calc_macd,
    "BOLLINGER": calc_bollinger,
    "STOCHASTIC": calc_stochastic,
}


def _download_ohlcv(symbol: str, period: str):
    """yfinance로 OHLCV 데이터를 다운로드합니다. (재시도 포함)"""
    import pandas as pd
    import time

    for attempt in range(3):
        try:
            data = yf.download(symbol.upper(), period=period, auto_adjust=False, progress=False)
            if not data.empty:
                break
        except Exception:
            pass
        if attempt < 2:
            time.sleep(2)
    else:
        data = pd.DataFrame()

    if data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"종목 '{symbol}'의 데이터를 가져올 수 없습니다. 티커를 확인하거나 잠시 후 재시도하세요."
        )

    # MultiIndex 컬럼 처리 (yfinance 0.2.40+ 에서 ticker별 MultiIndex 반환)
    if isinstance(data.columns, pd.MultiIndex):
        data = data.droplevel("Ticker", axis=1)

    # 컬럼명 소문자 통일
    data.columns = [c.lower() for c in data.columns]
    return data


@router.post("/analysis/indicators")
def analyze_indicators(req: IndicatorRequest):
    """
    요청된 지표를 계산하여 반환합니다.
    indicators가 빈 배열이면 6종 전체를 계산합니다.
    """
    try:
        df = _download_ohlcv(req.symbol, req.period)

        # 요청된 지표만 또는 전체
        requested = [i.upper() for i in req.indicators] if req.indicators else list(INDICATOR_FUNCTIONS.keys())

        results = {}
        signals = []

        for name in requested:
            func = INDICATOR_FUNCTIONS.get(name)
            if func is None:
                continue
            sig = func(df)
            signals.append(sig)
            results[name] = {
                "name": sig.name,
                "value": sig.values,
                "signal": sig.signal,
                "confidence": round(sig.confidence, 4),
                "weight": round(1.0 / max(len(requested), 1), 4),
                "description": sig.description,
            }

        # 전체 지표가 2개 이상이면 충돌 분석
        conflict = None
        if len(signals) >= 2:
            report = analyze_conflicts(signals)
            conflict = report.to_dict()

        # 종합 스코어 산출
        score_result = score_local(req.symbol.upper(), signals)

        return {
            "status": "success",
            "data": {
                "symbol": req.symbol.upper(),
                "market": req.market,
                "name": req.symbol.upper(),
                "indicators": results,
                "compositeScore": round(score_result.total_score, 1),
                "compositeSignal": score_result.final_signal.lower(),
                "compositeLabel": _signal_label(score_result.final_signal),
                "categories": [
                    {"category": c.category, "score": round(c.score, 1), "details": c.details}
                    for c in score_result.categories
                ],
                "conflict": conflict,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _signal_label(signal: str) -> str:
    labels = {
        "STRONG_BUY": "적극 매수",
        "BUY": "매수",
        "HOLD": "관망",
        "SELL": "매도",
        "STRONG_SELL": "적극 매도",
    }
    return labels.get(signal, signal)


@router.post("/analysis/insights")
def generate_insights(
    req: InsightRequest,
    x_llm_key: str = Header(None),
):
    """LLM 기반 투자 인사이트 생성"""
    if not x_llm_key:
        raise HTTPException(status_code=401, detail="X-LLM-Key header is required")

    client = OpenAI(api_key=x_llm_key)

    prompt = f"""너는 투자 분석 AI다.
아래 데이터는 투자 대시보드 백엔드에서 전달된 분석 결과다.

반드시 아래 JSON 형식으로만 응답해라.
설명 문장, 마크다운, 코드블록은 절대 쓰지 마라.

입력 데이터:
symbol: {req.symbol}
market: {req.market}
topic: {req.topic}
compositeScore: {req.compositeScore}
indicators: {json.dumps(req.indicators, ensure_ascii=False)}

응답 JSON 형식:
{{
  "insights": [
    "첫 번째 투자 요약 문장",
    "두 번째 투자 요약 문장",
    "세 번째 투자 요약 문장"
  ],
  "conflict": {{
    "detected": true 또는 false,
    "buyIndicators": ["매수 신호 지표명"],
    "sellIndicators": ["매도 신호 지표명"],
    "accuracy": 0부터 100 사이 숫자,
    "corrected": "최종 판단",
    "reasoning": "충돌 판단 이유"
  }}
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 투자 대시보드용 LLM 분석 엔진이다. 반드시 JSON만 출력한다."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=512,
        )

        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)

        return {
            "status": "success",
            "data": result_json,
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM response was not valid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))