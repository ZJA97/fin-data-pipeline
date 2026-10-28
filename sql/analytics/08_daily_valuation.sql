DROP TABLE IF EXISTS daily_valuation;

CREATE TABLE daily_valuation AS
SELECT
    p.ticker,
    p.date,
    p.quantity,
    pr.currency,
    pr.close_price,
    pr.is_stale,
    fx.to_gbp                                              AS fx_to_gbp,
    p.quantity * pr.close_price * fx.to_gbp                AS market_value_gbp,
    e.cost_basis_gbp,
    p.quantity * pr.close_price * fx.to_gbp - e.cost_basis_gbp AS unrealised_pnl_gbp,
    e.realised_pnl_cum_gbp,
    p.quantity * pr.close_price * fx.to_gbp - e.cost_basis_gbp
        + e.realised_pnl_cum_gbp                           AS total_pnl_gbp
FROM daily_positions p
JOIN price_daily pr ON pr.ticker = p.ticker AND pr.date = p.date
JOIN fx_daily    fx ON fx.date = p.date AND fx.currency = pr.currency
JOIN ledger_eod  e  ON e.ticker = p.ticker
                   AND e.date = (
                       SELECT MAX(x.date) FROM ledger_eod x
                       WHERE x.ticker = p.ticker AND x.date <= p.date
                   );

CREATE UNIQUE INDEX idx_daily_valuation_pk ON daily_valuation (ticker, date);