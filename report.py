import sqlite3

conn = sqlite3.connect("data/pipeline.db")


def q(sql, *params):
    return conn.execute(sql, params).fetchall()


n_trades, first, last = q("SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM clean_trades")[0]
n_secs = q("SELECT COUNT(DISTINCT ticker) FROM clean_trades")[0][0]
date, mv, cost, unreal, real, total, held = q(
    """SELECT date, market_value_gbp, cost_basis_gbp, unrealised_pnl_gbp,
              realised_pnl_cum_gbp, total_pnl_gbp, positions_held
       FROM portfolio_daily ORDER BY date DESC LIMIT 1"""
)[0]

print("Paste into the README 'Result' section:\n")
print(
    f"{n_trades} trades across {n_secs} securities, {first} to {last}. "
    f"On {date}: portfolio value £{mv:,.0f} on cost basis £{cost:,.0f}; "
    f"realised P&L £{real:,.0f}, unrealised £{unreal:,.0f}, total £{total:,.0f}."
)

print(f"\nPositions held: {held}")
print("\nTop 5 holdings by weight:")
for ticker, value, weight, u in q(
    """SELECT ticker, ROUND(market_value_gbp), 
              ROUND(100.0 * market_value_gbp / (SELECT SUM(market_value_gbp) FROM daily_valuation WHERE date = ?), 1),
              ROUND(unrealised_pnl_gbp)
       FROM daily_valuation WHERE date = ?
       ORDER BY market_value_gbp DESC LIMIT 5""",
    date, date,
):
    print(f"  {ticker:8} £{value:>10,.0f}  {weight:>5}%  unrealised £{u:,.0f}")

print("\nSame-day trades in one security (why ledger_eod has fewer rows than trade_ledger):")
for r in q("SELECT ticker, trade_date, COUNT(*) FROM trade_ledger GROUP BY ticker, trade_date HAVING COUNT(*) > 1"):
    print(" ", r)

cols = [r[1] for r in q("PRAGMA table_info(dim_security)")]
print("\ndim_security has an is_index column:", "is_index" in cols)