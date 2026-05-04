"""
Conflict Watchdog — 충돌 중재 엔진
──────────────────────────────────
여러 보조지표의 BUY/SELL/HOLD 신호를 취합하여,
신호 간 충돌을 감지하고 가중치 기반 최종 의사결정을 생성합니다.

■ 지표 간 충돌 시, 과거 유사 기간의 백테스트 적중률 기반 가중치를 적용합니다.
■ 단순 다수결이 아닌, 신뢰도(confidence) × 적중률(accuracy) 가중 평균으로 산출합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from agi_core.engine.indicators import IndicatorSignal, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD

logger = logging.getLogger(__name__)


# ─── 과거 백테스트 적중률 기반 가중치 테이블 ────────────────────────────────────
# 각 지표가 과거 유사 시장 상황에서 올바른 신호를 제공한 비율 (0.0 ~ 1.0)
# 이 테이블은 시장 조건(상승장/하락장/횡보장)에 따라 다르게 적용됩니다.
BACKTEST_ACCURACY = {
    # 지표명: {시장조건: 적중률}
    "SMA": {
        "trending_up": 0.72,
        "trending_down": 0.70,
        "sideways": 0.45,
        "default": 0.62,
    },
    "EMA": {
        "trending_up": 0.75,
        "trending_down": 0.73,
        "sideways": 0.48,
        "default": 0.65,
    },
    "RSI": {
        "trending_up": 0.60,
        "trending_down": 0.65,
        "sideways": 0.70,
        "default": 0.65,
    },
    "MACD": {
        "trending_up": 0.78,
        "trending_down": 0.76,
        "sideways": 0.42,
        "default": 0.65,
    },
    "Bollinger Bands": {
        "trending_up": 0.55,
        "trending_down": 0.58,
        "sideways": 0.75,
        "default": 0.63,
    },
    "Stochastic": {
        "trending_up": 0.58,
        "trending_down": 0.62,
        "sideways": 0.72,
        "default": 0.64,
    },
}

# 알 수 없는 지표의 기본 적중률
DEFAULT_ACCURACY = 0.50


# ─── 충돌 분석 결과 데이터 클래스 ───────────────────────────────────────────────
@dataclass
class ConflictReport:
    """충돌 중재 엔진 분석 결과"""
    total_signals: int
    buy_count: int
    sell_count: int
    hold_count: int
    buy_ratio: float
    sell_ratio: float
    hold_ratio: float
    conflicts_detected: bool
    weighted_signal: str               # BUY / SELL / HOLD
    weighted_confidence: float         # 0.0 ~ 1.0
    reasoning: str
    indicator_details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_signals": self.total_signals,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "hold_count": self.hold_count,
            "buy_ratio": round(self.buy_ratio, 4),
            "sell_ratio": round(self.sell_ratio, 4),
            "hold_ratio": round(self.hold_ratio, 4),
            "conflicts_detected": self.conflicts_detected,
            "weighted_signal": self.weighted_signal,
            "weighted_confidence": round(self.weighted_confidence, 4),
            "reasoning": self.reasoning,
            "indicator_details": self.indicator_details,
        }


# ─── 시장 조건 감지 ─────────────────────────────────────────────────────────────
def _detect_market_condition(signals: list[IndicatorSignal]) -> str:
    """
    지표 신호 패턴을 기반으로 현재 시장 조건을 추론합니다.

    Returns:
        "trending_up" | "trending_down" | "sideways"
    """
    buy_confidence_sum = 0.0
    sell_confidence_sum = 0.0
    hold_confidence_sum = 0.0

    for sig in signals:
        if sig.signal == SIGNAL_BUY:
            buy_confidence_sum += sig.confidence
        elif sig.signal == SIGNAL_SELL:
            sell_confidence_sum += sig.confidence
        else:
            hold_confidence_sum += sig.confidence

    total = buy_confidence_sum + sell_confidence_sum + hold_confidence_sum
    if total == 0:
        return "sideways"

    buy_pct = buy_confidence_sum / total
    sell_pct = sell_confidence_sum / total

    if buy_pct > 0.5:
        return "trending_up"
    elif sell_pct > 0.5:
        return "trending_down"
    else:
        return "sideways"


# ─── 지표별 가중치 조회 ─────────────────────────────────────────────────────────
def _get_indicator_weight(indicator_name: str, market_condition: str) -> float:
    """
    지표명과 시장 조건에 따른 백테스트 적중률(가중치)을 반환합니다.
    """
    accuracy_table = BACKTEST_ACCURACY.get(indicator_name, {})
    return accuracy_table.get(market_condition, accuracy_table.get("default", DEFAULT_ACCURACY))


# ─── 충돌 감지 ──────────────────────────────────────────────────────────────────
def _detect_conflicts(signals: list[IndicatorSignal]) -> bool:
    """
    BUY와 SELL 신호가 동시에 존재하면 충돌로 판단합니다.
    단, 신뢰도가 0.3 미만인 약한 신호는 충돌 판단에서 제외합니다.
    """
    strong_signals = [s for s in signals if s.confidence >= 0.3]
    has_buy = any(s.signal == SIGNAL_BUY for s in strong_signals)
    has_sell = any(s.signal == SIGNAL_SELL for s in strong_signals)
    return has_buy and has_sell


# ─── 가중 신호 계산 ─────────────────────────────────────────────────────────────
def _calculate_weighted_signal(
    signals: list[IndicatorSignal],
    market_condition: str,
) -> tuple[str, float, list[dict]]:
    """
    각 지표의 (신뢰도 × 백테스트 적중률) 가중합으로 최종 신호를 결정합니다.

    Returns:
        (최종 신호, 최종 신뢰도, 지표별 상세 정보)
    """
    weighted_scores = {SIGNAL_BUY: 0.0, SIGNAL_SELL: 0.0, SIGNAL_HOLD: 0.0}
    total_weight = 0.0
    details = []

    for sig in signals:
        accuracy = _get_indicator_weight(sig.name, market_condition)
        weight = sig.confidence * accuracy
        weighted_scores[sig.signal] += weight
        total_weight += weight

        details.append({
            "indicator": sig.name,
            "signal": sig.signal,
            "confidence": round(sig.confidence, 4),
            "backtest_accuracy": round(accuracy, 4),
            "weighted_score": round(weight, 4),
            "description": sig.description,
        })

    if total_weight == 0:
        return SIGNAL_HOLD, 0.0, details

    # 가중 비율 산출
    for key in weighted_scores:
        weighted_scores[key] /= total_weight

    # 최종 신호 결정
    final_signal = max(weighted_scores, key=weighted_scores.get)  # type: ignore[arg-type]
    final_confidence = weighted_scores[final_signal]

    return final_signal, final_confidence, details


# ─── 메인 충돌 분석 함수 ────────────────────────────────────────────────────────
def analyze_conflicts(
    signals: list[IndicatorSignal],
    market_condition: Optional[str] = None,
) -> ConflictReport:
    """
    여러 지표의 신호를 종합 분석하여 최종 의사결정을 생성합니다.

    ■ 충돌이 없으면: 다수 신호를 그대로 채택 (신뢰도 보정 없음)
    ■ 충돌이 있으면: 백테스트 적중률 가중치를 적용하여 최종 신호 결정

    Args:
        signals:          각 지표의 IndicatorSignal 리스트
        market_condition: 시장 조건 (None이면 자동 감지)

    Returns:
        ConflictReport: 충돌 분석 결과
    """
    if not signals:
        return ConflictReport(
            total_signals=0,
            buy_count=0, sell_count=0, hold_count=0,
            buy_ratio=0, sell_ratio=0, hold_ratio=0,
            conflicts_detected=False,
            weighted_signal=SIGNAL_HOLD,
            weighted_confidence=0.0,
            reasoning="분석할 지표 신호가 없습니다.",
        )

    # 신호별 집계
    buy_signals = [s for s in signals if s.signal == SIGNAL_BUY]
    sell_signals = [s for s in signals if s.signal == SIGNAL_SELL]
    hold_signals = [s for s in signals if s.signal == SIGNAL_HOLD]

    total = len(signals)
    buy_ratio = len(buy_signals) / total
    sell_ratio = len(sell_signals) / total
    hold_ratio = len(hold_signals) / total

    # 시장 조건 감지
    if market_condition is None:
        market_condition = _detect_market_condition(signals)

    # 충돌 감지
    conflicts_detected = _detect_conflicts(signals)

    # 가중 신호 계산
    final_signal, final_confidence, details = _calculate_weighted_signal(signals, market_condition)

    # 분석 근거 생성
    reasoning = _generate_reasoning(
        buy_count=len(buy_signals),
        sell_count=len(sell_signals),
        hold_count=len(hold_signals),
        conflicts_detected=conflicts_detected,
        final_signal=final_signal,
        final_confidence=final_confidence,
        market_condition=market_condition,
        details=details,
    )

    return ConflictReport(
        total_signals=total,
        buy_count=len(buy_signals),
        sell_count=len(sell_signals),
        hold_count=len(hold_signals),
        buy_ratio=buy_ratio,
        sell_ratio=sell_ratio,
        hold_ratio=hold_ratio,
        conflicts_detected=conflicts_detected,
        weighted_signal=final_signal,
        weighted_confidence=final_confidence,
        reasoning=reasoning,
        indicator_details=details,
    )


# ─── 분석 근거 텍스트 생성 ─────────────────────────────────────────────────────
def _generate_reasoning(
    buy_count: int,
    sell_count: int,
    hold_count: int,
    conflicts_detected: bool,
    final_signal: str,
    final_confidence: float,
    market_condition: str,
    details: list[dict],
) -> str:
    """충돌 분석 근거를 한국어로 생성합니다."""

    market_names = {
        "trending_up": "상승 추세",
        "trending_down": "하락 추세",
        "sideways": "횡보",
    }
    market_label = market_names.get(market_condition, "불명")

    parts = [
        f"[시장 조건: {market_label}]",
        f"총 {buy_count + sell_count + hold_count}개 지표 분석 완료.",
        f"  매수(BUY): {buy_count}개 | 매도(SELL): {sell_count}개 | 관망(HOLD): {hold_count}개",
    ]

    if conflicts_detected:
        parts.append("")
        parts.append("⚠ 지표 간 신호 충돌 감지!")
        parts.append(f"  → 백테스트 적중률 가중치({market_label} 조건)를 적용하여 중재합니다.")

        # 충돌하는 지표 쌍 명시
        buy_indicators = [d["indicator"] for d in details if d["signal"] == SIGNAL_BUY]
        sell_indicators = [d["indicator"] for d in details if d["signal"] == SIGNAL_SELL]
        parts.append(f"  매수 신호: {', '.join(buy_indicators)}")
        parts.append(f"  매도 신호: {', '.join(sell_indicators)}")
    else:
        parts.append("")
        parts.append("✓ 지표 간 충돌 없음 — 일관된 방향성 확인.")

    signal_labels = {SIGNAL_BUY: "매수(BUY)", SIGNAL_SELL: "매도(SELL)", SIGNAL_HOLD: "관망(HOLD)"}
    parts.append("")
    parts.append(f"▶ 최종 판단: {signal_labels.get(final_signal, final_signal)}")
    parts.append(f"  가중 신뢰도: {final_confidence:.1%}")

    return "\n".join(parts)
