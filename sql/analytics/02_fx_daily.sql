DROP TABLE IF EXISTS fx_daily;

-- fx_daily.to_gbp = multiply a local-currency amount by this to get GBP
CREATE TABLE fx_daily AS
WITH gbp AS (
    SELECT date, 'GBP' AS currency, 1.0 AS to_gbp
    FROM dim_date
),
usd AS (
    SELECT
        d.date,
        'USD' AS currency,
        -- GBPUSD=X is USD per 1 GBP, so USD -> GBP is the reciprocal
        1.0 / (
            SELECT f.rate
            FROM clean_fx f
            WHERE f.ticker = 'GBPUSD=X' AND f.price_date <= d.date
            ORDER BY f.price_date DESC
            LIMIT 1
        ) AS to_gbp
    FROM dim_date d
),
eur AS (
    SELECT
        d.date,
        'EUR' AS currency,
        -- EURGBP=X is GBP per 1 EUR, so it's already the multiplier
        (
            SELECT f.rate
            FROM clean_fx f
            WHERE f.ticker = 'EURGBP=X' AND f.price_date <= d.date
            ORDER BY f.price_date DESC
            LIMIT 1
        ) AS to_gbp
    FROM dim_date d
)
SELECT * FROM gbp
UNION ALL SELECT * FROM usd WHERE to_gbp IS NOT NULL
UNION ALL SELECT * FROM eur WHERE to_gbp IS NOT NULL;

CREATE UNIQUE INDEX idx_fx_daily_pk ON fx_daily (date, currency);