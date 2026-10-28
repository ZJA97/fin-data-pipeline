DROP TABLE IF EXISTS portfolio_daily;

CREATE TABLE portfolio_daily AS
WITH totals AS (
    SELECT
        date,
        SUM(market_value_gbp)      AS market_value_gbp,
        SUM(cost_basis_gbp)        AS cost_basis_gbp,
        SUM(unrealised_pnl_gbp)    AS unrealised_pnl_gbp,
        SUM(realised_pnl_cum_gbp)  AS realised_pnl_cum_gbp,
        SUM(total_pnl_gbp)         AS total_pnl_gbp,
        COUNT(CASE WHEN quantity > 0 THEN 1 END) AS positions_held
    FROM daily_valuation
    GROUP BY date
)
SELECT
    *,
    total_pnl_gbp - LAG(total_pnl_gbp) OVER (ORDER BY date) AS daily_pnl_gbp
FROM totals;

CREATE UNIQUE INDEX idx_portfolio_daily_pk ON portfolio_daily (date);