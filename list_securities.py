import sqlite3

conn = sqlite3.connect("data/pipeline.db")
for r in conn.execute("SELECT ticker, quote_currency, price_divisor FROM dim_security ORDER BY ticker"):
    print(r)