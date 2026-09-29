"""Computes rolling risk metrics per ticker using gs_quant.timeseries.

Everything here runs on local pandas Series. The functions used from
gs_quant (volatility, max_drawdown, relative_strength_index, bollinger_bands)
are pure calculations on a price series and don't touch GsSession or need
any credentials, unlike the parts of gs-quant that pull data from Marquee.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from gs_quant.timeseries import Window, bollinger_bands, max_drawdown, relative_strength_index, volatility


@dataclass
class TickerMetrics:
    ticker: str
    close: pd.Series
    volatility_short: pd.Series
    volatility_baseline: pd.Series
    drawdown: pd.Series
    rsi: pd.Series
    bollinger_upper: pd.Series
    bollinger_lower: pd.Series

    def latest(self, series: pd.Series) -> float | None:
        clean = series.dropna()
        return float(clean.iloc[-1]) if not clean.empty else None


def compute_metrics(ticker: str, df: pd.DataFrame, windows) -> TickerMetrics:
    """Compute rolling metrics for one ticker's OHLC history.

    `windows` is a config.Windows instance with the rolling window sizes.
    Window(n, n) uses a full ramp-up so the first `n` values aren't computed
    off a partial window.
    """
    close = df["Close"]

    vol_short = volatility(close, Window(windows.volatility_short, windows.volatility_short))
    vol_baseline = volatility(close, Window(windows.volatility_baseline, windows.volatility_baseline))
    drawdown = max_drawdown(close, Window(windows.drawdown_window, windows.drawdown_window))
    rsi = relative_strength_index(close, Window(windows.rsi_window, windows.rsi_window))

    # bollinger_bands returns pd.concat([lower, upper], axis=1), so column 0
    # is the lower band and column 1 is the upper band.
    bands = bollinger_bands(close, Window(windows.bollinger_window, windows.bollinger_window))
    lower = bands.iloc[:, 0]
    upper = bands.iloc[:, 1]

    return TickerMetrics(
        ticker=ticker,
        close=close,
        volatility_short=vol_short,
        volatility_baseline=vol_baseline,
        drawdown=drawdown,
        rsi=rsi,
        bollinger_upper=upper,
        bollinger_lower=lower,
    )
