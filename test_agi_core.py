"""
AGI 코어 단위 테스트
─────────────────────
indicators, conflict_watchdog, scoring, nl_parser 모듈 검증
"""

import sys
import os
import asyncio
import numpy as np
import pandas as pd

# agi_core 패키지 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agi_core.engine.indicators import (
    calc_sma, calc_ema, calc_rsi, calc_macd, calc_bollinger, calc_stochastic,
    calculate_indicators, calculate_all_indicators,
    SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD,
)
from agi_core.engine.conflict_watchdog import analyze_conflicts, ConflictReport
from agi_core.engine.scoring import score_local, score_technical, score_financial, score_macro, score_supply_demand
from agi_core.parser.nl_parser import parse_query_fallback, ParsedQuery


def generate_test_ohlcv(n: int = 200, trend: str = "up") -> pd.DataFrame:
    """테스트용 OHLCV DataFrame 생성"""
    np.random.seed(42)
    base_price = 100.0

    if trend == "up":
        drift = 0.002
    elif trend == "down":
        drift = -0.002
    else:
        drift = 0.0

    returns = np.random.normal(drift, 0.015, n)
    prices = base_price * np.cumprod(1 + returns)

    df = pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.005, 0.005, n)),
        "high": prices * (1 + np.random.uniform(0.002, 0.02, n)),
        "low": prices * (1 - np.random.uniform(0.002, 0.02, n)),
        "close": prices,
        "volume": np.random.randint(1_000_000, 10_000_000, n),
    })
    return df


def test_separator(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


# ─── 테스트 1: 기술적 지표 계산 ─────────────────────────────────────────────────
def test_indicators():
    test_separator("TEST 1: 기술적 지표 계산")
    df = generate_test_ohlcv(200, "up")

    # SMA
    sma = calc_sma(df)
    print(f"  SMA → 신호: {sma.signal}, 신뢰도: {sma.confidence:.2f}")
    print(f"         값: {sma.values}")
    assert sma.signal in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD)
    assert 0 <= sma.confidence <= 1

    # EMA
    ema = calc_ema(df)
    print(f"  EMA → 신호: {ema.signal}, 신뢰도: {ema.confidence:.2f}")
    assert ema.signal in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD)

    # RSI
    rsi = calc_rsi(df)
    print(f"  RSI → 신호: {rsi.signal}, 신뢰도: {rsi.confidence:.2f}")
    print(f"         RSI 값: {rsi.values['rsi']}")
    assert 0 <= rsi.values["rsi"] <= 100

    # MACD
    macd = calc_macd(df)
    print(f"  MACD → 신호: {macd.signal}, 신뢰도: {macd.confidence:.2f}")
    print(f"          MACD: {macd.values['macd_line']}, Signal: {macd.values['signal_line']}")
    assert macd.signal in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD)

    # 볼린저 밴드
    bb = calc_bollinger(df)
    print(f"  Bollinger → 신호: {bb.signal}, 신뢰도: {bb.confidence:.2f}")
    print(f"              %B: {bb.values['percent_b']}")
    assert bb.values["upper_band"] is not None
    assert bb.values["lower_band"] is not None

    # 스토캐스틱
    stoch = calc_stochastic(df)
    print(f"  Stochastic → 신호: {stoch.signal}, 신뢰도: {stoch.confidence:.2f}")
    print(f"               %K: {stoch.values['percent_k']}, %D: {stoch.values['percent_d']}")
    assert 0 <= stoch.values["percent_k"] <= 100

    # 일괄 계산
    all_signals = calculate_all_indicators(df)
    print(f"\n  ▶ 전체 지표 ({len(all_signals)}개) 일괄 계산 완료")
    for sig in all_signals:
        print(f"    - {sig.name}: {sig.signal} (신뢰도 {sig.confidence:.2f})")

    print("\n  ✓ 기술적 지표 테스트 통과!")
    return all_signals


