DROP TABLE IF EXISTS clean_prices;

CREATE TABLE clean_prices AS
WITH ranked AS (
    SELECT
        UPPER(TRIM(ticker)) AS ticker,
        date(date)          AS price_date,
        open, high, low, close, adj_close, volume,
        ROW_NUMBER() OVER (
            PARTITION BY UPPER(TRIM(ticker)), date(date)
            ORDER BY ingested_at DESC
        ) AS rn
    FROM raw_prices
    WHERE source = 'yfinance'
      AND close IS NOT NULL
      AND close > 0
)
SELECT ticker, price_date, open, high, low, close, adj_close, volume
FROM ranked
WHERE rn = 1;

CREATE UNIQUE INDEX idx_clean_prices_pk ON clean_prices (ticker, price_date);