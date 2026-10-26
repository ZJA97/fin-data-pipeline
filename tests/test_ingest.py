from datetime import date
import sqlite3

import pandas as pd

from pipeline import ingest
from pipeline.db import init_db


def test_ingestion_rejects_rows_with_missing_prices(monkeypatch):
    conn = sqlite3.connect(":memory:")
    init_db(conn)

    # Simulate Yahoo Finance returning one good row and one bad row.
    fake_data = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "date": "2024-01-02",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "adj_close": 100.5,
                "volume": 1000,
            },
            {
                "ticker": "AAA",
                "date": "2024-01-03",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": None,
                "adj_close": None,
                "volume": 1000,
            },
        ]
    )

    def fake_fetch_history(symbol, start, end):
        return fake_data.copy()

    monkeypatch.setattr(ingest, "fetch_history", fake_fetch_history)

    results = ingest.ingest_symbols(
        conn,
        "raw_prices",
        ["AAA"],
        "2024-01-01",
        date(2024, 1, 4),
    )

    # Only the valid row should be inserted.
    assert results[0].rows == 1

    saved_rows = conn.execute(
        "SELECT ticker, date, close, adj_close FROM raw_prices"
    ).fetchall()

    assert saved_rows == [("AAA", "2024-01-02", 100.5, 100.5)]

    conn.close()