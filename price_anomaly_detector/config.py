"""Loads the YAML config that holds tickers, window sizes, and rule thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class Windows:
    volatility_short: int
    volatility_baseline: int
    drawdown_window: int
    rsi_window: int
    bollinger_window: int


@dataclass
class Rules:
    volatility_ratio_threshold: float
    drawdown_threshold: float
    rsi_overbought: float
    rsi_oversold: float
    bollinger_breach_std: float


@dataclass
class Config:
    tickers: list[str]
    lookback_days: int
    windows: Windows
    rules: Rules


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    return Config(
        tickers=raw["tickers"],
        lookback_days=raw["lookback_days"],
        windows=Windows(**raw["windows"]),
        rules=Rules(**raw["rules"]),
    )
