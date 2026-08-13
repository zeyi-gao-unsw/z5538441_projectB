"""Station 1 - ETL: load, clean, and quality-check the raw datasets.

All raw data loads ONLY through ``src/data_access.py``. This module applies the
cleaning rules from ``context/DATA_GUIDE.md``:

- prices are unique on (ticker, date) - exact duplicates dropped if any appear
- news is de-duplicated on exact (ticker, date, title) matches (~2,847 rows)
- news dates are tz-aware UTC while prices are tz-naive, so news dates are
  normalised with ``.dt.tz_localize(None)`` and floored to midnight
- crypto has 10 stray rows dated 2024-01-01; the sample is capped at 2023-12-31
- integrity checks: a missing-date audit per ticker and an extreme-return screen
  (|daily return| > 50%). Extreme returns are real market events (e.g. the 2020
  crash and meme/crypto squeezes): they are FLAGGED and KEPT, never deleted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_access

CRYPTO_SAMPLE_END = pd.Timestamp("2023-12-31")
EXTREME_RETURN_THRESHOLD = 0.50


def _dedup_prices(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Prices must be unique on (ticker, date); drop exact duplicates if any."""
    n_dup = df.duplicated(["ticker", "date"]).sum()
    if n_dup:
        print(f"[etl] {name}: dropped {n_dup} duplicate ticker-date rows")
    df = df.drop_duplicates(["ticker", "date"], keep="first")
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def _missing_date_audit(df: pd.DataFrame, name: str) -> pd.Series:
    """Count, per ticker, dates on the panel's union calendar the ticker lacks."""
    calendar = pd.DatetimeIndex(sorted(df["date"].unique()))
    per_ticker = df.groupby("ticker")["date"].nunique()
    missing = len(calendar) - per_ticker
    missing = missing[missing > 0].sort_values(ascending=False)
    if len(missing):
        print(f"[etl] {name}: missing-date audit (vs union calendar of "
              f"{len(calendar)} days):")
        for ticker, n in missing.items():
            print(f"      {ticker}: {n} missing day(s)")
    else:
        print(f"[etl] {name}: no missing dates on the union calendar "
              f"({len(calendar)} days) for any ticker")
    return missing


def _extreme_return_screen(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Flag |daily return| > 50%. Flagged rows are KEPT and documented.

    These are genuine market events (crash days, short squeezes, crypto
    rallies), not data errors, so deleting them would corrupt the backtest.
    """
    px = df.pivot(index="date", columns="ticker", values="adjClose").sort_index()
    rets = px.pct_change()
    extreme = rets.abs() > EXTREME_RETURN_THRESHOLD
    n_flag = int(extreme.sum().sum())
    print(f"[etl] {name}: extreme-return screen |r| > "
          f"{EXTREME_RETURN_THRESHOLD:.0%}: {n_flag} observation(s) flagged "
          f"(KEPT - genuine market moves, documented, never deleted)")
    if n_flag:
        flagged = rets[extreme].stack().dropna().sort_values()
        for (date, ticker), r in flagged.items():
            print(f"      {ticker} {date.date()}: {r:+.1%}")
    return df


def load_clean_equity() -> pd.DataFrame:
    """Clean equity prices: dedup on ticker+date, audits, outlier screen."""
    df = data_access.load_equity_prices().copy()
    df = _dedup_prices(df, "equity_prices")
    _missing_date_audit(df, "equity_prices")
    _extreme_return_screen(df, "equity_prices")
    return df


def load_clean_crypto() -> pd.DataFrame:
    """Clean crypto prices: cap at 2023-12-31, dedup, audits, outlier screen."""
    df = data_access.load_crypto_prices().copy()
    n_stray = int((df["date"] > CRYPTO_SAMPLE_END).sum())
    df = df[df["date"] <= CRYPTO_SAMPLE_END]
    print(f"[etl] crypto_prices: dropped {n_stray} stray rows dated after "
          f"{CRYPTO_SAMPLE_END.date()} (sample capped at 2023-12-31)")
    df = _dedup_prices(df, "crypto_prices")
    _missing_date_audit(df, "crypto_prices")
    _extreme_return_screen(df, "crypto_prices")
    return df


def load_clean_news() -> pd.DataFrame:
    """Clean news: exact-dup removal on ticker+date+title, tz normalisation.

    The raw ``date`` is tz-aware UTC; prices are tz-naive, so the timezone is
    stripped and the timestamp floored to midnight before any calendar work.
    Publisher is often blank - left as-is (not used downstream).
    """
    df = data_access.load_news_headlines().copy()
    n0 = len(df)
    df = df.drop_duplicates(["ticker", "date", "title"], keep="first")
    print(f"[etl] news_headlines: dropped {n0 - len(df)} exact duplicate rows "
          f"(ticker+date+title); {len(df)} remain")
    df["date"] = df["date"].dt.tz_localize(None).dt.normalize()
    df = df.sort_values(["date", "ticker"]).reset_index(drop=True)
    return df


def map_headlines_to_trading_days(
    news: pd.DataFrame, equity_trading_days: pd.DatetimeIndex
) -> pd.DataFrame:
    """Align every headline to an equity trading day.

    A headline maps to the SAME day if that day is a trading day, otherwise to
    the NEXT trading day (weekend/holiday news is first actionable on the next
    session). Headlines after the last trading day have no next trading day and
    are DROPPED (count printed) - never clipped onto the final session.
    """
    days = pd.DatetimeIndex(equity_trading_days).sort_values()
    dates = pd.DatetimeIndex(news["date"])
    pos = days.searchsorted(dates)  # first trading day >= headline date
    mapped = days[np.minimum(pos, len(days) - 1)]
    has_next = pos < len(days)

    out = news.copy()
    out["trading_day"] = mapped
    n_dropped = int((~has_next).sum())
    out = out[has_next].reset_index(drop=True)
    print(f"[etl] headline->trading-day mapping: {n_dropped} headline(s) "
          f"dropped (no next trading day within the sample); "
          f"{len(out)} mapped")
    return out
