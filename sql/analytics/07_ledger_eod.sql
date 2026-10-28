DROP TABLE IF EXISTS ledger_eod;

-- Last ledger state on each day a ticker traded
CREATE TABLE ledger_eod AS
WITH ranked AS (
    SELECT
        ticker, trade_date AS date, qty_after, cost_after, cum_realised_pnl,
        ROW_NUMBER() OVER (PARTITION BY ticker, trade_date ORDER BY n DESC) AS rn
    FROM trade_ledger
)
SELECT
    ticker, date, qty_after,
    cost_after       AS cost_basis_gbp,
    cum_realised_pnl AS realised_pnl_cum_gbp
FROM ranked
WHERE rn = 1;

CREATE UNIQUE INDEX idx_ledger_eod_pk ON ledger_eod (ticker, date);