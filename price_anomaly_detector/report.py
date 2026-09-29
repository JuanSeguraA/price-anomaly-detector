"""Formats rule engine results into a console summary and a markdown report."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from price_anomaly_detector.rules import TickerResult

DEFAULT_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def format_console(results: list[TickerResult], run_date: date) -> str:
    fired = [r for r in results if r.fired]
    lines = [f"price-anomaly-detector report for {run_date.isoformat()}", ""]

    if not fired:
        lines.append(f"Nothing unusual today. Checked {len(results)} tickers, all quiet.")
        return "\n".join(lines)

    lines.append(f"{len(fired)} of {len(results)} tickers flagged:")
    lines.append("")
    for result in fired:
        for flag in result.flags:
            lines.append(f"  {result.ticker}: {flag.message}")

    return "\n".join(lines)


def format_markdown(
    results: list[TickerResult],
    run_date: date,
    commentary: dict[str, str] | None = None,
) -> str:
    fired = [r for r in results if r.fired]
    commentary = commentary or {}

    lines = [f"# Daily report: {run_date.isoformat()}", ""]

    if not fired:
        lines.append(f"Nothing unusual today. Checked {len(results)} tickers, all quiet.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"{len(fired)} of {len(results)} tickers flagged something unusual.")
    lines.append("")

    for result in fired:
        lines.append(f"## {result.ticker}")
        lines.append("")
        for flag in result.flags:
            lines.append(f"- **{flag.rule}**: {flag.message}")
        if result.ticker in commentary:
            lines.append("")
            lines.append(f"> {commentary[result.ticker]}")
        lines.append("")

    return "\n".join(lines)


def write_markdown_report(
    results: list[TickerResult],
    run_date: date,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    commentary: dict[str, str] | None = None,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"report-{run_date.isoformat()}.md"
    out_path.write_text(format_markdown(results, run_date, commentary), encoding="utf-8")
    return out_path