# ─── 테스트 2: 충돌 중재 엔진 ───────────────────────────────────────────────────
def test_conflict_watchdog(signals=None):
    test_separator("TEST 2: Conflict Watchdog (충돌 중재 엔진)")

    if signals is None:
        df = generate_test_ohlcv(200, "up")
        signals = calculate_all_indicators(df)

    report = analyze_conflicts(signals)
    print(f"  총 신호 수: {report.total_signals}")
    print(f"  매수: {report.buy_count} ({report.buy_ratio:.1%})")
    print(f"  매도: {report.sell_count} ({report.sell_ratio:.1%})")
    print(f"  관망: {report.hold_count} ({report.hold_ratio:.1%})")
    print(f"  충돌 감지: {'⚠ 예' if report.conflicts_detected else '✓ 없음'}")
    print(f"  최종 판단: {report.weighted_signal} (신뢰도 {report.weighted_confidence:.2%})")
    print(f"\n  분석 근거:")
    for line in report.reasoning.split("\n"):
        print(f"    {line}")

    assert report.total_signals == len(signals)
    assert abs(report.buy_ratio + report.sell_ratio + report.hold_ratio - 1.0) < 0.001
    assert report.weighted_signal in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD)

    # 빈 신호 테스트
    empty_report = analyze_conflicts([])
    assert empty_report.total_signals == 0
    assert empty_report.weighted_signal == SIGNAL_HOLD

    print("\n  ✓ 충돌 중재 엔진 테스트 통과!")
    return report


# ─── 테스트 3: 스코어링 알고리즘 ───────────────────────────────────────────────
def test_scoring():
    test_separator("TEST 3: 4-카테고리 스코어링")

    df = generate_test_ohlcv(200, "up")
    signals = calculate_all_indicators(df)

    # 로컬 스코어링 (재무/수급/거시 데이터 없음 → 기본값)
    result = score_local("AAPL", signals)
    print(f"  종목: {result.ticker}")
    print(f"  총점: {result.total_score}/100")
    print(f"  최종 신호: {result.final_signal}")
    for cat in result.categories:
        print(f"    [{cat.category:>15}] {cat.score:5.1f}/25 — {cat.details}")

    assert 0 <= result.total_score <= 100
    assert result.final_signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
    assert len(result.categories) == 4
    assert all(0 <= c.score <= 25 for c in result.categories)

    # 재무 데이터 포함 테스트
    print(f"\n  ── 재무 데이터 포함 테스트 ──")
    result_with_data = score_local(
        "AAPL", signals,
        financial_data={"per": 15.2, "roe": 25.3, "debt_ratio": 45, "revenue_growth": 12.5},
        supply_demand_data={"foreign_net": 5e9, "volume_trend": "increasing"},
        macro_data={"interest_rate_trend": "falling", "vix": 18, "gdp_growth": 2.5},
    )
    print(f"  총점: {result_with_data.total_score}/100")
    print(f"  최종 신호: {result_with_data.final_signal}")
    for cat in result_with_data.categories:
        print(f"    [{cat.category:>15}] {cat.score:5.1f}/25 — {cat.details}")

    assert 0 <= result_with_data.total_score <= 100

    print("\n  ✓ 스코어링 테스트 통과!")


# ─── 테스트 4: 자연어 파서 (폴백) ───────────────────────────────────────────────
def test_nl_parser():
    test_separator("TEST 4: 자연어 파서 (규칙 기반 폴백)")

    test_cases = [
        # 기존 테스트
        ("애플 주가 3개월치 캔들차트로 띄워줘", "AAPL", "candlestick", "3mo", "stock"),
        ("비트코인 1년 라인차트", "BTC/USDT", "line", "1y", "crypto"),
        ("테슬라 6개월 볼린저밴드", "TSLA", "candlestick", "6mo", "stock"),
        ("삼성전자 한달 RSI MACD", "005930.KS", "candlestick", "1mo", "stock"),
        ("이더리움 일주일", "ETH/USDT", "candlestick", "5d", "crypto"),
        # 신규: 확장 매핑 테스트 (기존에는 AAPL로 빠지던 종목들)
        ("현대차 3개월 차트", "005380.KS", "candlestick", "3mo", "stock"),
        ("LG에너지솔루션 6개월", "373220.KS", "candlestick", "6mo", "stock"),
        ("포스코 1년 RSI", "005490.KS", "candlestick", "1y", "stock"),
        ("카카오 한달 MACD", "035720.KQ", "candlestick", "1mo", "stock"),
        ("솔라나 3개월 라인차트", "SOL/USDT", "line", "3mo", "crypto"),
        # 신규: 동적 기간 추출 테스트
        ("삼성전자 2개월", "005930.KS", "candlestick", "2mo", "stock"),
        ("애플 10년", "AAPL", "candlestick", "10y", "stock"),
    ]

    for user_input, expected_ticker, expected_chart, expected_period, expected_asset in test_cases:
        result = parse_query_fallback(user_input)
        status = "PASS" if result.target_ticker == expected_ticker else "FAIL"
        print(f"  [{status}] \"{user_input}\"")
        print(f"      -> ticker={result.target_ticker}, chart={result.chart_type}, "
              f"period={result.period}, asset={result.asset_type}")
        print(f"        indicators={result.required_indicators}")

        assert result.target_ticker == expected_ticker, f"Expected {expected_ticker}, got {result.target_ticker}"
        assert result.chart_type == expected_chart, f"Expected {expected_chart}, got {result.chart_type}"
        assert result.period == expected_period, f"Expected {expected_period}, got {result.period}"
        assert result.asset_type == expected_asset, f"Expected {expected_asset}, got {result.asset_type}"

    # 동적 추출 테스트: 매핑에 없는 종목
    print("\n  -- 동적 추출 테스트 --")
    r1 = parse_query_fallback("005930 3개월 차트")
    print(f"  [6자리 코드] '005930 3개월 차트' -> {r1.target_ticker}")
    assert r1.target_ticker == "005930.KS", f"Expected 005930.KS, got {r1.target_ticker}"

    r2 = parse_query_fallback("PLTR 1년")
    print(f"  [영문 티커] 'PLTR 1년' -> {r2.target_ticker}")
    assert r2.target_ticker == "PLTR", f"Expected PLTR, got {r2.target_ticker}"

    print("\n  PASS: 자연어 파서 테스트 통과!")


