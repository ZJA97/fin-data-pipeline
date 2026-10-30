"""Compute every figure for the daily summary. No LLM involved here."""
import sqlite3

# If a table or column name differs in your DB, fix it here and nowhere else.
SQL_LATEST = "SELECT MAX(date) FROM portfolio_daily"
SQL_PREV = "SELECT MAX(date) FROM portfolio_daily WHERE date < ?"
SQL_DAY = """
    SELECT market_value_gbp, total_pnl_gbp, daily_pnl_gbp, positions_held
    FROM portfolio_daily WHERE date = ?
"""
SQL_PREV_VALUE = "SELECT market_value_gbp FROM portfolio_daily WHERE date = ?"
SQL_MOVERS = """
    SELECT t.ticker, t.total_pnl_gbp - y.total_pnl_gbp AS day_pnl
    FROM daily_valuation t
    JOIN daily_valuation y ON y.ticker = t.ticker AND y.date = ?
    WHERE t.date = ?
    ORDER BY day_pnl {order} LIMIT 3
"""
SQL_STALE = """
    SELECT COUNT(*) FROM daily_valuation
    WHERE date = ? AND quantity > 0 AND is_stale = 1
"""
SQL_RECON = """
    SELECT status, COUNT(*) FROM recon_breaks
    WHERE run_ts = (SELECT MAX(run_ts) FROM recon_breaks)
    GROUP BY status
"""
SQL_DQ = """
    SELECT "check", COUNT(*) FROM dq_results
    WHERE run_ts = (SELECT MAX(run_ts) FROM dq_results)
    GROUP BY "check" ORDER BY 2 DESC
"""


def gbp(x: float) -> str:
    return f"{'-' if x < 0 else ''}£{abs(x):,.0f}"


def pct(x: float) -> str:
    return f"{x:+.2f}%"


def build_facts(conn: sqlite3.Connection, as_of: str | None = None) -> dict:
    as_of = as_of or conn.execute(SQL_LATEST).fetchone()[0]
    mv, total_pnl, day_pnl, held = conn.execute(SQL_DAY, (as_of,)).fetchone()
    prev = conn.execute(SQL_PREV, (as_of,)).fetchone()[0]

    day_pnl_pct = None
    top_gainers, top_losers = [], []
    if prev:
        prev_mv = conn.execute(SQL_PREV_VALUE, (prev,)).fetchone()[0]
        if day_pnl is not None and prev_mv:
            day_pnl_pct = pct(day_pnl / prev_mv * 100)
        for order, bucket in (("DESC", top_gainers), ("ASC", top_losers)):
            for ticker, p in conn.execute(SQL_MOVERS.format(order=order), (prev, as_of)):
                bucket.append({"ticker": ticker, "pnl": gbp(p)})

    return {
        "date": as_of,
        "market_value": gbp(mv),
        "day_pnl": gbp(day_pnl) if day_pnl is not None else None,
        "day_pnl_pct": day_pnl_pct,
        "total_pnl": gbp(total_pnl),
        "positions_held": held,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "stale_prices": conn.execute(SQL_STALE, (as_of,)).fetchone()[0],
        "recon_by_status": dict(conn.execute(SQL_RECON).fetchall()),
        "dq_issues_by_check": dict(conn.execute(SQL_DQ).fetchall()),
    }