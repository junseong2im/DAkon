"""
4-카테고리 스코어링 알고리즘
────────────────────────────
4개 카테고리에 각 25점씩 할당하여 합산 후 0~100점의 TotalScore를 반환합니다.

카테고리:
  1. 기술적 (Technical)     — 차트/지표 기반 분석        [0~25점]
  2. 재무   (Financial)     — 기업 재무제표 분석          [0~25점]
  3. 수급   (Supply/Demand) — 매수/매도 세력 분석         [0~25점]
  4. 거시   (Macro)         — 거시경제 환경 분석          [0~25점]

■ 기술적 카테고리는 indicators.py + conflict_watchdog.py 결과를 입력으로 사용합니다.
■ 재무/수급/거시 카테고리는 LLM 분석 또는 외부 데이터가 없을 경우 기본값을 사용합니다.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from agi_core.engine.indicators import (
    IndicatorSignal,
    SIGNAL_BUY,
    SIGNAL_SELL,
    SIGNAL_HOLD,
)
from agi_core.engine.conflict_watchdog import analyze_conflicts, ConflictReport
from agi_core.prompts.system_prompts import ANALYSIS_REPORT_PROMPT

logger = logging.getLogger(__name__)

# ─── 설정 ───────────────────────────────────────────────────────────────────────
MAX_CATEGORY_SCORE = 25.0
DEFAULT_MODEL = "gpt-4o"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


# ─── 스코어 데이터 클래스 ──────────────────────────────────────────────────────
@dataclass
class CategoryScore:
    """개별 카테고리 점수"""
    category: str
    score: float          # 0.0 ~ 25.0
    details: str
    sub_scores: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "score": round(self.score, 2),
            "details": self.details,
            "sub_scores": self.sub_scores,
        }


@dataclass
class ScoringResult:
    """최종 스코어링 결과"""
    ticker: str
    total_score: float
    categories: list[CategoryScore]
    final_signal: str
    conflict_report: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "total_score": round(self.total_score, 2),
            "categories": [c.to_dict() for c in self.categories],
            "final_signal": self.final_signal,
            "conflict_report": self.conflict_report,
        }


# ─── 최종 신호 결정 ─────────────────────────────────────────────────────────────
def _determine_signal(total_score: float) -> str:
    """
    총점 기준 최종 투자 신호를 결정합니다.

    - 80~100: STRONG_BUY
    - 60~79:  BUY
    - 40~59:  HOLD
    - 20~39:  SELL
    - 0~19:   STRONG_SELL
    """
    if total_score >= 80:
        return "STRONG_BUY"
    elif total_score >= 60:
        return "BUY"
    elif total_score >= 40:
        return "HOLD"
    elif total_score >= 20:
        return "SELL"
    else:
        return "STRONG_SELL"


# ─── 1. 기술적 카테고리 스코어링 (0~25) ────────────────────────────────────────
def score_technical(
    indicator_signals: list[IndicatorSignal],
    conflict_report: Optional[ConflictReport] = None,
) -> CategoryScore:
    """
    기술적 지표 분석 결과를 기반으로 점수를 산출합니다.

    점수 산출 기준:
    - 각 지표의 (신호 점수 × 신뢰도)를 평균하여 0~25점으로 환산
    - BUY = 1.0, HOLD = 0.5, SELL = 0.0
    - 충돌 감지 시 신뢰도 페널티 적용 (-2점)
    """
    if not indicator_signals:
        return CategoryScore(
            category="technical",
            score=12.5,  # 중립 기본값
            details="기술적 지표 데이터 없음 — 기본값 적용",
        )

    signal_scores = {SIGNAL_BUY: 1.0, SIGNAL_HOLD: 0.5, SIGNAL_SELL: 0.0}

    weighted_sum = 0.0
    total_confidence = 0.0
    sub_scores = {}

    for sig in indicator_signals:
        base = signal_scores.get(sig.signal, 0.5)
        weighted = base * sig.confidence
        weighted_sum += weighted
        total_confidence += sig.confidence
        sub_scores[sig.name] = {
            "signal": sig.signal,
            "confidence": round(sig.confidence, 2),
            "contribution": round(weighted, 4),
        }

    # 평균 → 0~25 범위로 스케일링
    avg = weighted_sum / len(indicator_signals) if indicator_signals else 0.5
    raw_score = avg * MAX_CATEGORY_SCORE

    # 충돌 페널티
    penalty = 0.0
    if conflict_report and conflict_report.conflicts_detected:
        penalty = 2.0
        raw_score = max(0, raw_score - penalty)

    score = min(MAX_CATEGORY_SCORE, max(0, raw_score))

    # 설명 생성
    buy_count = sum(1 for s in indicator_signals if s.signal == SIGNAL_BUY)
    sell_count = sum(1 for s in indicator_signals if s.signal == SIGNAL_SELL)
    hold_count = sum(1 for s in indicator_signals if s.signal == SIGNAL_HOLD)

    detail_parts = [
        f"{len(indicator_signals)}개 지표 분석: 매수 {buy_count}, 매도 {sell_count}, 관망 {hold_count}."
    ]
    if penalty > 0:
        detail_parts.append(f"신호 충돌로 {penalty}점 감점 적용.")

    return CategoryScore(
        category="technical",
        score=round(score, 2),
        details=" ".join(detail_parts),
        sub_scores=sub_scores,
    )


# ─── 2. 재무 카테고리 스코어링 (0~25) ──────────────────────────────────────────
def score_financial(
    financial_data: Optional[dict] = None,
) -> CategoryScore:
    """
    기업 재무 데이터를 기반으로 점수를 산출합니다.

    Args:
        financial_data: 재무 데이터 딕셔너리 (선택적)
            - per:           PER (주가수익비율)
            - pbr:           PBR (주가순자산비율)
            - roe:           ROE (자기자본이익률, %)
            - debt_ratio:    부채비율 (%)
            - revenue_growth: 매출 성장률 (%)

    외부 데이터 없으면 기본값(12.5점) 반환.
    """
    if not financial_data:
        return CategoryScore(
            category="financial",
            score=12.5,
            details="재무 데이터 미제공 — 기본값 적용 (외부 데이터 연동 필요)",
        )

    score = 12.5  # 기본 시작점
    details = []
    sub = {}

    # PER 평가 (낮을수록 양호)
    per = financial_data.get("per")
    if per is not None:
        sub["per"] = per
        if per < 10:
            score += 3.0
            details.append(f"PER {per:.1f}: 저평가")
        elif per < 20:
            score += 1.5
            details.append(f"PER {per:.1f}: 적정")
        elif per < 40:
            score -= 1.0
            details.append(f"PER {per:.1f}: 다소 높음")
        else:
            score -= 2.5
            details.append(f"PER {per:.1f}: 고평가")

    # ROE 평가 (높을수록 양호)
    roe = financial_data.get("roe")
    if roe is not None:
        sub["roe"] = roe
        if roe > 20:
            score += 3.0
            details.append(f"ROE {roe:.1f}%: 우수")
        elif roe > 10:
            score += 1.5
            details.append(f"ROE {roe:.1f}%: 양호")
        elif roe > 0:
            details.append(f"ROE {roe:.1f}%: 보통")
        else:
            score -= 2.0
            details.append(f"ROE {roe:.1f}%: 부진")

    # 부채비율 평가 (낮을수록 양호)
    debt_ratio = financial_data.get("debt_ratio")
    if debt_ratio is not None:
        sub["debt_ratio"] = debt_ratio
        if debt_ratio < 50:
            score += 2.0
            details.append(f"부채비율 {debt_ratio:.0f}%: 안정적")
        elif debt_ratio < 100:
            score += 0.5
            details.append(f"부채비율 {debt_ratio:.0f}%: 보통")
        else:
            score -= 2.0
            details.append(f"부채비율 {debt_ratio:.0f}%: 높음")

    # 매출 성장률 평가
    revenue_growth = financial_data.get("revenue_growth")
    if revenue_growth is not None:
        sub["revenue_growth"] = revenue_growth
        if revenue_growth > 20:
            score += 2.5
            details.append(f"매출 성장 +{revenue_growth:.1f}%: 고성장")
        elif revenue_growth > 5:
            score += 1.0
            details.append(f"매출 성장 +{revenue_growth:.1f}%: 양호")
        elif revenue_growth > 0:
            details.append(f"매출 성장 +{revenue_growth:.1f}%: 정체")
        else:
            score -= 2.0
            details.append(f"매출 성장 {revenue_growth:.1f}%: 역성장")

    score = min(MAX_CATEGORY_SCORE, max(0, score))
    return CategoryScore(
        category="financial",
        score=round(score, 2),
        details="; ".join(details) if details else "재무 데이터 분석 완료",
        sub_scores=sub,
    )


# ─── 3. 수급 카테고리 스코어링 (0~25) ──────────────────────────────────────────
def score_supply_demand(
    supply_demand_data: Optional[dict] = None,
) -> CategoryScore:
    """
    매수/매도 세력 데이터를 기반으로 점수를 산출합니다.

    Args:
        supply_demand_data: 수급 데이터 딕셔너리 (선택적)
            - foreign_net:       외국인 순매수/매도 (양수=순매수)
            - institutional_net: 기관 순매수/매도
            - individual_net:    개인 순매수/매도
            - short_ratio:       공매도 비율 (%)
            - volume_trend:      거래량 추세 ("increasing"/"decreasing"/"stable")

    외부 데이터 없으면 기본값(12.5점) 반환.
    """
    if not supply_demand_data:
        return CategoryScore(
            category="supply_demand",
            score=12.5,
            details="수급 데이터 미제공 — 기본값 적용 (외부 데이터 연동 필요)",
        )

    score = 12.5
    details = []
    sub = {}

    # 외국인 수급
    foreign_net = supply_demand_data.get("foreign_net")
    if foreign_net is not None:
        sub["foreign_net"] = foreign_net
        if foreign_net > 0:
            score += min(3.0, foreign_net / 1e9)  # 10억원당 1점, 최대 3점
            details.append(f"외국인 순매수 {foreign_net/1e8:.0f}억원")
        else:
            score -= min(3.0, abs(foreign_net) / 1e9)
            details.append(f"외국인 순매도 {abs(foreign_net)/1e8:.0f}억원")

    # 기관 수급
    institutional_net = supply_demand_data.get("institutional_net")
    if institutional_net is not None:
        sub["institutional_net"] = institutional_net
        if institutional_net > 0:
            score += min(2.5, institutional_net / 1e9)
            details.append(f"기관 순매수 {institutional_net/1e8:.0f}억원")
        else:
            score -= min(2.5, abs(institutional_net) / 1e9)
            details.append(f"기관 순매도 {abs(institutional_net)/1e8:.0f}억원")

    # 공매도 비율
    short_ratio = supply_demand_data.get("short_ratio")
    if short_ratio is not None:
        sub["short_ratio"] = short_ratio
        if short_ratio > 10:
            score -= 2.0
            details.append(f"공매도 비율 {short_ratio:.1f}%: 높음")
        elif short_ratio > 5:
            score -= 0.5
            details.append(f"공매도 비율 {short_ratio:.1f}%: 보통")
        else:
            score += 1.0
            details.append(f"공매도 비율 {short_ratio:.1f}%: 낮음")

    # 거래량 추세
    volume_trend = supply_demand_data.get("volume_trend")
    if volume_trend:
        sub["volume_trend"] = volume_trend
        if volume_trend == "increasing":
            score += 1.5
            details.append("거래량 증가 추세")
        elif volume_trend == "decreasing":
            score -= 1.0
            details.append("거래량 감소 추세")
        else:
            details.append("거래량 보합")

    score = min(MAX_CATEGORY_SCORE, max(0, score))
    return CategoryScore(
        category="supply_demand",
        score=round(score, 2),
        details="; ".join(details) if details else "수급 데이터 분석 완료",
        sub_scores=sub,
    )


# ─── 4. 거시경제 카테고리 스코어링 (0~25) ──────────────────────────────────────
def score_macro(
    macro_data: Optional[dict] = None,
) -> CategoryScore:
    """
    거시경제 환경 데이터를 기반으로 점수를 산출합니다.

    Args:
        macro_data: 거시경제 데이터 딕셔너리 (선택적)
            - interest_rate_trend: 금리 추세 ("rising"/"falling"/"stable")
            - inflation:          인플레이션율 (%)
            - gdp_growth:         GDP 성장률 (%)
            - vix:                VIX 지수
            - dollar_index_trend: 달러 인덱스 추세

    외부 데이터 없으면 기본값(12.5점) 반환.
    """
    if not macro_data:
        return CategoryScore(
            category="macro",
            score=12.5,
            details="거시경제 데이터 미제공 — 기본값 적용 (외부 데이터 연동 필요)",
        )

    score = 12.5
    details = []
    sub = {}

    # 금리 추세
    ir_trend = macro_data.get("interest_rate_trend")
    if ir_trend:
        sub["interest_rate_trend"] = ir_trend
        if ir_trend == "falling":
            score += 3.0
            details.append("금리 인하 추세: 유동성 확대 기대")
        elif ir_trend == "rising":
            score -= 2.5
            details.append("금리 인상 추세: 긴축 환경")
        else:
            details.append("금리 동결 기조")

    # 인플레이션
    inflation = macro_data.get("inflation")
    if inflation is not None:
        sub["inflation"] = inflation
        if inflation < 2:
            score += 2.0
            details.append(f"인플레이션 {inflation:.1f}%: 안정적")
        elif inflation < 4:
            score += 0.5
            details.append(f"인플레이션 {inflation:.1f}%: 보통")
        else:
            score -= 2.0
            details.append(f"인플레이션 {inflation:.1f}%: 높음")

    # GDP 성장률
    gdp = macro_data.get("gdp_growth")
    if gdp is not None:
        sub["gdp_growth"] = gdp
        if gdp > 3:
            score += 2.5
            details.append(f"GDP 성장 +{gdp:.1f}%: 호황")
        elif gdp > 1:
            score += 1.0
            details.append(f"GDP 성장 +{gdp:.1f}%: 완만")
        elif gdp > 0:
            details.append(f"GDP 성장 +{gdp:.1f}%: 저성장")
        else:
            score -= 3.0
            details.append(f"GDP 성장 {gdp:.1f}%: 경기 침체 우려")

    # VIX (공포 지수)
    vix = macro_data.get("vix")
    if vix is not None:
        sub["vix"] = vix
        if vix < 15:
            score += 2.0
            details.append(f"VIX {vix:.1f}: 시장 안정")
        elif vix < 25:
            score += 0.5
            details.append(f"VIX {vix:.1f}: 보통")
        elif vix < 35:
            score -= 1.5
            details.append(f"VIX {vix:.1f}: 불안")
        else:
            score -= 3.0
            details.append(f"VIX {vix:.1f}: 공포 극심")

    score = min(MAX_CATEGORY_SCORE, max(0, score))
    return CategoryScore(
        category="macro",
        score=round(score, 2),
        details="; ".join(details) if details else "거시경제 데이터 분석 완료",
        sub_scores=sub,
    )


# ─── LLM 기반 종합 스코어링 (선택적) ──────────────────────────────────────────
async def score_with_llm(
    ticker: str,
    indicator_signals: list[IndicatorSignal],
    conflict_report: ConflictReport,
    api_key: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
) -> Optional[ScoringResult]:
    """
    LLM을 활용하여 모든 카테고리를 종합적으로 스코어링합니다.
    기술적 지표 데이터를 컨텍스트로 전달하여 LLM이 4개 카테고리를 평가합니다.

    Args:
        ticker:            종목 코드
        indicator_signals: 기술적 지표 결과 리스트
        conflict_report:   충돌 분석 결과
        api_key:           OpenAI 호환 API Key
        model:             사용할 모델명
        base_url:          API 베이스 URL

    Returns:
        ScoringResult 또는 None (LLM 호출 실패 시)
    """
    # 지표 데이터를 컨텍스트로 구성
    indicator_context = []
    for sig in indicator_signals:
        indicator_context.append({
            "indicator": sig.name,
            "signal": sig.signal,
            "confidence": sig.confidence,
            "description": sig.description,
            "values": sig.values,
        })

    user_message = json.dumps({
        "ticker": ticker,
        "indicators": indicator_context,
        "conflict_analysis": conflict_report.to_dict(),
    }, ensure_ascii=False, indent=2)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": ANALYSIS_REPORT_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        data = json.loads(content)

        # LLM 결과를 ScoringResult로 변환
        categories = []
        for cat_data in data.get("categories", []):
            categories.append(CategoryScore(
                category=cat_data["category"],
                score=min(MAX_CATEGORY_SCORE, max(0, float(cat_data["score"]))),
                details=cat_data.get("details", ""),
            ))

        total = sum(c.score for c in categories)
        return ScoringResult(
            ticker=data.get("ticker", ticker),
            total_score=round(total, 2),
            categories=categories,
            final_signal=_determine_signal(total),
            conflict_report=data.get("conflict_report"),
        )

    except Exception as e:
        logger.error(f"LLM 스코어링 실패: {e}")
        return None


# ─── 로컬 스코어링 (LLM 불필요) ────────────────────────────────────────────────
def score_local(
    ticker: str,
    indicator_signals: list[IndicatorSignal],
    conflict_report: Optional[ConflictReport] = None,
    financial_data: Optional[dict] = None,
    supply_demand_data: Optional[dict] = None,
    macro_data: Optional[dict] = None,
) -> ScoringResult:
    """
    LLM 없이 로컬에서 4-카테고리 스코어링을 수행합니다.

    Args:
        ticker:             종목 코드
        indicator_signals:  기술적 지표 결과 리스트
        conflict_report:    충돌 분석 결과 (없으면 자동 생성)
        financial_data:     재무 데이터 (선택)
        supply_demand_data: 수급 데이터 (선택)
        macro_data:         거시경제 데이터 (선택)

    Returns:
        ScoringResult: 0~100점 스코어링 결과
    """
    # 충돌 분석이 없으면 생성
    if conflict_report is None and indicator_signals:
        conflict_report = analyze_conflicts(indicator_signals)

    # 4개 카테고리 스코어링
    tech_score = score_technical(indicator_signals, conflict_report)
    fin_score = score_financial(financial_data)
    sd_score = score_supply_demand(supply_demand_data)
    macro_score = score_macro(macro_data)

    categories = [tech_score, fin_score, sd_score, macro_score]
    total = sum(c.score for c in categories)

    conflict_text = None
    if conflict_report:
        conflict_text = conflict_report.reasoning

    return ScoringResult(
        ticker=ticker,
        total_score=round(total, 2),
        categories=categories,
        final_signal=_determine_signal(total),
        conflict_report=conflict_text,
    )


# ─── 통합 스코어링 함수 (LLM 우선 → 로컬 폴백) ────────────────────────────────
async def calculate_total_score(
    ticker: str,
    indicator_signals: list[IndicatorSignal],
    api_key: Optional[str] = None,
    financial_data: Optional[dict] = None,
    supply_demand_data: Optional[dict] = None,
    macro_data: Optional[dict] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
) -> ScoringResult:
    """
    종합 스코어링을 수행합니다.
    API Key가 있으면 LLM 스코어링을 시도하고, 실패 시 로컬 스코어링으로 폴백합니다.

    Args:
        ticker:             종목 코드
        indicator_signals:  기술적 지표 결과 리스트
        api_key:            OpenAI 호환 API Key (없으면 로컬 스코어링)
        financial_data:     재무 데이터 (선택)
        supply_demand_data: 수급 데이터 (선택)
        macro_data:         거시경제 데이터 (선택)
        model:              LLM 모델명
        base_url:           API 베이스 URL

    Returns:
        ScoringResult: 0~100점 스코어링 결과
    """
    # 충돌 분석
    conflict_report = analyze_conflicts(indicator_signals)

    # LLM 스코어링 시도
    if api_key and api_key.strip():
        llm_result = await score_with_llm(
            ticker, indicator_signals, conflict_report, api_key, model, base_url
        )
        if llm_result:
            return llm_result

    # 로컬 폴백
    return score_local(
        ticker=ticker,
        indicator_signals=indicator_signals,
        conflict_report=conflict_report,
        financial_data=financial_data,
        supply_demand_data=supply_demand_data,
        macro_data=macro_data,
    )
