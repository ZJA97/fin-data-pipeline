import sqlite3

import yfinance as yf

conn = sqlite3.connect("data/pipeline.db")
tickers = [r[0] for r in conn.execute(
    "SELECT ticker FROM dim_security WHERE ticker LIKE '%.L' ORDER BY ticker")]

for t in tickers:
    try:
        cur = yf.Ticker(t).fast_info["currency"]
    except Exception as e:
        cur = f"lookup failed ({e})"
    print(f"{t:10} {cur}")