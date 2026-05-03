"""
자연어 인터페이스 파서 (Natural Language Parser)
───────────────────────────────────────────────
사용자의 자연어 입력을 OpenAI 호환 API를 통해 파싱하여
구조화된 JSON(Ticker, Period, ChartType 등)으로 변환합니다.

■ Strict JSON Mode 를 사용하여 출력 형식을 강제합니다.
■ BYOK 방식으로 사용자가 전달한 api_key 를 그대로 사용합니다.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from agi_core.prompts.system_prompts import NL_QUERY_PARSER_PROMPT

logger = logging.getLogger(__name__)

# ─── 기본 설정 ──────────────────────────────────────────────────────────────────
DEFAULT_MODEL = "gpt-4o"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
REQUEST_TIMEOUT = 30.0


# ─── 파싱 결과 데이터 클래스 ────────────────────────────────────────────────────
@dataclass
class ParsedQuery:
    """자연어 질의 파싱 결과"""
    target_ticker: str
    chart_type: str
    period: str
    required_indicators: list[str]
    asset_type: str  # "stock" | "crypto"

    def to_dict(self) -> dict:
        return {
            "target_ticker": self.target_ticker,
            "chart_type": self.chart_type,
            "period": self.period,
            "required_indicators": self.required_indicators,
            "asset_type": self.asset_type,
        }


# ─── 유효성 검증 ────────────────────────────────────────────────────────────────
VALID_CHART_TYPES = {"candlestick", "line", "bar", "area"}
VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
VALID_INDICATORS = {"volume", "sma", "ema", "rsi", "macd", "bollinger", "stochastic"}
VALID_ASSET_TYPES = {"stock", "crypto"}


def _validate_parsed_result(data: dict) -> ParsedQuery:
    """파싱 결과의 유효성을 검증하고 ParsedQuery 객체로 변환합니다."""

    # 필수 필드 확인
    required_fields = ["target_ticker", "chart_type", "period"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"필수 필드 누락: {field}")

    # ticker 정리 (공백 제거, 대문자 변환 — 암호화폐 페어는 그대로)
    ticker = data["target_ticker"].strip()
    if "/" not in ticker:
        ticker = ticker.upper()

    # chart_type 검증
    chart_type = data.get("chart_type", "candlestick").lower()
    if chart_type not in VALID_CHART_TYPES:
        logger.warning(f"알 수 없는 차트 타입 '{chart_type}', 기본값 'candlestick' 사용")
        chart_type = "candlestick"

    # period 검증
    period = data.get("period", "3mo").lower()
    if period not in VALID_PERIODS:
        logger.warning(f"알 수 없는 기간 '{period}', 기본값 '3mo' 사용")
        period = "3mo"

    # indicators 검증 및 필터링
    raw_indicators = data.get("required_indicators", ["volume"])
    if not isinstance(raw_indicators, list):
        raw_indicators = ["volume"]
    indicators = [ind.lower() for ind in raw_indicators if ind.lower() in VALID_INDICATORS]
    if not indicators:
        indicators = ["volume"]

    # asset_type 검증
    asset_type = data.get("asset_type", "stock").lower()
    if asset_type not in VALID_ASSET_TYPES:
        # 암호화폐 페어 패턴 자동 감지
        asset_type = "crypto" if "/" in ticker else "stock"

    return ParsedQuery(
        target_ticker=ticker,
        chart_type=chart_type,
        period=period,
        required_indicators=indicators,
        asset_type=asset_type,
    )


# ─── LLM 호출을 통한 자연어 파싱 ───────────────────────────────────────────────
async def parse_query(
    user_input: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
) -> ParsedQuery:
    """
    사용자의 자연어 입력을 LLM을 통해 파싱합니다.

    Args:
        user_input: 사용자 자연어 질의 (예: "애플 주가 3개월치 캔들차트로 띄워줘")
        api_key:    OpenAI 호환 API Key
        model:      사용할 모델명 (기본: gpt-4o)
        base_url:   API 베이스 URL (기본: https://api.openai.com/v1)

    Returns:
        ParsedQuery: 파싱된 질의 결과

    Raises:
        ValueError:  파싱 결과 유효성 검증 실패
        httpx.HTTPStatusError: API 호출 실패
    """
    if not user_input or not user_input.strip():
        raise ValueError("빈 질의는 처리할 수 없습니다.")

    if not api_key or not api_key.strip():
        raise ValueError("API Key가 필요합니다.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": NL_QUERY_PARSER_PROMPT},
            {"role": "user", "content": user_input.strip()},
        ],
        "response_format": {"type": "json_object"},  # Strict JSON Mode
        "temperature": 0.1,  # 결정론적 출력을 위해 낮게 설정
        "max_tokens": 256,
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

    result = response.json()

    # 응답에서 JSON 추출
    try:
        content = result["choices"][0]["message"]["content"]
        parsed_data = json.loads(content)
    except (KeyError, IndexError) as e:
        raise ValueError(f"LLM 응답 구조가 예상과 다릅니다: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답이 유효한 JSON이 아닙니다: {e}")

    logger.info(f"파싱 결과: {parsed_data}")

    # 유효성 검증 후 반환
    return _validate_parsed_result(parsed_data)


# ─── 폴백: 로컬 규칙 기반 파싱 ──────────────────────────────────────────────────
# LLM 호출 실패 시 간단한 규칙 기반 파서로 대체
_TICKER_MAP = {
    "애플": "AAPL", "apple": "AAPL",
    "테슬라": "TSLA", "tesla": "TSLA",
    "구글": "GOOGL", "google": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN", "amazon": "AMZN",
    "마이크로소프트": "MSFT", "microsoft": "MSFT", "ms": "MSFT",
    "엔비디아": "NVDA", "nvidia": "NVDA",
    "메타": "META", "meta": "META", "페이스북": "META",
    "넷플릭스": "NFLX", "netflix": "NFLX",
    "삼성전자": "005930.KS", "삼성": "005930.KS",
    "sk하이닉스": "000660.KS", "하이닉스": "000660.KS",
    "카카오": "035720.KS",
    "네이버": "035420.KS",
    "비트코인": "BTC/USDT", "btc": "BTC/USDT",
    "이더리움": "ETH/USDT", "eth": "ETH/USDT",
    "리플": "XRP/USDT", "xrp": "XRP/USDT",
    "솔라나": "SOL/USDT", "sol": "SOL/USDT",
    "도지코인": "DOGE/USDT", "doge": "DOGE/USDT",
}

_PERIOD_MAP = {
    "1일": "1d", "하루": "1d", "오늘": "1d",
    "1주": "5d", "일주일": "5d", "한주": "5d",
    "1개월": "1mo", "한달": "1mo",
    "3개월": "3mo", "삼개월": "3mo", "세달": "3mo",
    "6개월": "6mo", "반년": "6mo",
    "1년": "1y", "일년": "1y", "한해": "1y",
    "2년": "2y", "이년": "2y",
    "5년": "5y", "오년": "5y",
}

_CHART_TYPE_MAP = {
    "캔들": "candlestick", "캔들차트": "candlestick", "봉차트": "candlestick",
    "라인": "line", "선": "line", "선차트": "line",
    "바": "bar", "막대": "bar",
    "영역": "area", "에어리어": "area",
}

# 긴 키워드 우선으로 정렬하여 부분 매칭 중복 방지
_INDICATOR_MAP = {
    "단순이동평균": "sma",
    "지수이동평균": "ema",
    "볼린저밴드": "bollinger",
    "이동평균": "sma",
    "이평선": "sma",
    "스토캐스틱": "stochastic",
    "상대강도": "rsi",
    "거래량": "volume",
    "볼린저": "bollinger",
    "rsi": "rsi",
    "macd": "macd",
}


def parse_query_fallback(user_input: str) -> ParsedQuery:
    """
    LLM 없이 규칙 기반으로 자연어를 파싱합니다.
    LLM 호출 실패 시 폴백으로 사용됩니다.

    Args:
        user_input: 사용자 자연어 질의

    Returns:
        ParsedQuery: 파싱된 질의 결과 (최선의 추론)
    """
    text = user_input.strip().lower()

    # 티커 추출
    ticker = None
    asset_type = "stock"
    for keyword, symbol in _TICKER_MAP.items():
        if keyword in text:
            ticker = symbol
            if "/" in symbol:
                asset_type = "crypto"
            break

    if ticker is None:
        # 영문 대문자 패턴 시도 (예: "AAPL", "TSLA")
        match = re.search(r'\b([A-Z]{1,5})\b', user_input)
        if match:
            ticker = match.group(1)
        else:
            ticker = "AAPL"  # 최종 기본값

    # 기간 추출
    period = "3mo"  # 기본값
    for keyword, p in _PERIOD_MAP.items():
        if keyword in text:
            period = p
            break

    # 차트 타입 추출
    chart_type = "candlestick"  # 기본값
    for keyword, ct in _CHART_TYPE_MAP.items():
        if keyword in text:
            chart_type = ct
            break

    # 지표 추출 (중복 방지: set 사용 + 매칭된 키워드 부분 제거로 부분 매칭 중복 차단)
    indicators_set: set[str] = set()
    remaining_text = text
    for keyword, ind in _INDICATOR_MAP.items():
        if keyword in remaining_text:
            indicators_set.add(ind)
            remaining_text = remaining_text.replace(keyword, "", 1)
    indicators = list(indicators_set) if indicators_set else ["volume"]

    return ParsedQuery(
        target_ticker=ticker,
        chart_type=chart_type,
        period=period,
        required_indicators=indicators,
        asset_type=asset_type,
    )


# ─── 통합 파싱 함수 (LLM 우선 → 폴백) ─────────────────────────────────────────
async def parse_query_safe(
    user_input: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
) -> ParsedQuery:
    """
    자연어 파싱을 시도합니다. LLM 호출이 실패하면 규칙 기반 폴백을 사용합니다.

    Args:
        user_input: 사용자 자연어 질의
        api_key:    OpenAI 호환 API Key (없으면 폴백 사용)
        model:      사용할 모델명
        base_url:   API 베이스 URL

    Returns:
        ParsedQuery: 파싱된 질의 결과
    """
    # API Key가 있으면 LLM 파싱 시도
    if api_key and api_key.strip():
        try:
            return await parse_query(user_input, api_key, model, base_url)
        except Exception as e:
            logger.warning(f"LLM 파싱 실패, 폴백 사용: {e}")

    # 폴백
    return parse_query_fallback(user_input)
