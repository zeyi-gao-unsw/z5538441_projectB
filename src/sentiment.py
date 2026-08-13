"""Station 3 - News sentiment: VADER with an extended finance lexicon.

VADER is a general-purpose social-media lexicon, so roughly half of finance
headlines score neutral with it - many of them false neutrals ("plunge",
"downgrade", "beat" carry clear financial meaning but no general sentiment).
As a deliberate extension, FINANCE_LEXICON adds ~60 finance-specific terms
with hand-assigned scores on VADER's -4..+4 scale (sign = direction, magnitude
= strength, mirroring VADER's own conventions). The terms are merged into
VADER's lexicon at runtime; VADER's original entries are untouched, so
casing/punctuation/intensifier handling is preserved (which is why the raw
headline text is scored whole, never stripped).

Pipeline (per the project spec):
1. score every headline's compound value
2. average per ticker x trading day
3. 5-day EMA smoothing per ticker (min_periods=1)
4. equal-weight average across tickers within a sector -> daily sector index
5. forward-fill sector gaps up to 10 trading days, then neutral 0.0
6. lag the whole index by EXACTLY 1 trading day (shift(1)) so day t's value
   uses only information available up to t-1 (no look-ahead)
"""
from __future__ import annotations

import pandas as pd

from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Deliberate extension over plain VADER: finance terms with scores on
# VADER's -4 (very negative) .. +4 (very positive) scale.
FINANCE_LEXICON = {
    # earnings & guidance
    "beat": 2.0, "beats": 2.0, "miss": -2.0, "misses": -2.0,
    "outperform": 2.2, "outperforms": 2.2, "underperform": -2.2,
    "guidance": 0.3, "raises guidance": 2.4, "cuts guidance": -2.4,
    "upgrade": 2.0, "upgrades": 2.0, "upgraded": 2.0,
    "downgrade": -2.0, "downgrades": -2.0, "downgraded": -2.0,
    "overweight": 1.2, "underweight": -1.2, "buy": 1.4, "sell": -1.4,
    # price action
    "surge": 2.5, "surges": 2.5, "soar": 2.5, "soars": 2.5, "rally": 2.2,
    "rallies": 2.2, "jump": 1.8, "jumps": 1.8, "gain": 1.5, "gains": 1.5,
    "record": 1.8, "all-time high": 2.4,
    "plunge": -2.5, "plunges": -2.5, "plummet": -2.6, "plummets": -2.6,
    "tumble": -2.2, "tumbles": -2.2, "slump": -2.0, "slumps": -2.0,
    "sink": -2.0, "sinks": -2.0, "drop": -1.6, "drops": -1.6,
    "fall": -1.5, "falls": -1.5, "decline": -1.4, "declines": -1.4,
    "crash": -2.8, "crashes": -2.8, "selloff": -2.2, "sell-off": -2.2,
    "rout": -2.4, "rebound": 1.8, "rebounds": 1.8, "recover": 1.6,
    "recovers": 1.6, "recovery": 1.6, "volatile": -0.8, "volatility": -0.6,
    # corporate events
    "layoffs": -2.2, "layoff": -2.2, "job cuts": -2.2, "fired": -1.8,
    "fraud": -3.2, "fraudulent": -3.2, "scandal": -2.8, "probe": -2.0,
    "investigation": -1.8, "lawsuit": -1.9, "sued": -2.0, "fine": -1.7,
    "fined": -1.9, "penalty": -1.7, "recall": -1.8, "bankruptcy": -3.4,
    "bankrupt": -3.4, "default": -2.8, "delisting": -2.4, "halt": -1.2,
    "acquisition": 1.5, "acquires": 1.5, "merger": 1.4, "buyback": 1.8,
    "buybacks": 1.8, "dividend": 1.2, "spinoff": 0.8, "ipo": 0.6,
    "approval": 1.6, "approved": 1.6, "partnership": 1.2,
    # macro / sentiment
    "growth": 1.2, "profit": 1.5, "profits": 1.5, "profitable": 1.6,
    "loss": -1.6, "losses": -1.6, "weak": -1.3, "weakness": -1.4,
    "strong": 1.3, "strength": 1.3, "optimism": 1.6, "optimistic": 1.6,
    "pessimism": -1.6, "fear": -1.7, "fears": -1.7, "concern": -1.2,
    "concerns": -1.2, "warning": -1.8, "warns": -1.8, "risk": -1.0,
    "recession": -2.4, "inflation": -1.0, "hike": -0.8, "cut": -0.8,
}

EMA_SPAN = 5
FFILL_LIMIT = 10
NEUTRAL = 0.0


def make_analyzer() -> SentimentIntensityAnalyzer:
    """VADER analyser with the extended finance lexicon merged in."""
    analyzer = SentimentIntensityAnalyzer()
    analyzer.lexicon.update(FINANCE_LEXICON)
    return analyzer


def score_headlines(
    news_mapped: pd.DataFrame, analyzer: SentimentIntensityAnalyzer | None = None
) -> pd.DataFrame:
    """Compound VADER score for every headline (adds a 'compound' column)."""
    if analyzer is None:
        analyzer = make_analyzer()
    out = news_mapped.copy()
    out["compound"] = [analyzer.polarity_scores(t)["compound"]
                       for t in out["title"].astype(str)]
    return out


def ticker_day_sentiment(scored: pd.DataFrame) -> pd.DataFrame:
    """Mean compound per ticker x trading day."""
    return (scored.groupby(["ticker", "trading_day"])["compound"]
            .mean().rename("sentiment").reset_index())


def sector_sentiment_index(
    ticker_day: pd.DataFrame,
    ticker_sector: pd.DataFrame,
    equity_trading_days: pd.DatetimeIndex,
    ema_span: int = EMA_SPAN,
    ffill_limit: int = FFILL_LIMIT,
    lag: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Daily sector sentiment index: EMA, sector average, gap fill, then lag.

    Returns (lagged_index, pre_lag_index), each date x sector. The lagged
    frame is the tradeable signal: day t's value is the pre-lag value at t-1.
    Ticker-days with no headlines are left NaN until the sector average
    (equal-weight over tickers WITH a reading that day), then sector gaps are
    forward-filled up to `ffill_limit` trading days before falling back to
    neutral 0.0.
    """
    days = pd.DatetimeIndex(equity_trading_days)
    sector_map = ticker_sector.set_index("ticker")["sector"]

    wide = ticker_day.pivot(index="trading_day", columns="ticker",
                            values="sentiment").reindex(days)
    # 5-day EMA per ticker over the trading calendar (NaN gaps stay NaN)
    smooth = wide.ewm(span=ema_span, min_periods=1, ignore_na=True).mean()
    smooth = smooth.where(wide.notna())

    # equal-weight average of tickers within each sector, per day
    sectors = {}
    for sector in sector_map.unique():
        tickers = sector_map[sector_map == sector].index
        cols = [t for t in tickers if t in smooth.columns]
        sectors[sector] = smooth[cols].mean(axis=1)
    index = pd.DataFrame(sectors, index=days).sort_index(axis=1)

    # forward-fill gaps up to `ffill_limit` trading days, then neutral 0.0
    index = index.ffill(limit=ffill_limit).fillna(NEUTRAL)

    pre_lag = index
    lagged = pre_lag.shift(lag).fillna(NEUTRAL)
    lagged.index.name = "date"
    pre_lag.index.name = "date"
    return lagged, pre_lag
