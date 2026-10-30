import sqlite3

import pandas as pd

conn = sqlite3.connect("data/pipeline.db")
df = pd.read_sql(
    "SELECT date, market_value_gbp, daily_pnl_gbp, daily_return "
    "FROM analytics_portfolio_metrics",
    conn,
)

print("Largest absolute daily returns:")
top = df.reindex(df["daily_return"].abs().sort_values(ascending=False).index).head(8)
print(top.to_string(index=False))

print("\nFirst rows with a return:")
print(df.dropna(subset=["daily_return"]).head(5).to_string(index=False))