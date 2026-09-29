"""Pulls daily OHLC price data and caches it locally so repeated runs don't re-download everything."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "prices.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_prices (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
        """
    )
    conn.commit()
    return conn


def _cached_range(conn: sqlite3.Connection, ticker: str) -> tuple[str | None, str | None]:
    row = conn.execute(
        "SELECT MIN(date), MAX(date) FROM daily_prices WHERE ticker = ?", (ticker,)
    ).fetchone()
    return (row[0], row[1]) if row else (None, None)


def _store(conn: sqlite3.Connection, ticker: str, df: pd.DataFrame) -> None:
    rows = [
        (ticker, idx.strftime("%Y-%m-%d"), r.Open, r.High, r.Low, r.Close, int(r.Volume))
        for idx, r in df.iterrows()
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO daily_prices (ticker, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def fetch_prices(
    tickers: list[str],
    lookback_days: int,
    db_path: Path = DEFAULT_DB_PATH,
    end_date: date | None = None,
) -> dict[str, pd.DataFrame]:
    """Return a dict of ticker -> OHLC DataFrame, pulling only what's missing from the cache.

    yfinance is only hit for tickers/date ranges that aren't already in the local
    SQLite cache, so a second run on the same day is fast and doesn't re-download
    history that hasn't changed.
    """
    end_date = end_date or date.today()
    start_date = end_date - timedelta(days=lookback_days)

    conn = _connect(db_path)
    result: dict[str, pd.DataFrame] = {}

    try:
        for ticker in tickers:
            cached_min, cached_max = _cached_range(conn, ticker)
            have_full_range = (
                cached_min is not None
                and cached_min <= start_date.strftime("%Y-%m-%d")
                and cached_max is not None
                and cached_max >= (end_date - timedelta(days=1)).strftime("%Y-%m-%d")
            )

            if not have_full_range:
                raw = yf.download(
                    ticker,
                    start=start_date.strftime("%Y-%m-%d"),
                    end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                    progress=False,
                    auto_adjust=False,
                )
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                if not raw.empty:
                    _store(conn, ticker, raw)

            df = pd.read_sql(
                "SELECT date, open, high, low, close, volume FROM daily_prices "
                "WHERE ticker = ? AND date >= ? ORDER BY date",
                conn,
                params=(ticker, start_date.strftime("%Y-%m-%d")),
            )
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df.columns = ["Open", "High", "Low", "Close", "Volume"]
            result[ticker] = df
    finally:
        conn.close()

    return result
