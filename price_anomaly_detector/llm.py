"""Optional one-sentence commentary per flagged ticker, using Claude or GPT.

Skipped entirely if no API key is set. This is meant to add a bit of plain-
English context on top of the rule engine's output, not to replace it or to
give investment advice.
"""

from __future__ import annotations

import os

from price_anomaly_detector.rules import TickerResult

COMMENTARY_PROMPT_TEMPLATE = (
    "A stock monitoring tool flagged {ticker} for the following reasons:\n"
    "{reasons}\n\n"
    "In one plain-English sentence, add context a smart friend who doesn't follow "
    "markets closely would find useful. Do not give investment advice or say "
    "whether to buy or sell. Just describe what this pattern typically means."
)


def _build_prompt(result: TickerResult) -> str:
    reasons = "\n".join(f"- {flag.message}" for flag in result.flags)
    return COMMENTARY_PROMPT_TEMPLATE.format(ticker=result.ticker, reasons=reasons)


def _call_anthropic(prompt: str, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _call_openai(prompt: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def generate_commentary(results: list[TickerResult]) -> dict[str, str]:
    """Return {ticker: sentence} for flagged tickers, or {} if no key is set."""
    fired = [r for r in results if r.fired]
    if not fired:
        return {}

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        print("No ANTHROPIC_API_KEY or OPENAI_API_KEY set, skipping LLM commentary.")
        return {}

    commentary: dict[str, str] = {}
    for result in fired:
        prompt = _build_prompt(result)
        try:
            if anthropic_key:
                commentary[result.ticker] = _call_anthropic(prompt, anthropic_key)
            else:
                commentary[result.ticker] = _call_openai(prompt, openai_key)
        except Exception as e:
            print(f"LLM commentary failed for {result.ticker}, skipping: {e}")

    return commentary
