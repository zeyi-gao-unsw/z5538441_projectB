"""Station 2 - Feature engineering: returns panels and the daily text panel.

Calendar rules (per context/DATA_GUIDE.md):
- daily simple returns are computed from adjClose WITHIN each panel's own
  calendar first - never merge price levels across calendars and then
  difference (that creates spurious returns)
- the combined panel left-merges crypto returns onto the equity trading
  calendar; weekend-only crypto moves are intentionally dropped (a fund that
  trades on equity days cannot act on them)
"""
from __future__ import annotations

import pandas as pd


def price_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Wide adjClose matrix (date x ticker) on the panel's own calendar."""
    return prices.pivot(index="date", columns="ticker", values="adjClose").sort_index()


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily simple returns within the panel's own calendar.

    The first row per ticker is NaN (no prior price in-panel). Returns are
    never differenced across panels - each panel keeps its own calendar here.
    """
    return price_matrix(prices).pct_change()


def combined_returns_panel(
    equity_returns: pd.DataFrame, crypto_returns: pd.DataFrame
) -> pd.DataFrame:
    """Left-merge crypto returns onto the equity trading calendar.

    Equities trade ~252 days/yr, crypto ~365. Reindexing crypto returns to the
    equity calendar keeps every equity session's crypto move (which already
    includes the preceding weekend drift, since crypto returns were computed on
    their own calendar) and drops pure-weekend moves - intended behaviour.
    """
    crypto_on_eq = crypto_returns.reindex(equity_returns.index)
    combined = equity_returns.join(crypto_on_eq)
    combined.index.name = "date"
    return combined.sort_index()


def daily_news_panel(
    news_mapped: pd.DataFrame, equity_trading_days: pd.DatetimeIndex
) -> pd.DataFrame:
    """Per ticker x trading day: list of that day's headlines plus the sector.

    ``news_mapped`` must carry a ``trading_day`` column (see
    etl.map_headlines_to_trading_days). Raw headline text is kept whole - no
    stopword stripping or casing changes, because VADER relies on punctuation,
    casing and 'non-sentiment' words.
    """
    rows = (
        news_mapped.groupby(["trading_day", "ticker"])
        .agg(headlines=("title", list), sector=("sector", "first"))
        .reset_index()
        .rename(columns={"trading_day": "date"})
    )
    days = pd.DatetimeIndex(equity_trading_days)
    return rows[rows["date"].isin(days)].sort_values(["date", "ticker"]).reset_index(drop=True)
