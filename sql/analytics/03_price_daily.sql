DROP TABLE IF EXISTS price_daily;

-- One row per security per calendar day, forward-filled, in major currency units
CREATE TABLE price_daily AS
WITH grid AS (
    SELECT s.ticker, s.quote_currency AS currency, s.price_divisor, d.date
    FROM dim_security s
    CROSS JOIN dim_date d
),
filled AS (
    SELECT
        g.ticker, g.currency, g.price_divisor, g.date,
        -- Latest date up to today on which this ticker actually has a price
        -- (MAX ignores the NULLs on days with no price)
        MAX(p.price_date) OVER (
            PARTITION BY g.ticker
            ORDER BY g.date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS source_date
    FROM grid g
    LEFT JOIN clean_prices p
      ON p.ticker = g.ticker AND p.price_date = g.date
)
SELECT
    f.ticker,
    f.date,
    f.currency,
    f.source_date,
    p.close / f.price_divisor AS close_price,
    CASE WHEN f.source_date < f.date THEN 1 ELSE 0 END AS is_stale
FROM filled f
JOIN clean_prices p
  ON p.ticker = f.ticker AND p.price_date = f.source_date;

CREATE UNIQUE INDEX idx_price_daily_pk ON price_daily (ticker, date);