import sqlite3

conn = sqlite3.connect("data/pipeline.db")
queries = {
    "FX series": "SELECT ticker, MIN(price_date), MAX(price_date), COUNT(*) FROM clean_fx GROUP BY ticker",
    "Securities by currency": "SELECT quote_currency, COUNT(*) FROM dim_security GROUP BY quote_currency",
    "Price date range": "SELECT MIN(price_date), MAX(price_date), COUNT(DISTINCT ticker) FROM clean_prices",
    "Trades: raw unique vs clean": "SELECT (SELECT COUNT(DISTINCT trade_id) FROM raw_trades), (SELECT COUNT(*) FROM clean_trades)",
}
for title, q in queries.items():
    print(f"\n{title}")
    for row in conn.execute(q):
        print(row)