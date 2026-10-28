import sqlite3

c = sqlite3.connect("data/pipeline_test.db")
c.execute("UPDATE raw_prices SET adj_close = adj_close * 1.05 "
          "WHERE source = 'yfinance' AND ticker = 'AAPL' AND date = '2024-03-15'")
c.commit()
print("rows changed:", c.total_changes)