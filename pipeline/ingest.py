"""Fetch daily prices/FX from Yahoo Finance (via yfinance) and load them into raw tables."""
from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from .db import COLUMNS, insert_rows, latest_dates

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
COLUMN_MAP = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}


class FetchError(Exception):
    """Raised when a symbol could not be fetched after all retries."""


@dataclass
class IngestResult:
    symbol: str
    rows: int = 0
    error: str | None = None


def normalise(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Turn a yfinance frame into the raw-table shape. Values are otherwise left untouched."""
    if raw is None or raw.empty:
        return pd.DataFrame(columns=COLUMNS)

    idx = pd.DatetimeIndex(raw.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)  # keep the exchange's own calendar date

    out = raw.rename(columns=COLUMN_MAP).reindex(columns=list(COLUMN_MAP.values()))
    out.insert(0, "date", idx.strftime("%Y-%m-%d"))
    out.insert(0, "ticker", symbol)
    return out.reset_index(drop=True)[COLUMNS]


def fetch_history(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Fetch daily bars for one symbol in [start, end). Retries with backoff; may return empty."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = yf.Ticker(symbol).history(
                start=start.isoformat(), end=end.isoformat(), auto_adjust=False, actions=False
            )
            return normalise(raw, symbol)
        except Exception as exc:  # yfinance raises a variety of network/parsing errors
            last_error = exc
            log.warning("%s: attempt %d/%d failed: %s", symbol, attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(2**attempt)
    raise FetchError(f"{symbol}: gave up after {MAX_ATTEMPTS} attempts ({last_error})") from last_error


def ingest_symbols(
    conn: sqlite3.Connection, table: str, symbols: list[str], default_start: str, end: date
) -> list[IngestResult]:
    """Incrementally load each symbol into `table`. One bad symbol never stops the others.

    `end` is exclusive and should be today, so only completed trading days are stored.
    """
    latest = latest_dates(conn, table)
    results: list[IngestResult] = []

    for symbol in symbols:
        result = IngestResult(symbol)
        results.append(result)
        last = latest.get(symbol)
        start = date.fromisoformat(last) + timedelta(days=1) if last else date.fromisoformat(default_start)

        if start >= end:
            log.info("%s: already up to date (latest %s)", symbol, last)
            continue

        try:
            df = fetch_history(symbol, start, end)

            if last:  # never re-insert days we already hold
                df = df[df["date"] > last]

            # Reject rows without valid closing prices before inserting.
            if not df.empty:
                price_columns = ["open", "high", "low", "close", "adj_close"]
                df = df.copy()

                for column in price_columns:
                    df[column] = pd.to_numeric(df[column], errors="coerce")

                valid_prices = (
                    df[price_columns].notna().all(axis=1)
                    & (df[price_columns] > 0).all(axis=1)
                )

                rejected = int((~valid_prices).sum())
                if rejected:
                    log.warning(
                        "%s: rejected %d rows with missing or non-positive prices",
                        symbol,
                        rejected,
                    )

                df = df.loc[valid_prices].copy()

            result.rows = insert_rows(conn, table, df)










            
        except FetchError as exc:
            result.error = str(exc)
            log.error(str(exc))
            continue
        except sqlite3.Error as exc:
            result.error = f"{symbol}: database error: {exc}"
            log.error(result.error)
            continue

        if result.rows:
            log.info("%s: loaded %d rows (%s to %s)", symbol, result.rows, df["date"].min(), df["date"].max())
        elif last:
            log.info("%s: no new rows since %s", symbol, last)
        else:
            log.warning("%s: no data returned - is the ticker valid?", symbol)

    return results
