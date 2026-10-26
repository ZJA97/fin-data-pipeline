"""SQLite helpers for the raw layer."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAW_TABLES = ("raw_prices", "raw_fx")

COLUMNS = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS {table} (
    ticker      TEXT NOT NULL,
    date        TEXT NOT NULL,   -- ISO date, YYYY-MM-DD
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    adj_close   REAL,
    volume      INTEGER,
    source      TEXT NOT NULL,
    ingested_at TEXT NOT NULL    -- UTC timestamp of the load
);
CREATE INDEX IF NOT EXISTS idx_{table}_ticker_date ON {table} (ticker, date);
"""


def get_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def init_db(conn: sqlite3.Connection) -> None:
    for table in RAW_TABLES:
        conn.executescript(_SCHEMA.format(table=table))
    conn.commit()


def latest_dates(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    """Most recent date already stored per ticker (used for incremental loads)."""
    rows = conn.execute(f"SELECT ticker, MAX(date) FROM {table} GROUP BY ticker").fetchall()
    return {ticker: last for ticker, last in rows}


def insert_rows(conn: sqlite3.Connection, table: str, df: pd.DataFrame, source: str = "yfinance") -> int:
    """Append a normalised frame to a raw table. Returns the number of rows written."""
    if df.empty:
        return 0
    loaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    clean = df[COLUMNS].astype(object).where(df[COLUMNS].notna(), None)
    records = [(*row, source, loaded_at) for row in clean.itertuples(index=False, name=None)]
    with conn:  # commits on success, rolls back on error
        conn.executemany(
            f"INSERT INTO {table} ({', '.join(COLUMNS)}, source, ingested_at) "
            f"VALUES ({', '.join('?' * (len(COLUMNS) + 2))})",
            records,
        )
    return len(records)
