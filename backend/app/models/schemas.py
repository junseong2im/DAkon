"""
Pydantic 스키마 정의 - API 요청/응답 모델
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─── 차트 타입 열거형 ───
class ChartType(str, Enum):
    CANDLESTICK = "candlestick"
    LINE = "line"
    BAR = "bar"
    AREA = "area"


# ─── 자연어 질의 ───
class QueryRequest(BaseModel):
    """자연어 질의 요청"""
    prompt: str = Field(..., description="사용자 자연어 질의", example="애플 주가 3개월치 캔들차트로 띄워줘")
    api_key: str = Field(..., description="OpenAI 호환 API Key", example="sk-...")


class QueryResponse(BaseModel):
    """자연어 질의 파싱 결과"""
    target_ticker: str = Field(..., description="분석 대상 종목 코드", example="AAPL")
    chart_type: ChartType = Field(..., description="차트 유형", example="candlestick")
    period: str = Field(..., description="조회 기간", example="3mo")
    required_indicators: list[str] = Field(default_factory=list, description="필요 보조지표 목록")
    asset_type: str = Field(default="stock", description="자산 유형 (stock/crypto)")


# ─── 시장 데이터 ───
class OHLCVData(BaseModel):
    """정규화된 OHLCV 데이터"""
    timestamp: int = Field(..., description="Unix 타임스탬프")
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataResponse(BaseModel):
    """히스토리컬 시장 데이터 응답"""
    ticker: str
    period: str
    asset_type: str
    data: list[OHLCVData]


class RealtimePrice(BaseModel):
    """실시간 가격 데이터 (WebSocket 스트리밍)"""
    timestamp: int
    ticker: str
    current_price: float
    change_percent: float
    volume: Optional[float] = None


# ─── 기술적 지표 ───
class IndicatorResult(BaseModel):
    """기술적 지표 계산 결과"""
    name: str
    values: list[dict]
    signal: str = Field(..., description="BUY / SELL / HOLD")
    confidence: float = Field(..., ge=0, le=1)


class IndicatorsResponse(BaseModel):
    """지표 전체 응답"""
    ticker: str
    indicators: list[IndicatorResult]


# ─── AGI 스코어링 ───
class CategoryScore(BaseModel):
    """카테고리별 점수"""
    category: str
    score: float = Field(..., ge=0, le=25)
    details: str


class ScoringResponse(BaseModel):
    """AGI 스코어링 결과"""
    ticker: str
    total_score: float = Field(..., ge=0, le=100)
    categories: list[CategoryScore]
    final_signal: str = Field(..., description="STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL")
    conflict_report: Optional[str] = None


# ─── 분석 요청 ───
class AnalysisRequest(BaseModel):
    """종합 분석 요청"""
    ticker: str
    period: str = "3mo"
    api_key: str
    asset_type: str = "stock"


# ─── 에러 ───
class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
