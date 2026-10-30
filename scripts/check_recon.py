import sqlite3
import pandas as pd

conn = sqlite3.connect("data/pipeline.db")
df = pd.read_sql("SELECT * FROM recon_breaks", conn)

print("raw rows:", len(df), "| distinct ticker/date:", len(df.drop_duplicates(["ticker", "price_date"])))
print(df.groupby("ticker").size())
print(df[["pct_diff", "tolerance_pct", "warn_pct"]].describe().to_string())
print("date range:", df["price_date"].min(), "to", df["price_date"].max())
print(df.sort_values("price_date").head(5).to_string(index=False))