"""Generate synthetic trades and load them into raw_trades (SQLite)."""
import random
import sqlite3
from datetime import datetime, timezone

import pandas as pd

DB_PATH = "data/pipeline.db"   # CHANGE to your Phase 1 database path
SEED = 42                      # fixed seed = same trades every run
N_TRADES = 400
DEFECT_RATE = 0.02             # share of rows given deliberate defects


def currency_for(ticker: str) -> str:
    """Quote currency from the ticker suffix."""
    t = ticker.upper()
    if t.endswith(".L"):
        return "GBp"  # London quotes in pence, not pounds
    if t.endswith((".DE", ".PA", ".AS", ".MI")):
        return "EUR"
    return "USD"

TRADE_SIZES_GBP = (500, 1_000, 2_000, 5_000)   # typical order sizes
POUND_QUOTED = {"VWRL.L"}   # .L tickers quoted in pounds, not pence (keep in sync with dim_security)


def approx_price_gbp(ticker: str, price: float) -> float:
    """Rough GBP price per share. Used ONLY to size trades, never for valuation."""
    t = ticker.upper()
    if t.endswith(".L"):
        return price if t in POUND_QUOTED else price / 100
    if t.endswith((".DE", ".PA", ".AS", ".MI")):
        return price * 0.85
    return price * 0.78


def load_prices(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT ticker, date, close FROM raw_prices WHERE source = 'yfinance'", conn
    )
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna(subset=["close"])


def generate_trades(prices: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    tickers = sorted(t for t in prices["ticker"].unique() if not t.startswith("^"))
    close_by_ticker = {
        t: g.set_index("date")["close"] for t, g in prices.groupby("ticker")
    }
    all_dates = sorted(prices["date"].unique())
    trade_dates = sorted(rng.choices(all_dates, k=N_TRADES))

    holdings = {t: 0 for t in tickers}
    rows = []

    for d in trade_dates:
        ticker = rng.choice(tickers)
        closes = close_by_ticker[ticker]
        if d not in closes.index:
            continue  # no price for this ticker on this date

        # Fill price = that day's close plus up to +/-0.2% slippage
        price = round(float(closes.loc[d]) * (1 + rng.uniform(-0.002, 0.002)), 4)

        if holdings[ticker] == 0 or rng.random() < 0.65:
            side = "BUY"
            target = rng.choice(TRADE_SIZES_GBP)
            qty = max(1, round(target / approx_price_gbp(ticker, price)))
        else:
            side = "SELL"  # sell a quarter, half or all of the holding
            qty = max(1, round(holdings[ticker] * rng.choice([0.25, 0.5, 1.0])))

        holdings[ticker] += qty if side == "BUY" else -qty
        fee = round(0.001 * qty * price, 2)  # 0.1% commission, same units as price

        rows.append(
            {
                "trade_id": f"T{len(rows) + 1:05d}",
                "trade_date": pd.Timestamp(d).strftime("%Y-%m-%d"),
                "ticker": ticker,
                "side": side,
                "quantity": qty,
                "price": price,
                "currency": currency_for(ticker),
                "fee": fee,
            }
        )

    return pd.DataFrame(rows)


def inject_defects(df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """Make the raw layer realistically messy so the cleaning layer has work to do."""
    df = df.copy()
    n = max(2, int(len(df) * DEFECT_RATE))

    # Defect 1: lowercase, space-padded tickers
    for i in rng.sample(range(len(df)), k=n):
        df.at[i, "ticker"] = " " + df.at[i, "ticker"].lower() + " "

    # Defect 2: exact duplicate rows (same trade_id loaded twice)
    dupes = df.iloc[rng.sample(range(len(df)), k=n)]
    return pd.concat([df, dupes], ignore_index=True)


def main() -> None:
    rng = random.Random(SEED)
    with sqlite3.connect(DB_PATH) as conn:
        prices = load_prices(conn)
        trades = inject_defects(generate_trades(prices, rng), rng)
        trades["loaded_at"] = datetime.now(timezone.utc).isoformat()
        trades.to_sql("raw_trades", conn, if_exists="replace", index=False)

    print(f"Wrote {len(trades)} rows to raw_trades "
          f"({trades['trade_id'].nunique()} unique trades)")


if __name__ == "__main__":
    main()