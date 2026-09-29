# price-anomaly-detector

A small daily monitoring tool for a basket of stocks. It pulls price data,
compares each stock's recent volatility, drawdown, RSI, and Bollinger Bands
against its own history, and writes a plain-English report when something
looks off. Think of it as a tripwire, not a signal generator: most days
nothing fires, and when something does fire it tells you exactly why.

## Setup

```bash
git clone <this-repo-url>
cd price-anomaly-detector
python -m venv .venv
source .venv/Scripts/activate   # .venv\Scripts\activate on plain cmd, source .venv/bin/activate on Linux/Mac
pip install -r requirements.txt
```

Then run it:

```bash
python -m price_anomaly_detector
```

That checks the tickers listed in `config.yaml` and writes a report to
`reports/report-YYYY-MM-DD.md`, plus a console summary.

Useful flags:

```bash
python -m price_anomaly_detector --tickers AAPL TSLA NVDA
python -m price_anomaly_detector --output-dir /tmp/reports
python -m price_anomaly_detector --llm-commentary   # needs ANTHROPIC_API_KEY or OPENAI_API_KEY
```

Run `python -m price_anomaly_detector --help` for the full list.

## Example output

```
price-anomaly-detector report for 2026-09-29

3 of 7 tickers flagged:

  AAPL: Down 11.1% from its recent high.
  TSLA: 20-day volatility is 2.1x its 90-day average. Down 33.0% from its recent high.
  NVDA: RSI at 78, in overbought territory.

Report written to reports/report-2026-09-29.md
```

The markdown file in `reports/` has the same information with a bit more
structure, one section per flagged ticker.

## How it works

Every run pulls daily OHLC data for each ticker with `yfinance` and caches
it in a local SQLite database (`data/prices.db`) so a second run the same
day doesn't re-download history that hasn't changed.

For each ticker it computes four things using Goldman Sachs's
`gs-quant` timeseries library, all of which run locally on the price series
with no API key or account needed:

- **Rolling volatility**, 20-day window compared against a 90-day baseline
- **Max drawdown**, biggest peak-to-trough drop over a 60-day window
- **RSI**, 14-day relative strength index
- **Bollinger Bands**, 20-day moving average plus/minus 2 standard deviations

A ticker gets flagged when, for example, its 20-day volatility is at least
1.8x its own 90-day average, or it's down 10%+ from its recent high, or its
RSI crosses into overbought/oversold territory. The point of comparing
against each stock's own history instead of one fixed number for every
ticker is that "normal" volatility for NVDA and "normal" volatility for a
utility stock aren't the same thing. All the thresholds live in
`config.yaml`, not buried in the rule logic.

If you pass `--llm-commentary` and have `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY` set, each flagged ticker gets one extra sentence of
plain-English context from the model. Without a key set, this is skipped
silently (well, one line saying it's skipped) and the rest of the tool
works exactly the same.

## Limitations

- **Not investment advice.** It flags statistical outliers, nothing more.
- Doesn't know about news, earnings, macro events, or anything else that
  might actually explain a move. A stock down 20% after a bad earnings
  call and a stock down 20% for no clear reason look identical to this
  tool.
- The rule thresholds (1.8x volatility, 10% drawdown, etc.) are a
  simplification. They're reasonable defaults, not the result of rigorous
  backtesting.
- RSI and Bollinger Bands were originally designed for shorter-term
  technical trading, not as fundamental measures of "something is wrong."
  Treat a flag as "worth a look," not as a diagnosis.
- Baselines get noisier for tickers with less price history, since a
  90-day rolling average needs 90 days of data to mean much.

## What I'd build next

- Backtest the rule thresholds against a few years of history to see how
  often they'd have actually caught something worth catching, instead of
  firing constantly or never firing at all.
- Add a volume-based rule (unusual trading volume relative to average),
  since volume spikes are often a leading indicator before volatility
  shows up in the price itself.
- Track how long a ticker stays flagged across consecutive days, so the
  report can distinguish "just started acting up" from "has been unusual
  for a week straight."

## Tests

```bash
pytest
```

The test suite covers the rule engine (each rule with values that should
and shouldn't fire, edge cases like a zero baseline or an all-NaN series)
and the report formatting (quiet days, flagged days, commentary insertion).
It doesn't hit the network or gs-quant, everything runs on fabricated
pandas Series.
