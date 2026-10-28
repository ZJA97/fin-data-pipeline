DROP TABLE IF EXISTS daily_positions;

-- End-of-day holdings (including that day's trades) from first trade onwards
CREATE TABLE daily_positions AS
WITH first_trade AS (
    SELECT ticker, MIN(trade_date) AS first_date
    FROM fct_trades_gbp
    GROUP BY ticker
),
daily_net AS (
    SELECT ticker, trade_date, SUM(signed_quantity) AS net_qty
    FROM fct_trades_gbp
    GROUP BY ticker, trade_date
),
grid AS (
    SELECT f.ticker, d.date
    FROM first_trade f
    JOIN dim_date d ON d.date >= f.first_date
)
SELECT
    g.ticker,
    g.date,
    SUM(COALESCE(n.net_qty, 0)) OVER (
        PARTITION BY g.ticker
        ORDER BY g.date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS quantity
FROM grid g
LEFT JOIN daily_net n
  ON n.ticker = g.ticker AND n.trade_date = g.date;

CREATE UNIQUE INDEX idx_daily_positions_pk ON daily_positions (ticker, date);