# ─── 테스트 5: 시장 조건별 충돌 시나리오 ────────────────────────────────────────
def test_conflict_scenarios():
    test_separator("TEST 5: 충돌 시나리오 테스트")
    from agi_core.engine.indicators import IndicatorSignal

    # 시나리오 A: 전원 BUY (충돌 없음)
    print("  ── 시나리오 A: 전원 매수 ──")
    all_buy = [
        IndicatorSignal("RSI", SIGNAL_BUY, 0.8, {}, "과매도"),
        IndicatorSignal("MACD", SIGNAL_BUY, 0.7, {}, "골든크로스"),
        IndicatorSignal("SMA", SIGNAL_BUY, 0.6, {}, "상승추세"),
    ]
    report_a = analyze_conflicts(all_buy)
    print(f"    충돌: {report_a.conflicts_detected}, 결론: {report_a.weighted_signal}")
    assert not report_a.conflicts_detected
    assert report_a.weighted_signal == SIGNAL_BUY

    # 시나리오 B: BUY vs SELL (충돌)
    print("  ── 시나리오 B: 매수 vs 매도 충돌 ──")
    mixed = [
        IndicatorSignal("RSI", SIGNAL_BUY, 0.85, {}, "과매도"),
        IndicatorSignal("MACD", SIGNAL_SELL, 0.75, {}, "데드크로스"),
        IndicatorSignal("SMA", SIGNAL_BUY, 0.6, {}, "골든크로스"),
        IndicatorSignal("Bollinger Bands", SIGNAL_SELL, 0.5, {}, "상단돌파"),
    ]
    report_b = analyze_conflicts(mixed)
    print(f"    충돌: {report_b.conflicts_detected}, 결론: {report_b.weighted_signal}")
    print(f"    가중 신뢰도: {report_b.weighted_confidence:.2%}")
    assert report_b.conflicts_detected

    # 시나리오 C: 전원 HOLD
    print("  ── 시나리오 C: 전원 관망 ──")
    all_hold = [
        IndicatorSignal("RSI", SIGNAL_HOLD, 0.5, {}, "중립"),
        IndicatorSignal("MACD", SIGNAL_HOLD, 0.4, {}, "수렴"),
    ]
    report_c = analyze_conflicts(all_hold)
    print(f"    충돌: {report_c.conflicts_detected}, 결론: {report_c.weighted_signal}")
    assert not report_c.conflicts_detected
    assert report_c.weighted_signal == SIGNAL_HOLD

    print("\n  ✓ 충돌 시나리오 테스트 통과!")


# ─── 메인 ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  AGI 코어 단위 테스트 시작")
    print("=" * 60)

    signals = test_indicators()
    test_conflict_watchdog(signals)
    test_scoring()
    test_nl_parser()
    test_conflict_scenarios()

    print("\n" + "=" * 60)
    print("  🎉 모든 테스트 통과!")
    print("=" * 60)
