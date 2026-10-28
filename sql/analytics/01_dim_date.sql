DROP TABLE IF EXISTS dim_date;

-- Calendar = every day at least one of our markets traded
CREATE TABLE dim_date AS
SELECT DISTINCT price_date AS date
FROM clean_prices
ORDER BY price_date;

CREATE UNIQUE INDEX idx_dim_date_pk ON dim_date (date);