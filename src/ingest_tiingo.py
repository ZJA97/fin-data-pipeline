"""Fetch daily prices from Tiingo into raw_prices (source='tiingo')."""
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import requests

DB_PATH = "data/pipeline.db"
BASE_URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest_tiingo")


def is_supported(ticker):
    # Tiingo covers US securities: skip UK (.L), indices (^), FX/futures (=), crypto
    return not any(ch in ticker for ch in ".^=") and not ticker.endswith("-USD")


def fetch(ticker, start, end, token):
    resp = requests.get(
        BASE_URL.format(ticker=ticker.lower()),
        params={"startDate": start, "endDate": end, "format": "json"},
        headers={"Authorization": f"Token {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError("no rows returned")
    return data


def main():
    token = os.environ.get("TIINGO_API_KEY")
    if not token:
        sys.exit("Set TIINGO_API_KEY first")

    failures = 0
    with sqlite3.connect(DB_PATH) as conn:
        tickers = [r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM raw_prices WHERE source = 'yfinance' ORDER BY ticker")]
        start, end = conn.execute(
            "SELECT MIN(date), MAX(date) FROM raw_prices WHERE source = 'yfinance'").fetchone()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        for ticker in tickers:
            if not is_supported(ticker):
                log.warning("%s: not covered by Tiingo, skipped", ticker)
                continue
            try:
                data = fetch(ticker, start, end, token)
                rows = [(ticker, d["date"][:10], d["open"], d["high"], d["low"], d["close"],
                         d["adjClose"], d["volume"], "tiingo", now) for d in data]
                with conn:  # one transaction per ticker, so re-runs are safe
                    conn.execute("DELETE FROM raw_prices WHERE source = 'tiingo' AND ticker = ?", (ticker,))
                    conn.executemany(
                        "INSERT INTO raw_prices (ticker, date, open, high, low, close, adj_close, "
                        "volume, source, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
                log.info("%s: %d rows", ticker, len(rows))
            except Exception as exc:
                log.error("%s: %s", ticker, exc)
                failures += 1
            time.sleep(1)

    log.info("done, %d failures", failures)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()