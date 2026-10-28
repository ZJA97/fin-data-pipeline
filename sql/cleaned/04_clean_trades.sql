DROP TABLE IF EXISTS clean_trades;

CREATE TABLE clean_trades AS
WITH deduped AS (
    SELECT
        trade_id,
        date(trade_date)    AS trade_date,
        UPPER(TRIM(ticker)) AS ticker,
        UPPER(TRIM(side))   AS side,
        quantity,
        price,
        fee,
        ROW_NUMBER() OVER (
            PARTITION BY trade_id
            ORDER BY loaded_at DESC
        ) AS rn
    FROM raw_trades
)
SELECT
    d.trade_id,
    d.trade_date,
    d.ticker,
    d.side,
    d.quantity,
    CASE d.side WHEN 'BUY' THEN d.quantity ELSE -d.quantity END AS signed_quantity,
    d.price / s.price_divisor                AS price,        -- major units (pounds, not pence)
    d.fee   / s.price_divisor                AS fee,
    s.quote_currency                         AS currency,
    d.quantity * d.price / s.price_divisor   AS gross_amount
FROM deduped d
JOIN dim_security s ON s.ticker = d.ticker
WHERE d.rn = 1
  AND d.quantity > 0
  AND d.price > 0;

CREATE UNIQUE INDEX idx_clean_trades_pk ON clean_trades (trade_id);