DROP TABLE IF EXISTS clean_fx;

CREATE TABLE clean_fx AS
WITH ranked AS (
    SELECT
        UPPER(TRIM(ticker)) AS ticker,
        date(date)          AS price_date,
        close               AS rate,
        ROW_NUMBER() OVER (
            PARTITION BY UPPER(TRIM(ticker)), date(date)
            ORDER BY ingested_at DESC
        ) AS rn
    FROM raw_fx
    WHERE close IS NOT NULL
      AND close > 0
)
SELECT ticker, price_date, rate
FROM ranked
WHERE rn = 1;

CREATE UNIQUE INDEX idx_clean_fx_pk ON clean_fx (ticker, price_date);