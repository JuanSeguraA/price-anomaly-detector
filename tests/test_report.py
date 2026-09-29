"""Tests for report formatting, using fabricated TickerResult objects."""

from __future__ import annotations

from datetime import date

from price_anomaly_detector.report import format_console, format_markdown
from price_anomaly_detector.rules import Flag, TickerResult

RUN_DATE = date(2026, 3, 15)


def test_console_reports_all_quiet_when_nothing_fired():
    results = [TickerResult(ticker="AAPL", flags=[]), TickerResult(ticker="MSFT", flags=[])]
    output = format_console(results, RUN_DATE)
    assert "Nothing unusual today" in output
    assert "2 tickers" in output


def test_console_lists_flagged_tickers_and_reasons():
    results = [
        TickerResult(
            ticker="AAPL",
            flags=[Flag(rule="drawdown", message="Down 12.0% from its recent high.")],
        ),
        TickerResult(ticker="MSFT", flags=[]),
    ]
    output = format_console(results, RUN_DATE)
    assert "1 of 2 tickers flagged" in output
    assert "AAPL: Down 12.0% from its recent high." in output
    assert "MSFT" not in output.split("flagged:")[1]


def test_console_omits_quiet_tickers_from_flag_list():
    results = [
        TickerResult(ticker="AAPL", flags=[Flag(rule="rsi_overbought", message="RSI at 85.")]),
        TickerResult(ticker="TSLA", flags=[]),
    ]
    output = format_console(results, RUN_DATE)
    lines_with_reasons = [line for line in output.splitlines() if ":" in line and "AAPL" in line]
    assert len(lines_with_reasons) == 1


def test_markdown_all_quiet():
    results = [TickerResult(ticker="AAPL", flags=[])]
    output = format_markdown(results, RUN_DATE)
    assert output.startswith("# Daily report: 2026-03-15")
    assert "Nothing unusual today" in output


def test_markdown_includes_ticker_heading_and_bullets():
    results = [
        TickerResult(
            ticker="NVDA",
            flags=[
                Flag(rule="volatility_spike", message="20-day volatility is 2.1x its 90-day average."),
                Flag(rule="rsi_overbought", message="RSI at 78."),
            ],
        )
    ]
    output = format_markdown(results, RUN_DATE)
    assert "## NVDA" in output
    assert "- **volatility_spike**: 20-day volatility is 2.1x its 90-day average." in output
    assert "- **rsi_overbought**: RSI at 78." in output


def test_markdown_includes_commentary_when_provided():
    results = [TickerResult(ticker="TSLA", flags=[Flag(rule="drawdown", message="Down 15%.")])]
    commentary = {"TSLA": "This kind of drop often follows a earnings miss or guidance cut."}
    output = format_markdown(results, RUN_DATE, commentary=commentary)
    assert "> This kind of drop often follows a earnings miss or guidance cut." in output


def test_markdown_skips_commentary_for_quiet_tickers():
    results = [
        TickerResult(ticker="TSLA", flags=[Flag(rule="drawdown", message="Down 15%.")]),
        TickerResult(ticker="AAPL", flags=[]),
    ]
    commentary = {"TSLA": "Some context.", "AAPL": "Should never appear."}
    output = format_markdown(results, RUN_DATE, commentary=commentary)
    assert "Should never appear" not in output
