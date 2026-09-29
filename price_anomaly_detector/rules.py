"""Decides whether a ticker's latest metrics count as unusual.

Each rule compares a ticker against its own history rather than a fixed
threshold, since "normal" volatility for NVDA and "normal" volatility for a
utility stock are not the same number.
"""

from __future__ import annotations

from dataclasses import dataclass

from price_anomaly_detector.analytics import TickerMetrics
from price_anomaly_detector.config import Rules


@dataclass
class Flag:
    rule: str
    message: str


@dataclass
class TickerResult:
    ticker: str
    flags: list[Flag]

    @property
    def fired(self) -> bool:
        return len(self.flags) > 0


def check_volatility_spike(metrics: TickerMetrics, rules: Rules) -> Flag | None:
    short = metrics.latest(metrics.volatility_short)
    baseline = metrics.latest(metrics.volatility_baseline)
    if short is None or baseline is None or baseline == 0:
        return None

    ratio = short / baseline
    if ratio >= rules.volatility_ratio_threshold:
        return Flag(
            rule="volatility_spike",
            message=(
                f"20-day volatility is {ratio:.1f}x its 90-day average "
                f"({short:.1%} vs {baseline:.1%})."
            ),
        )
    return None


def check_drawdown(metrics: TickerMetrics, rules: Rules) -> Flag | None:
    dd = metrics.latest(metrics.drawdown)
    if dd is None:
        return None

    # max_drawdown returns a negative ratio (e.g. -0.12 for a 12% drop).
    if abs(dd) >= rules.drawdown_threshold:
        return Flag(
            rule="drawdown",
            message=f"Down {abs(dd):.1%} from its recent high.",
        )
    return None


def check_rsi(metrics: TickerMetrics, rules: Rules) -> Flag | None:
    rsi = metrics.latest(metrics.rsi)
    if rsi is None:
        return None

    if rsi >= rules.rsi_overbought:
        return Flag(rule="rsi_overbought", message=f"RSI at {rsi:.0f}, in overbought territory.")
    if rsi <= rules.rsi_oversold:
        return Flag(rule="rsi_oversold", message=f"RSI at {rsi:.0f}, in oversold territory.")
    return None


def check_bollinger_breach(metrics: TickerMetrics, rules: Rules) -> Flag | None:
    close = metrics.latest(metrics.close)
    upper = metrics.latest(metrics.bollinger_upper)
    lower = metrics.latest(metrics.bollinger_lower)
    if close is None or upper is None or lower is None:
        return None

    if close >= upper + rules.bollinger_breach_std:
        return Flag(
            rule="bollinger_breach_upper",
            message=f"Price {close:.2f} is at or above its upper Bollinger Band ({upper:.2f}).",
        )
    if close <= lower - rules.bollinger_breach_std:
        return Flag(
            rule="bollinger_breach_lower",
            message=f"Price {close:.2f} is at or below its lower Bollinger Band ({lower:.2f}).",
        )
    return None


RULE_CHECKS = [check_volatility_spike, check_drawdown, check_rsi, check_bollinger_breach]


def evaluate(metrics: TickerMetrics, rules: Rules) -> TickerResult:
    flags = [flag for check in RULE_CHECKS for flag in [check(metrics, rules)] if flag is not None]
    return TickerResult(ticker=metrics.ticker, flags=flags)
