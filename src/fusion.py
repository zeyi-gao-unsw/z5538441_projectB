"""Station 3 - Fusion: fold the equity sentiment signal into the equity fund.

The ticker -> sector mapping is derived from the loaded data at runtime
(data_access.load_sector_universe(), itself built from equity_prices) - never
a hardcoded sector-name dict.

Tilt rule (apply_sentiment_tilt): for each rebalance date, take the most
recent LAGGED sector sentiment row on or before that date, z-score it across
the 10 sectors, then scale each ticker's base weight multiplicatively by
(1 + alpha * z_sector). Weights are clipped at 0 and renormalised to sum 1,
so the tilted fund stays long-only and fully invested. Because the sentiment
index is already lagged by one trading day, the tilt uses only information
available before the rebalance day.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_access

DEFAULT_ALPHA = 0.25


def ticker_sector_map() -> pd.DataFrame:
    """Ticker -> sector from the live data (never hardcoded)."""
    return data_access.load_sector_universe()


def _zscore(row: pd.Series) -> pd.Series:
    std = row.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return row * 0.0
    return (row - row.mean()) / std


def apply_sentiment_tilt(
    base_weights: pd.DataFrame,
    sentiment_index: pd.DataFrame,
    alpha: float = DEFAULT_ALPHA,
    ticker_sector: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Tilt base weights by sector sentiment at each rebalance date.

    base_weights: wide (rebalance date x ticker) table from the base fund.
    sentiment_index: lagged daily sector index (date x sector).
    Returns a wide tilted-weight table on the same rebalance dates.
    """
    if ticker_sector is None:
        ticker_sector = ticker_sector_map()
    sector_of = ticker_sector.set_index("ticker")["sector"]

    sent = sentiment_index.sort_index()
    tilted = {}
    for d in base_weights.index:
        available = sent.index[sent.index <= d]
        if len(available) == 0:
            tilted[d] = base_weights.loc[d].to_numpy()
            continue
        z = _zscore(sent.loc[available[-1]])  # z-scored across sectors that day
        w = base_weights.loc[d].astype(float).copy()
        for ticker in w.index:
            sector = sector_of.get(ticker)
            if sector is not None and sector in z.index:
                w[ticker] = w[ticker] * (1.0 + alpha * float(z[sector]))
        w = w.clip(lower=0.0)
        total = w.sum()
        tilted[d] = (w / total).to_numpy() if total > 0 else base_weights.loc[d].to_numpy()
    out = pd.DataFrame(tilted).T
    out.index.name = "date"
    out.columns = base_weights.columns
    return out
