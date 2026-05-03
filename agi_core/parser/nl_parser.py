"""
자연어 인터페이스 파서 (Natural Language Parser)
───────────────────────────────────────────────
사용자의 자연어 입력을 OpenAI 호환 API를 통해 파싱하여
구조화된 JSON(Ticker, Period, ChartType 등)으로 변환합니다.

■ Strict JSON Mode 를 사용하여 출력 형식을 강제합니다.
■ BYOK 방식으로 사용자가 전달한 api_key 를 그대로 사용합니다.
■ 폴백 파서는 200+ 종목 매핑 + 정규식 동적 추출을 지원합니다.
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


# ─── 종목 매핑 테이블 (확장판) ───────────────────────────────────────────────────
# 긴 키워드 우선 매칭을 위해 삽입 순서 유지 (dict는 Python 3.7+ 순서 보장)
_TICKER_MAP = {
    # ── 한국 KOSPI 대형주 ──
    "삼성전자우": "005935.KS", "삼성전자": "005930.KS", "삼성": "005930.KS",
    "sk하이닉스": "000660.KS", "하이닉스": "000660.KS",
    "lg에너지솔루션": "373220.KS", "lg에너지": "373220.KS",
    "삼성바이오로직스": "207940.KS", "삼성바이오": "207940.KS",
    "현대자동차": "005380.KS", "현대차": "005380.KS", "현대": "005380.KS",
    "기아": "000270.KS", "기아차": "000270.KS",
    "셀트리온": "068270.KS",
    "kb금융": "105560.KS",
    "신한지주": "055550.KS", "신한금융": "055550.KS",
    "포스코홀딩스": "005490.KS", "포스코": "005490.KS",
    "삼성sdi": "006400.KS",
    "lg화학": "051910.KS",
    "현대모비스": "012330.KS", "모비스": "012330.KS",
    "삼성물산": "028260.KS",
    "삼성생명": "032830.KS",
    "하나금융지주": "086790.KS", "하나금융": "086790.KS",
    "lg전자": "066570.KS",
    "삼성화재": "000810.KS",
    "메리츠금융지주": "138040.KS", "메리츠금융": "138040.KS",
    "한국전력": "015760.KS", "한전": "015760.KS",
    "sk이노베이션": "096770.KS", "sk이노": "096770.KS",
    "sk텔레콤": "017670.KS", "skt": "017670.KS",
    "kt": "030200.KS",
    "lg": "003550.KS",
    "sk": "034730.KS",
    "두산에너빌리티": "034020.KS", "두산에너": "034020.KS",
    "한화에어로스페이스": "012450.KS", "한화에어로": "012450.KS",
    "한화오션": "042660.KS",
    "hd현대중공업": "329180.KS", "현대중공업": "329180.KS",
    "hd한국조선해양": "009540.KS", "한국조선해양": "009540.KS",
    "크래프톤": "259960.KS",
    "한미반도체": "042700.KS", "한미반": "042700.KS",
    "에코프로비엠": "247540.KS", "에코프로bm": "247540.KS",
    "에코프로": "086520.KS",
    "포스코퓨처엠": "003670.KS",
    "카카오뱅크": "323410.KS", "카뱅": "323410.KS",
    "우리금융지주": "316140.KS", "우리금융": "316140.KS",
    "sk스퀘어": "402340.KS",
    "현대건설": "000720.KS",
    "고려아연": "010130.KS",
    "삼성에스디에스": "018260.KS", "삼성sds": "018260.KS",
    "한화솔루션": "009830.KS",
    "lg이노텍": "011070.KS",
    "lg디스플레이": "034220.KS", "lgd": "034220.KS",
    "cj제일제당": "097950.KS",
    "아모레퍼시픽": "090430.KS", "아모레": "090430.KS",
    "대한항공": "003490.KS",
    "한화": "000880.KS",
    "롯데케미칼": "011170.KS",
    "s-oil": "010950.KS", "에스오일": "010950.KS",

    # ── 한국 KOSDAQ 주요 종목 ──
    "카카오": "035720.KQ", "카카오게임즈": "293490.KQ",
    "네이버": "035420.KS",
    "엔씨소프트": "036570.KS", "엔씨": "036570.KS",
    "넷마블": "251270.KS",
    "펄어비스": "263750.KS",
    "위메이드": "112040.KQ",
    "컴투스": "078340.KQ",
    "셀트리온헬스케어": "091990.KQ", "셀트리온헬스": "091990.KQ",
    "에이치엘비": "028300.KQ", "hlb": "028300.KQ",
    "알테오젠": "196170.KQ",
    "리가켐바이오": "141080.KQ",
    "레인보우로보틱스": "277810.KQ",
    "클래시스": "214150.KQ",
    "엘앤에프": "066970.KQ",
    "두산로보틱스": "454910.KQ",

    # ── 미국 주요 종목 ──
    "애플": "AAPL", "apple": "AAPL",
    "테슬라": "TSLA", "tesla": "TSLA",
    "엔비디아": "NVDA", "nvidia": "NVDA",
    "마이크로소프트": "MSFT", "microsoft": "MSFT",
    "구글": "GOOGL", "google": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN", "amazon": "AMZN",
    "메타": "META", "meta": "META", "페이스북": "META",
    "넷플릭스": "NFLX", "netflix": "NFLX",
    "amd": "AMD",
    "인텔": "INTC", "intel": "INTC",
    "브로드컴": "AVGO", "broadcom": "AVGO",
    "팔란티어": "PLTR", "palantir": "PLTR",
    "코인베이스": "COIN", "coinbase": "COIN",
    "스노우플레이크": "SNOW", "snowflake": "SNOW",
    "크라우드스트라이크": "CRWD",
    "유니티": "U",
    "로블록스": "RBLX", "roblox": "RBLX",
    "스포티파이": "SPOT", "spotify": "SPOT",
    "에어비앤비": "ABNB", "airbnb": "ABNB",
    "우버": "UBER", "uber": "UBER",
    "줌비디오": "ZM", "zoom": "ZM",
    "쇼피파이": "SHOP", "shopify": "SHOP",
    "디즈니": "DIS", "disney": "DIS",
    "나이키": "NKE", "nike": "NKE",
    "코카콜라": "KO", "coca-cola": "KO",
    "맥도날드": "MCD", "mcdonald": "MCD",
    "존슨앤드존슨": "JNJ", "j&j": "JNJ",
    "jp모건": "JPM", "jpmorgan": "JPM",
    "골드만삭스": "GS", "goldman": "GS",
    "버크셔해서웨이": "BRK-B", "버크셔": "BRK-B",
    "월마트": "WMT", "walmart": "WMT",
    "비자": "V", "visa": "V",
    "마스터카드": "MA", "mastercard": "MA",

    # ── 미국 ETF ──
    "spy": "SPY", "s&p500": "SPY", "에스앤피": "SPY",
    "qqq": "QQQ", "나스닥etf": "QQQ",
    "dia": "DIA", "다우etf": "DIA",
    "iwm": "IWM",
    "arkk": "ARKK", "아크": "ARKK",
    "tqqq": "TQQQ",
    "soxl": "SOXL",

    # ── 암호화폐 ──
    "비트코인": "BTC/USDT", "btc": "BTC/USDT", "비트": "BTC/USDT",
    "이더리움": "ETH/USDT", "eth": "ETH/USDT", "이더": "ETH/USDT",
    "리플": "XRP/USDT", "xrp": "XRP/USDT",
    "솔라나": "SOL/USDT", "sol": "SOL/USDT",
    "도지코인": "DOGE/USDT", "doge": "DOGE/USDT", "도지": "DOGE/USDT",
    "에이다": "ADA/USDT", "ada": "ADA/USDT", "카르다노": "ADA/USDT",
    "폴카닷": "DOT/USDT", "dot": "DOT/USDT",
    "아발란체": "AVAX/USDT", "avax": "AVAX/USDT",
    "체인링크": "LINK/USDT", "link": "LINK/USDT",
    "매틱": "MATIC/USDT", "matic": "MATIC/USDT", "폴리곤": "MATIC/USDT",
    "시바이누": "SHIB/USDT", "shib": "SHIB/USDT",
    "스텔라루멘": "XLM/USDT", "xlm": "XLM/USDT",
    "트론": "TRX/USDT", "trx": "TRX/USDT",
    "수이": "SUI/USDT", "sui": "SUI/USDT",
}

# 기간 매핑 (정적 + 동적 정규식 보완)
_PERIOD_MAP = {
    "1일": "1d", "하루": "1d", "오늘": "1d", "당일": "1d",
    "1주": "5d", "일주일": "5d", "한주": "5d", "이번주": "5d",
    "2주": "10d", "이주일": "10d",
    "1개월": "1mo", "한달": "1mo", "1달": "1mo",
    "2개월": "2mo", "두달": "2mo",
    "3개월": "3mo", "삼개월": "3mo", "세달": "3mo",
    "6개월": "6mo", "반년": "6mo", "육개월": "6mo",
    "1년": "1y", "일년": "1y", "한해": "1y", "올해": "ytd",
    "2년": "2y", "이년": "2y",
    "3년": "3y",
    "5년": "5y", "오년": "5y",
    "10년": "10y", "십년": "10y",
    "전체": "max", "최대": "max",
}

_CHART_TYPE_MAP = {
    "캔들": "candlestick", "캔들차트": "candlestick", "봉차트": "candlestick", "봉": "candlestick",
    "라인": "line", "선": "line", "선차트": "line", "꺾은선": "line",
    "바": "bar", "막대": "bar", "바차트": "bar",
    "영역": "area", "에어리어": "area", "면적": "area",
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
    "sma": "sma",
    "ema": "ema",
    "bb": "bollinger",
}


# ─── 동적 기간 추출 (정규식) ────────────────────────────────────────────────────
def _extract_period_dynamic(text: str) -> Optional[str]:
    """정적 매핑에 없는 기간을 정규식으로 동적 추출합니다."""
    # "N일", "N주", "N개월", "N달", "N년" 패턴
    m = re.search(r'(\d+)\s*(일|주일?|주|개월|달|년)', text)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2)

    if unit == "일":
        return f"{num}d"
    elif unit in ("주", "주일"):
        return f"{num * 5}d"
    elif unit in ("개월", "달"):
        return f"{num}mo"
    elif unit == "년":
        return f"{num}y"
    return None


# ─── 동적 티커 추출 (정규식) ────────────────────────────────────────────────────
def _extract_ticker_dynamic(text: str, original_input: str) -> tuple[Optional[str], str]:
    """
    매핑 테이블에 없는 종목을 정규식으로 추출합니다.

    Returns:
        (ticker, asset_type) 또는 (None, "stock")
    """
    # 한국 종목코드 6자리 숫자 패턴 (예: 005930, 373220)
    m = re.search(r'\b(\d{6})\b', text)
    if m:
        code = m.group(1)
        return f"{code}.KS", "stock"

    # 영문 대문자 티커 패턴 (예: AAPL, TSLA, BRK-B)
    m = re.search(r'\b([A-Z]{1,5}(?:-[A-Z])?)(?:\s|$)', original_input)
    if m:
        return m.group(1), "stock"

    # 한글 종목명 추출 (조사 제거: 의/을/를/이/가/은/는/도/에/로 등)
    m = re.search(r'([가-힣A-Za-z][가-힣A-Za-z0-9\-]{1,15})(?:의|을|를|이|가|은|는|도|에|로|차트|주가|분석|시세)?', text)
    if m:
        candidate = m.group(1).strip()
        # 기간/차트 키워드가 아닌 경우만 종목명으로 간주
        non_ticker_words = {"캔들", "라인", "차트", "봉차트", "바차트", "영역", "선차트",
                           "오늘", "내일", "어제", "올해", "전체", "최대", "분석", "시세",
                           "보여", "띄워", "알려", "비교", "수익률"}
        if candidate not in non_ticker_words and len(candidate) >= 2:
            return candidate, "stock"

    return None, "stock"


# ─── 폴백: 스마트 규칙 기반 파싱 ────────────────────────────────────────────────
def parse_query_fallback(user_input: str) -> ParsedQuery:
    """
    LLM 없이 규칙 기반으로 자연어를 파싱합니다.
    LLM 호출 실패 시 폴백으로 사용됩니다.

    200+ 종목 매핑 + 동적 정규식 추출로 대부분의 질의를 처리합니다.
    매핑에 없는 종목은 사용자 입력에서 종목명을 추출하여 그대로 반환합니다.

    Args:
        user_input: 사용자 자연어 질의

    Returns:
        ParsedQuery: 파싱된 질의 결과 (최선의 추론)
    """
    text = user_input.strip().lower()

    # ── 1) 티커 추출: 매핑 테이블 우선 ──
    ticker = None
    asset_type = "stock"

    # 긴 키워드 우선 매칭 (예: "삼성전자우"가 "삼성"보다 먼저)
    for keyword, symbol in _TICKER_MAP.items():
        if keyword in text:
            ticker = symbol
            if "/" in symbol:
                asset_type = "crypto"
            break

    # ── 2) 매핑 실패 → 동적 추출 ──
    if ticker is None:
        ticker, asset_type = _extract_ticker_dynamic(text, user_input)

    # ── 3) 최종 폴백: 입력 원문에서 첫 단어 사용 (AAPL 대신) ──
    if ticker is None:
        # 첫 번째 의미있는 단어를 추출
        words = re.findall(r'[가-힣A-Za-z0-9\-]+', user_input)
        ticker = words[0] if words else user_input.strip()

    # ── 기간 추출: 정적 매핑 → 동적 정규식 ──
    period = None
    for keyword, p in _PERIOD_MAP.items():
        if keyword in text:
            period = p
            break
    if period is None:
        period = _extract_period_dynamic(text) or "3mo"

    # ── 차트 타입 추출 ──
    chart_type = "candlestick"
    for keyword, ct in _CHART_TYPE_MAP.items():
        if keyword in text:
            chart_type = ct
            break

    # ── 지표 추출 (중복 방지) ──
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
