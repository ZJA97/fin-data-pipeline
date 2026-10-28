DROP TABLE IF EXISTS fct_trades_gbp;

-- Each trade converted to GBP at the FX rate on its trade date
CREATE TABLE fct_trades_gbp AS
SELECT
    t.trade_id,
    t.trade_date,
    t.ticker,
    t.side,
    t.quantity,
    t.signed_quantity,
    t.currency,
    t.price,
    t.fee,
    fx.to_gbp                  AS fx_to_gbp,
    t.gross_amount * fx.to_gbp AS gross_gbp,
    t.fee * fx.to_gbp          AS fee_gbp
FROM clean_trades t
JOIN fx_daily fx
  ON fx.date = t.trade_date AND fx.currency = t.currency;

CREATE UNIQUE INDEX idx_fct_trades_gbp_pk ON fct_trades_gbp (trade_id);