DROP TABLE IF EXISTS dim_security;

CREATE TABLE dim_security AS
SELECT DISTINCT
    ticker,
    CASE WHEN ticker LIKE '^%' THEN 1 ELSE 0 END AS is_index,
    CASE
        WHEN ticker LIKE '%.L' THEN 'GBP'
        WHEN ticker LIKE '%.DE' OR ticker LIKE '%.PA'
          OR ticker LIKE '%.AS' OR ticker LIKE '%.MI' THEN 'EUR'
        ELSE 'USD'
    END AS quote_currency,
    CASE WHEN ticker LIKE '%.L' AND ticker NOT IN ('VWRL.L') THEN 100.0 ELSE 1.0 END AS price_divisor
FROM clean_prices;

CREATE UNIQUE INDEX idx_dim_security_pk ON dim_security (ticker);