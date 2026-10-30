"""Export dashboard tables from SQLite to CSV for Power BI."""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/pipeline.db")
OUT_DIR = Path("powerbi/data")
SECTORS_PATH = Path("config/sectors.csv")

QUERIES = {
    "dim_date": "SELECT date FROM dim_date ORDER BY date",
    "portfolio_metrics": "SELECT * FROM analytics_portfolio_metrics ORDER BY date",
    "positions_daily": """
        SELECT date, ticker, currency, quantity, market_value_gbp,
               unrealised_pnl_gbp, is_stale
        FROM daily_valuation
        WHERE quantity <> 0
    """,
    # latest row per ticker and date, so repeated daily runs don't double count
    "reconciliation_breaks": """
        SELECT run_ts, ticker, price_date, close_a, close_b, abs_diff, pct_diff,
               tolerance_pct, warn_pct, status
        FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY ticker, price_date ORDER BY run_ts DESC) AS rn
            FROM recon_breaks
        )
        WHERE rn = 1
    """,
    "dq_results": """
        SELECT run_ts, source, "check", ticker, price_date, detail
        FROM dq_results
    """,
}


def add_sectors(positions: pd.DataFrame) -> pd.DataFrame:
    sectors = pd.read_csv(SECTORS_PATH)[["ticker", "sector"]]
    out = positions.merge(sectors, on="ticker", how="left")
    out["sector"] = out["sector"].fillna("Unclassified")
    missing = sorted(out.loc[out["sector"] == "Unclassified", "ticker"].unique())
    if missing:
        print(f"WARNING: no sector for {missing}")
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        for name, sql in QUERIES.items():
            df = pd.read_sql(sql, conn)
            if name == "positions_daily":
                df = add_sectors(df)
            df.to_csv(OUT_DIR / f"{name}.csv", index=False)
            print(f"{name}: {len(df)} rows")
            if name == "reconciliation_breaks" and len(df):
                print(df["status"].value_counts().to_string())


if __name__ == "__main__":
    main()