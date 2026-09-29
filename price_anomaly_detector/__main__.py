"""CLI entrypoint: python -m price_anomaly_detector"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from price_anomaly_detector.analytics import compute_metrics
from price_anomaly_detector.config import DEFAULT_CONFIG_PATH, load_config
from price_anomaly_detector.data import DEFAULT_DB_PATH, fetch_prices
from price_anomaly_detector.report import DEFAULT_REPORTS_DIR, format_console, write_markdown_report
from price_anomaly_detector.rules import evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="price-anomaly-detector",
        description="Check a basket of stocks for unusual volatility, drawdowns, RSI, or Bollinger Band breaches.",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.yaml"
    )
    parser.add_argument(
        "--tickers", nargs="+", default=None, help="Override the ticker list from config.yaml"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_REPORTS_DIR, help="Directory to write the markdown report to"
    )
    parser.add_argument(
        "--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to the local SQLite price cache"
    )
    parser.add_argument(
        "--llm-commentary", action="store_true", help="Add one sentence of LLM context per flagged ticker"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    tickers = args.tickers or config.tickers
    run_date = date.today()

    prices = fetch_prices(tickers, config.lookback_days, db_path=args.db_path, end_date=run_date)

    results = []
    for ticker in tickers:
        df = prices.get(ticker)
        if df is None or df.empty:
            print(f"No price data for {ticker}, skipping.")
            continue
        metrics = compute_metrics(ticker, df, config.windows)
        results.append(evaluate(metrics, config.rules))

    commentary = {}
    if args.llm_commentary:
        from price_anomaly_detector.llm import generate_commentary

        commentary = generate_commentary(results)

    print(format_console(results, run_date))

    out_path = write_markdown_report(results, run_date, reports_dir=args.output_dir, commentary=commentary)
    print(f"\nReport written to {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
