"""Portfolio-level performance and risk metrics for the dashboard."""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

DB_PATH = Path("data/pipeline.db")
OUT_TABLE = "analytics_portfolio_metrics"
TRADING_DAYS = 252
VOL_WINDOW = 30


def compute_metrics(pf: pd.DataFrame) -> pd.DataFrame:
    """pf needs: date, market_value_gbp, total_pnl_gbp, daily_pnl_gbp."""
    df = (
        pf.sort_values("date")
        .set_index("date")[["market_value_gbp", "total_pnl_gbp", "daily_pnl_gbp"]]
        .copy()
    )
    prev_value = df["market_value_gbp"].shift(1)

    # P&L over yesterday's value, so buying more never counts as a return
    df["daily_return"] = df["daily_pnl_gbp"] / prev_value.where(prev_value > 0)

    growth = (1 + df["daily_return"].fillna(0)).cumprod()
    df["cumulative_return"] = growth - 1
    df["rolling_vol_30d"] = df["daily_return"].rolling(VOL_WINDOW).std() * np.sqrt(TRADING_DAYS)
    df["drawdown"] = growth / growth.cummax() - 1
    return df


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        pf = pd.read_sql(
            "SELECT date, market_value_gbp, total_pnl_gbp, daily_pnl_gbp FROM portfolio_daily",
            conn, parse_dates=["date"],
        )

        # sanity check: daily P&L should equal the day-on-day change in total P&L
        gap = (pf.sort_values("date")["total_pnl_gbp"].diff() - pf.sort_values("date")["daily_pnl_gbp"]).abs().max()
        if gap > 0.01:
            print(f"WARNING: daily_pnl_gbp differs from change in total_pnl_gbp by up to {gap:.2f}")

        out = compute_metrics(pf).reset_index()
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out.to_sql(OUT_TABLE, conn, if_exists="replace", index=False)

    print(f"Wrote {len(out)} rows to {OUT_TABLE}")
    print(f"Largest daily move: {out['daily_return'].abs().max():.2%}")


if __name__ == "__main__":
    main()