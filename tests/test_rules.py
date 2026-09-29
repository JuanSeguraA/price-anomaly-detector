"""Tests for the rule engine, using fabricated TickerMetrics so we don't need
real market data or gs_quant to test the decision logic itself."""

from __future__ import annotations

import pandas as pd
import pytest

from price_anomaly_detector.analytics import TickerMetrics
from price_anomaly_detector.config import Rules
from price_anomaly_detector.rules import (
    check_bollinger_breach,
    check_drawdown,
    check_rsi,
    check_volatility_spike,
    evaluate,
)


def series(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2026-01-01", periods=len(values)))


def make_metrics(
    close: list[float] = None,
    volatility_short: list[float] = None,
    volatility_baseline: list[float] = None,
    drawdown: list[float] = None,
    rsi: list[float] = None,
    bollinger_upper: list[float] = None,
    bollinger_lower: list[float] = None,
) -> TickerMetrics:
    return TickerMetrics(
        ticker="TEST",
        close=series(close or [100.0]),
        volatility_short=series(volatility_short or [0.2]),
        volatility_baseline=series(volatility_baseline or [0.2]),
        drawdown=series(drawdown or [-0.05]),
        rsi=series(rsi or [50.0]),
        bollinger_upper=series(bollinger_upper or [110.0]),
        bollinger_lower=series(bollinger_lower or [90.0]),
    )


DEFAULT_RULES = Rules(
    volatility_ratio_threshold=1.8,
    drawdown_threshold=0.10,
    rsi_overbought=70,
    rsi_oversold=30,
    bollinger_breach_std=0.0,
)


class TestVolatilitySpike:
    def test_fires_above_threshold(self):
        metrics = make_metrics(volatility_short=[0.40], volatility_baseline=[0.20])
        flag = check_volatility_spike(metrics, DEFAULT_RULES)
        assert flag is not None
        assert flag.rule == "volatility_spike"
        assert "2.0x" in flag.message

    def test_does_not_fire_below_threshold(self):
        metrics = make_metrics(volatility_short=[0.30], volatility_baseline=[0.20])
        assert check_volatility_spike(metrics, DEFAULT_RULES) is None

    def test_handles_zero_baseline(self):
        metrics = make_metrics(volatility_short=[0.10], volatility_baseline=[0.0])
        assert check_volatility_spike(metrics, DEFAULT_RULES) is None

    def test_handles_all_nan(self):
        metrics = make_metrics(volatility_short=[float("nan")], volatility_baseline=[0.2])
        assert check_volatility_spike(metrics, DEFAULT_RULES) is None


class TestDrawdown:
    def test_fires_when_drop_exceeds_threshold(self):
        metrics = make_metrics(drawdown=[-0.15])
        flag = check_drawdown(metrics, DEFAULT_RULES)
        assert flag is not None
        assert flag.rule == "drawdown"
        assert "15.0%" in flag.message

    def test_does_not_fire_for_small_drop(self):
        metrics = make_metrics(drawdown=[-0.03])
        assert check_drawdown(metrics, DEFAULT_RULES) is None

    def test_fires_exactly_at_threshold(self):
        metrics = make_metrics(drawdown=[-0.10])
        assert check_drawdown(metrics, DEFAULT_RULES) is not None


class TestRsi:
    def test_fires_overbought(self):
        metrics = make_metrics(rsi=[85.0])
        flag = check_rsi(metrics, DEFAULT_RULES)
        assert flag is not None
        assert flag.rule == "rsi_overbought"

    def test_fires_oversold(self):
        metrics = make_metrics(rsi=[12.0])
        flag = check_rsi(metrics, DEFAULT_RULES)
        assert flag is not None
        assert flag.rule == "rsi_oversold"

    def test_does_not_fire_in_neutral_range(self):
        metrics = make_metrics(rsi=[55.0])
        assert check_rsi(metrics, DEFAULT_RULES) is None


class TestBollingerBreach:
    def test_fires_above_upper_band(self):
        metrics = make_metrics(close=[115.0], bollinger_upper=[110.0], bollinger_lower=[90.0])
        flag = check_bollinger_breach(metrics, DEFAULT_RULES)
        assert flag is not None
        assert flag.rule == "bollinger_breach_upper"

    def test_fires_below_lower_band(self):
        metrics = make_metrics(close=[85.0], bollinger_upper=[110.0], bollinger_lower=[90.0])
        flag = check_bollinger_breach(metrics, DEFAULT_RULES)
        assert flag is not None
        assert flag.rule == "bollinger_breach_lower"

    def test_does_not_fire_inside_bands(self):
        metrics = make_metrics(close=[100.0], bollinger_upper=[110.0], bollinger_lower=[90.0])
        assert check_bollinger_breach(metrics, DEFAULT_RULES) is None


class TestEvaluate:
    def test_returns_no_flags_for_quiet_ticker(self):
        metrics = make_metrics()
        result = evaluate(metrics, DEFAULT_RULES)
        assert result.fired is False
        assert result.flags == []

    def test_collects_multiple_flags(self):
        metrics = make_metrics(
            volatility_short=[0.5],
            volatility_baseline=[0.2],
            drawdown=[-0.20],
            rsi=[50.0],
            close=[100.0],
            bollinger_upper=[110.0],
            bollinger_lower=[90.0],
        )
        result = evaluate(metrics, DEFAULT_RULES)
        assert result.fired is True
        fired_rules = {f.rule for f in result.flags}
        assert fired_rules == {"volatility_spike", "drawdown"}

    def test_latest_ignores_trailing_nan(self):
        metrics = make_metrics(rsi=[50.0, 80.0, float("nan")])
        assert metrics.latest(metrics.rsi) == 80.0

    def test_latest_returns_none_for_all_nan(self):
        metrics = make_metrics(rsi=[float("nan"), float("nan")])
        assert metrics.latest(metrics.rsi) is None
