import pandas as pd

from pipeline.checks import run_all_checks


def _bars(ticker: str) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-01", "2024-02-29").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "ticker": ticker,
            "date": dates,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "adj_close": 100.5,
            "volume": 1000,
        }
    )


def test_checks_pass_on_clean_data_and_catch_each_problem():
    clean = pd.concat([_bars("AAA"), _bars("BBB")], ignore_index=True)
    results = run_all_checks(clean, ["AAA", "BBB"], max_gap_days=7)
    assert all(r.passed for r in results), [r for r in results if not r.passed]

    bad = clean.copy()
    # gap: remove three weeks of AAA
    bad = bad[~((bad.ticker == "AAA") & bad.date.between("2024-01-10", "2024-01-31"))]
    # duplicate: repeat a BBB row
    bad = pd.concat([bad, bad[bad.ticker == "BBB"].head(1)], ignore_index=True)
    # non-positive price
    bad.loc[bad.index[0], "close"] = -1.0

    # "ZZZ" is in the config but never returned any rows
    outcome = {r.name: r for r in run_all_checks(bad, ["AAA", "BBB", "ZZZ"], max_gap_days=7)}
    assert not outcome["ticker_resolved"].passed and "ZZZ" in outcome["ticker_resolved"].detail
    assert not outcome["no_duplicates"].passed
    assert not outcome["no_long_gaps"].passed
    assert not outcome["positive_prices"].passed
