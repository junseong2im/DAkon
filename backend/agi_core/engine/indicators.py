"""
기술적 지표 계산 모듈 (Technical Indicators)
─────────────────────────────────────────────
pandas/numpy 기반으로 주요 기술적 지표를 벡터 연산합니다.

지원 지표:
  - SMA  (Simple Moving Average)
  - EMA  (Exponential Moving Average)
  - RSI  (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - 볼린저 밴드 (Bollinger Bands)
  - 스토캐스틱 (Stochastic Oscillator)

모든 함수는 pandas DataFrame을 입력으로 받고,
지표 값이 추가된 DataFrame 또는 결과 딕셔너리를 반환합니다.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─── 신호 상수 ──────────────────────────────────────────────────────────────────
SIGNAL_BUY = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_HOLD = "HOLD"


@dataclass
class IndicatorSignal:
    """개별 지표의 계산 결과 및 신호"""
    name: str
    signal: str            # BUY / SELL / HOLD
    confidence: float      # 0.0 ~ 1.0
    values: dict           # 지표 고유 값들
    description: str = ""  # 신호 근거 설명

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "signal": self.signal,
            "confidence": self.confidence,
            "values": self.values,
            "description": self.description,
        }


# ─── SMA (Simple Moving Average) ───────────────────────────────────────────────
def calc_sma(
    df: pd.DataFrame,
    column: str = "close",
    periods: Optional[list[int]] = None,
) -> IndicatorSignal:
    """
    단순이동평균을 계산하고 골든크로스/데드크로스 신호를 생성합니다.

    Args:
        df:      OHLCV DataFrame (close 컬럼 필수)
        column:  이동평균 대상 컬럼명
        periods: 이동평균 기간 목록 (기본: [20, 50, 200])
    """
    if periods is None:
        periods = [20, 50, 200]

    values = {}
    for period in periods:
        if len(df) >= period:
            sma = df[column].rolling(window=period).mean()
            values[f"sma_{period}"] = round(float(sma.iloc[-1]), 4) if not pd.isna(sma.iloc[-1]) else None
        else:
            values[f"sma_{period}"] = None

    # 신호 판단: 단기 SMA > 장기 SMA → 골든크로스 (BUY)
    current_price = float(df[column].iloc[-1])
    short_sma = values.get(f"sma_{periods[0]}")
    long_sma = values.get(f"sma_{periods[-1]}")

    signal = SIGNAL_HOLD
    confidence = 0.5
    description = ""

    if short_sma is not None and long_sma is not None:
        if short_sma > long_sma and current_price > short_sma:
            signal = SIGNAL_BUY
            confidence = min(0.6 + (short_sma - long_sma) / long_sma, 0.95)
            description = f"골든크로스: 단기 SMA({periods[0]})가 장기 SMA({periods[-1]}) 위"
        elif short_sma < long_sma and current_price < short_sma:
            signal = SIGNAL_SELL
            confidence = min(0.6 + (long_sma - short_sma) / long_sma, 0.95)
            description = f"데드크로스: 단기 SMA({periods[0]})가 장기 SMA({periods[-1]}) 아래"
        else:
            description = "이동평균 수렴 중 — 뚜렷한 방향성 없음"

    values["current_price"] = current_price
    return IndicatorSignal(name="SMA", signal=signal, confidence=confidence, values=values, description=description)


# ─── EMA (Exponential Moving Average) ──────────────────────────────────────────
def calc_ema(
    df: pd.DataFrame,
    column: str = "close",
    periods: Optional[list[int]] = None,
) -> IndicatorSignal:
    """
    지수이동평균을 계산합니다. SMA보다 최근 데이터에 높은 가중치를 부여합니다.
    """
    if periods is None:
        periods = [12, 26, 50]

    values = {}
    for period in periods:
        if len(df) >= period:
            ema = df[column].ewm(span=period, adjust=False).mean()
            values[f"ema_{period}"] = round(float(ema.iloc[-1]), 4)
        else:
            values[f"ema_{period}"] = None

    current_price = float(df[column].iloc[-1])
    short_ema = values.get(f"ema_{periods[0]}")
    long_ema = values.get(f"ema_{periods[-1]}")

    signal = SIGNAL_HOLD
    confidence = 0.5
    description = ""

    if short_ema is not None and long_ema is not None:
        if short_ema > long_ema:
            signal = SIGNAL_BUY
            confidence = min(0.6 + (short_ema - long_ema) / long_ema, 0.95)
            description = f"단기 EMA({periods[0]}) > 장기 EMA({periods[-1]}): 상승 추세"
        elif short_ema < long_ema:
            signal = SIGNAL_SELL
            confidence = min(0.6 + (long_ema - short_ema) / long_ema, 0.95)
            description = f"단기 EMA({periods[0]}) < 장기 EMA({periods[-1]}): 하락 추세"

    values["current_price"] = current_price
    return IndicatorSignal(name="EMA", signal=signal, confidence=confidence, values=values, description=description)


# ─── RSI (Relative Strength Index) ─────────────────────────────────────────────
def calc_rsi(
    df: pd.DataFrame,
    column: str = "close",
    period: int = 14,
) -> IndicatorSignal:
    """
    RSI를 계산합니다.
    - RSI < 30: 과매도 → BUY 신호
    - RSI > 70: 과매수 → SELL 신호
    - 30 ≤ RSI ≤ 70: HOLD
    """
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Wilder's smoothing (EMA 방식)
    for i in range(period, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

    signal = SIGNAL_HOLD
    confidence = 0.5
    description = ""

    if current_rsi < 30:
        signal = SIGNAL_BUY
        confidence = min(0.7 + (30 - current_rsi) / 100, 0.95)
        description = f"RSI {current_rsi:.1f} — 과매도 구간, 반등 가능성"
    elif current_rsi > 70:
        signal = SIGNAL_SELL
        confidence = min(0.7 + (current_rsi - 70) / 100, 0.95)
        description = f"RSI {current_rsi:.1f} — 과매수 구간, 조정 가능성"
    else:
        description = f"RSI {current_rsi:.1f} — 중립 구간"

    values = {
        "rsi": round(current_rsi, 2),
        "period": period,
        "overbought_threshold": 70,
        "oversold_threshold": 30,
    }

    return IndicatorSignal(name="RSI", signal=signal, confidence=confidence, values=values, description=description)


# ─── MACD (Moving Average Convergence Divergence) ──────────────────────────────
def calc_macd(
    df: pd.DataFrame,
    column: str = "close",
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> IndicatorSignal:
    """
    MACD를 계산합니다.
    - MACD 라인이 시그널 라인 상향돌파 → BUY
    - MACD 라인이 시그널 라인 하향돌파 → SELL
    """
    fast_ema = df[column].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df[column].ewm(span=slow_period, adjust=False).mean()

    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    current_macd = float(macd_line.iloc[-1])
    current_signal = float(signal_line.iloc[-1])
    current_hist = float(histogram.iloc[-1])
    prev_hist = float(histogram.iloc[-2]) if len(histogram) > 1 else 0

    signal = SIGNAL_HOLD
    confidence = 0.5
    description = ""

    if current_macd > current_signal:
        if prev_hist <= 0 < current_hist:
            signal = SIGNAL_BUY
            confidence = 0.8
            description = "MACD 골든크로스: 상승 전환 신호"
        else:
            signal = SIGNAL_BUY
            confidence = 0.6
            description = "MACD 라인이 시그널 라인 위 — 상승 추세 유지"
    elif current_macd < current_signal:
        if prev_hist >= 0 > current_hist:
            signal = SIGNAL_SELL
            confidence = 0.8
            description = "MACD 데드크로스: 하락 전환 신호"
        else:
            signal = SIGNAL_SELL
            confidence = 0.6
            description = "MACD 라인이 시그널 라인 아래 — 하락 추세 유지"

    values = {
        "macd_line": round(current_macd, 4),
        "signal_line": round(current_signal, 4),
        "histogram": round(current_hist, 4),
        "fast_period": fast_period,
        "slow_period": slow_period,
        "signal_period": signal_period,
    }

    return IndicatorSignal(name="MACD", signal=signal, confidence=confidence, values=values, description=description)


# ─── 볼린저 밴드 (Bollinger Bands) ─────────────────────────────────────────────
def calc_bollinger(
    df: pd.DataFrame,
    column: str = "close",
    period: int = 20,
    std_dev: float = 2.0,
) -> IndicatorSignal:
    """
    볼린저 밴드를 계산합니다.
    - 가격이 하단 밴드 이하 → BUY (과매도)
    - 가격이 상단 밴드 이상 → SELL (과매수)
    """
    sma = df[column].rolling(window=period).mean()
    rolling_std = df[column].rolling(window=period).std()

    upper_band = sma + (rolling_std * std_dev)
    lower_band = sma - (rolling_std * std_dev)

    current_price = float(df[column].iloc[-1])
    current_upper = float(upper_band.iloc[-1]) if not pd.isna(upper_band.iloc[-1]) else None
    current_lower = float(lower_band.iloc[-1]) if not pd.isna(lower_band.iloc[-1]) else None
    current_middle = float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None

    # %B 계산 (밴드 내 위치 비율: 0 = 하단, 1 = 상단)
    bandwidth = None
    percent_b = None
    if current_upper is not None and current_lower is not None and current_upper != current_lower:
        bandwidth = round((current_upper - current_lower) / current_middle * 100, 2)
        percent_b = round((current_price - current_lower) / (current_upper - current_lower), 4)

    signal = SIGNAL_HOLD
    confidence = 0.5
    description = ""

    if current_lower is not None and current_price <= current_lower:
        signal = SIGNAL_BUY
        confidence = 0.75
        description = f"가격이 하단 밴드({current_lower:.2f}) 이하 — 과매도 가능"
    elif current_upper is not None and current_price >= current_upper:
        signal = SIGNAL_SELL
        confidence = 0.75
        description = f"가격이 상단 밴드({current_upper:.2f}) 이상 — 과매수 가능"
    elif percent_b is not None:
        if percent_b < 0.3:
            signal = SIGNAL_BUY
            confidence = 0.55
            description = f"밴드 하단부(%B={percent_b:.2f}) — 반등 가능성"
        elif percent_b > 0.7:
            signal = SIGNAL_SELL
            confidence = 0.55
            description = f"밴드 상단부(%B={percent_b:.2f}) — 조정 가능성"
        else:
            description = f"밴드 중앙부(%B={percent_b:.2f}) — 중립"

    values = {
        "upper_band": round(current_upper, 4) if current_upper else None,
        "middle_band": round(current_middle, 4) if current_middle else None,
        "lower_band": round(current_lower, 4) if current_lower else None,
        "bandwidth": bandwidth,
        "percent_b": percent_b,
        "period": period,
        "std_dev": std_dev,
    }

    return IndicatorSignal(
        name="Bollinger Bands", signal=signal, confidence=confidence, values=values, description=description
    )


# ─── 스토캐스틱 오실레이터 (Stochastic Oscillator) ─────────────────────────────
def calc_stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
    smooth_k: int = 3,
) -> IndicatorSignal:
    """
    스토캐스틱 오실레이터를 계산합니다.
    - %K < 20 & %K > %D: 과매도 반등 → BUY
    - %K > 80 & %K < %D: 과매수 하락 → SELL
    """
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()

    # Fast %K
    fast_k = 100 * (df["close"] - low_min) / (high_max - low_min)

    # Slow %K (Fast %K의 이동평균)
    slow_k = fast_k.rolling(window=smooth_k).mean()

    # %D (Slow %K의 이동평균)
    slow_d = slow_k.rolling(window=d_period).mean()

    current_k = float(slow_k.iloc[-1]) if not pd.isna(slow_k.iloc[-1]) else 50.0
    current_d = float(slow_d.iloc[-1]) if not pd.isna(slow_d.iloc[-1]) else 50.0

    signal = SIGNAL_HOLD
    confidence = 0.5
    description = ""

    if current_k < 20 and current_k > current_d:
        signal = SIGNAL_BUY
        confidence = 0.75
        description = f"%K({current_k:.1f}) 과매도 구간에서 %D({current_d:.1f}) 상향돌파"
    elif current_k > 80 and current_k < current_d:
        signal = SIGNAL_SELL
        confidence = 0.75
        description = f"%K({current_k:.1f}) 과매수 구간에서 %D({current_d:.1f}) 하향돌파"
    elif current_k < 20:
        signal = SIGNAL_BUY
        confidence = 0.55
        description = f"%K({current_k:.1f}) 과매도 구간"
    elif current_k > 80:
        signal = SIGNAL_SELL
        confidence = 0.55
        description = f"%K({current_k:.1f}) 과매수 구간"
    else:
        description = f"%K({current_k:.1f}), %D({current_d:.1f}) — 중립 구간"

    values = {
        "percent_k": round(current_k, 2),
        "percent_d": round(current_d, 2),
        "k_period": k_period,
        "d_period": d_period,
    }

    return IndicatorSignal(
        name="Stochastic", signal=signal, confidence=confidence, values=values, description=description
    )


# ─── 지표 일괄 계산 ─────────────────────────────────────────────────────────────
INDICATOR_FUNCTIONS = {
    "sma": calc_sma,
    "ema": calc_ema,
    "rsi": calc_rsi,
    "macd": calc_macd,
    "bollinger": calc_bollinger,
    "stochastic": calc_stochastic,
}


def calculate_indicators(
    df: pd.DataFrame,
    indicator_names: Optional[list[str]] = None,
) -> list[IndicatorSignal]:
    """
    지정된 지표를 일괄 계산합니다.

    Args:
        df:              OHLCV DataFrame (컬럼: open, high, low, close, volume)
        indicator_names: 계산할 지표명 목록 (기본: 전체 계산)

    Returns:
        list[IndicatorSignal]: 각 지표의 계산 결과 및 신호 목록
    """
    if indicator_names is None:
        indicator_names = list(INDICATOR_FUNCTIONS.keys())

    results = []
    for name in indicator_names:
        name_lower = name.lower()
        if name_lower in INDICATOR_FUNCTIONS:
            try:
                result = INDICATOR_FUNCTIONS[name_lower](df)
                results.append(result)
                logger.info(f"[{name_lower}] 신호={result.signal}, 신뢰도={result.confidence:.2f}")
            except Exception as e:
                logger.error(f"[{name_lower}] 지표 계산 실패: {e}")
                results.append(IndicatorSignal(
                    name=name_lower,
                    signal=SIGNAL_HOLD,
                    confidence=0.0,
                    values={"error": str(e)},
                    description=f"계산 오류: {e}",
                ))
        else:
            logger.warning(f"지원하지 않는 지표: {name}")

    return results


def calculate_all_indicators(df: pd.DataFrame) -> list[IndicatorSignal]:
    """모든 지원 지표를 계산합니다."""
    return calculate_indicators(df, list(INDICATOR_FUNCTIONS.keys()))
