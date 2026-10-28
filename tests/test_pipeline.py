import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "pipeline.db"

# Each query counts violations. Zero rows violating = test passes.
INVARIANTS = {
    "no_trades_lost_in_cleaning":
        "SELECT (SELECT COUNT(DISTINCT trade_id) FROM raw_trades) - (SELECT COUNT(*) FROM clean_trades)",
    "no_trades_lost_in_gbp_conversion":
        "SELECT (SELECT COUNT(*) FROM clean_trades) - (SELECT COUNT(*) FROM fct_trades_gbp)",
    "no_index_tickers_traded":
        "SELECT COUNT(*) FROM clean_trades WHERE ticker LIKE '^%'",
    "trade_dates_exist_in_calendar":
        "SELECT COUNT(*) FROM clean_trades WHERE trade_date NOT IN (SELECT date FROM dim_date)",
    "no_short_positions":
        "SELECT COUNT(*) FROM daily_positions WHERE quantity < 0",
    "final_positions_match_trade_ledger":
        """SELECT COUNT(*) FROM (
               SELECT ticker, SUM(signed_quantity) AS q FROM clean_trades GROUP BY ticker
           ) t
           LEFT JOIN daily_positions p
             ON p.ticker = t.ticker AND p.date = (SELECT MAX(date) FROM dim_date)
           WHERE p.quantity IS NULL OR p.quantity <> t.q""",
    "every_position_has_a_price":
        """SELECT COUNT(*) FROM daily_positions p
           LEFT JOIN price_daily pr ON pr.ticker = p.ticker AND pr.date = p.date
           WHERE pr.close_price IS NULL""",
    "every_position_has_an_fx_rate":
        """SELECT COUNT(*) FROM daily_positions p
           JOIN dim_security s ON s.ticker = p.ticker
           LEFT JOIN fx_daily fx ON fx.date = p.date AND fx.currency = s.quote_currency
           WHERE fx.to_gbp IS NULL""",
    "valuation_covers_every_position_row":
        "SELECT (SELECT COUNT(*) FROM daily_positions) - (SELECT COUNT(*) FROM daily_valuation)",
    "ledger_quantity_matches_positions":
        """SELECT COUNT(*) FROM daily_valuation v
           JOIN ledger_eod e ON e.ticker = v.ticker
            AND e.date = (SELECT MAX(x.date) FROM ledger_eod x
                          WHERE x.ticker = v.ticker AND x.date <= v.date)
           WHERE e.qty_after <> v.quantity""",
    "zero_holding_means_zero_cost_basis":
        "SELECT COUNT(*) FROM daily_valuation WHERE quantity = 0 AND ABS(cost_basis_gbp) > 0.01",
    "no_null_valuations":
        "SELECT COUNT(*) FROM daily_valuation WHERE market_value_gbp IS NULL OR unrealised_pnl_gbp IS NULL",
    "cash_flows_reconcile_to_pnl":
        """SELECT COUNT(*) FROM (
               SELECT ticker,
                      SUM(CASE WHEN side = 'SELL' THEN gross_gbp - fee_gbp
                               ELSE -(gross_gbp + fee_gbp) END) AS net_cash
               FROM fct_trades_gbp GROUP BY ticker
           ) c
           JOIN ledger_eod e ON e.ticker = c.ticker
            AND e.date = (SELECT MAX(date) FROM ledger_eod x WHERE x.ticker = c.ticker)
           WHERE ABS((e.realised_pnl_cum_gbp - e.cost_basis_gbp) - c.net_cash) > 0.01""",
}


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(DB_PATH)
    yield c
    c.close()


@pytest.mark.parametrize("name", INVARIANTS)
def test_invariant(conn, name):
    violations = conn.execute(INVARIANTS[name]).fetchone()[0]
    assert violations == 0, f"{name}: {violations} violation(s)"


def test_average_cost_ledger_known_example():
    """Hand-computed example, run through the real ledger SQL in a throwaway database.

    T1 BUY 10  cost 1,000 + 10 fee            -> qty 10, cost 1,010
    T2 BUY 10  cost 1,200 + 10 fee            -> qty 20, cost 2,220
    T3 SELL 5  proceeds 700 - 5 fee = 695
               cost removed 2,220 * 5/20 = 555 -> realised 140, qty 15, cost 1,665
    T4 SELL 15 proceeds 2,000
               cost removed 1,665              -> realised 335, qty 0, cost 0
    """
    mem = sqlite3.connect(":memory:")
    mem.execute(
        """CREATE TABLE fct_trades_gbp (
               trade_id TEXT, ticker TEXT, trade_date TEXT, side TEXT,
               quantity INTEGER, gross_gbp REAL, fee_gbp REAL)"""
    )
    mem.executemany(
        "INSERT INTO fct_trades_gbp VALUES (?,?,?,?,?,?,?)",
        [
            ("T1", "XYZ", "2024-01-02", "BUY", 10, 1000.0, 10.0),
            ("T2", "XYZ", "2024-01-03", "BUY", 10, 1200.0, 10.0),
            ("T3", "XYZ", "2024-01-04", "SELL", 5, 700.0, 5.0),
            ("T4", "XYZ", "2024-01-05", "SELL", 15, 2000.0, 0.0),
        ],
    )
    mem.executescript((ROOT / "sql" / "analytics" / "06_trade_ledger.sql").read_text(encoding="utf-8"))

    rows = mem.execute(
        "SELECT trade_id, qty_after, cost_after, realised_pnl FROM trade_ledger ORDER BY n"
    ).fetchall()

    assert [r[0] for r in rows] == ["T1", "T2", "T3", "T4"]
    assert [r[1] for r in rows] == [10, 20, 15, 0]
    assert [r[2] for r in rows] == pytest.approx([1010.0, 2220.0, 1665.0, 0.0])
    assert [r[3] for r in rows] == pytest.approx([0.0, 0.0, 140.0, 335.0])