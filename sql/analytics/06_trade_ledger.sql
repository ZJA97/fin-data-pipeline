DROP TABLE IF EXISTS trade_ledger;
DROP TABLE IF EXISTS trade_seq;

-- Number each ticker's trades in order (trade_id breaks same-day ties)
CREATE TEMP TABLE trade_seq AS
SELECT
    trade_id, ticker, trade_date, side, quantity, gross_gbp, fee_gbp,
    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trade_date, trade_id) AS n
FROM fct_trades_gbp;

CREATE INDEX idx_trade_seq ON trade_seq (ticker, n);

-- Walk each ticker's trades in order, carrying quantity and cost basis forward
CREATE TABLE trade_ledger AS
WITH RECURSIVE ledger (
    trade_id, ticker, trade_date, n, side, quantity, qty_after, cost_after, realised_pnl
) AS (
    -- Anchor: first trade per ticker (always a BUY, since there are no shorts)
    SELECT trade_id, ticker, trade_date, n, side, quantity,
           quantity,
           gross_gbp + fee_gbp,
           0.0
    FROM trade_seq
    WHERE n = 1

    UNION ALL

    -- Step: apply trade n+1 to the state after trade n
    SELECT
        s.trade_id, s.ticker, s.trade_date, s.n, s.side, s.quantity,
        CASE s.side WHEN 'BUY' THEN l.qty_after + s.quantity
                    ELSE l.qty_after - s.quantity END,
        CASE s.side WHEN 'BUY' THEN l.cost_after + s.gross_gbp + s.fee_gbp
                    ELSE l.cost_after - l.cost_after * s.quantity / l.qty_after END,
        CASE s.side WHEN 'BUY' THEN 0.0
                    ELSE (s.gross_gbp - s.fee_gbp) - l.cost_after * s.quantity / l.qty_after END
    FROM ledger l
    JOIN trade_seq s ON s.ticker = l.ticker AND s.n = l.n + 1
)
SELECT
    trade_id, ticker, trade_date, n, side, quantity,
    qty_after, cost_after, realised_pnl,
    SUM(realised_pnl) OVER (
        PARTITION BY ticker ORDER BY n
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cum_realised_pnl
FROM ledger;

CREATE UNIQUE INDEX idx_trade_ledger_pk ON trade_ledger (trade_id);
CREATE UNIQUE INDEX idx_trade_ledger_seq ON trade_ledger (ticker, n);