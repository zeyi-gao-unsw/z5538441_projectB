"""Pipeline tests for the Part B (Station 3) build.

Run from the project folder:

    python -m pytest -q

Data-dependent tests load through src/data_access.py (cached after the first
download). The backtest tests run on a small real-data subset so the suite
stays fast; the sentiment and fusion tests use synthetic inputs.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import etl, features, fusion, portfolios, sentiment  # noqa: E402


# --------------------------------------------------------------------------
# Session fixtures: real data (downloaded once), small panels for speed
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def clean_data():
    equity = etl.load_clean_equity()
    crypto = etl.load_clean_crypto()
    return equity, crypto


@pytest.fixture(scope="session")
def panels(clean_data):
    equity, crypto = clean_data
    eq_ret = features.daily_returns(equity)
    cr_ret = features.daily_returns(crypto)
    combined = features.combined_returns_panel(eq_ret, cr_ret)
    return {"equity": eq_ret, "crypto": cr_ret, "combined": combined}


@pytest.fixture(scope="session")
def small_panel(panels):
    """12 combined-panel tickers over ~1.5 years: fast but real backtest data."""
    panel = panels["combined"].dropna().iloc[:380, :12]
    return panel


@pytest.fixture(scope="session")
def subset_weights(small_panel):
    """Rebalance weights for every method on the small real panel."""
    return {m: portfolios.compute_rebalance_weights(small_panel, m)
            for m in portfolios.OPTIMISERS}


# --------------------------------------------------------------------------
# 1. Returns are computed WITHIN each panel's own calendar
# --------------------------------------------------------------------------

def test_returns_within_panels(panels):
    eq_ret, cr_ret = panels["equity"], panels["crypto"]
    # first return per ticker is NaN (no prior price inside the panel)
    assert eq_ret.iloc[0].isna().all()
    assert cr_ret.iloc[0].isna().all()
    # equity panel keeps its own calendar, crypto its own
    assert len(cr_ret) > len(eq_ret)
    # combined panel is a reindex of within-panel returns, NOT a fresh
    # differencing of merged price levels: a merged crypto value must equal
    # the crypto panel's own return on that day
    combined = panels["combined"]
    day = combined.dropna().index[10]
    coin = panels["crypto"].columns[0]
    assert combined.loc[day, coin] == pytest.approx(cr_ret.loc[day, coin])
    # no weekend dates leak into the combined panel
    assert combined.index.equals(eq_ret.index)


# --------------------------------------------------------------------------
# 2. Rebalance weights are long-only and fully invested, and methods differ
# --------------------------------------------------------------------------

def test_weights_long_only_and_sum_to_one(subset_weights):
    for method, w in subset_weights.items():
        assert len(w) > 0, method
        sums = w.sum(axis=1).to_numpy()
        assert np.allclose(sums, 1.0, atol=1e-6), f"{method}: sums {sums}"
        assert (w.to_numpy() >= 0.0).all(), f"{method}: negative weight"


def test_weights_differ_across_methods(subset_weights):
    """Solver-stall guard: identical weights across methods would mean the
    optimiser silently returned the equal-weight start point."""
    names = list(subset_weights)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            wa = subset_weights[a]
            wb = subset_weights[b].loc[wa.index, wa.columns]
            diff = (wa - wb).abs().to_numpy().mean()
            assert diff > 1e-6, f"{a} and {b} produced identical weights"


# --------------------------------------------------------------------------
# 3. OOS period starts only after the first 252 trading days
# --------------------------------------------------------------------------

def test_oos_starts_after_estimation_window(small_panel):
    rets, weights = None, None
    for method in portfolios.OPTIMISERS:
        w = portfolios.compute_rebalance_weights(small_panel, method)
        r = portfolios.portfolio_returns(small_panel, w)
        first_pos = small_panel.index.get_loc(r.index[0])
        assert first_pos > portfolios.WINDOW, \
            f"{method}: OOS starts at position {first_pos}"
        # and the estimation slice excludes the rebalance day itself
        p = small_panel.index.get_loc(w.index[0])
        assert p >= portfolios.WINDOW
    # no look-ahead in portfolio_returns: day t uses weights set before t
    w = portfolios.compute_rebalance_weights(small_panel, "min_variance")
    r = portfolios.portfolio_returns(small_panel, w)
    assert r.index[0] > w.index[0]


# --------------------------------------------------------------------------
# 4. Sentiment index is lagged by exactly one trading day
# --------------------------------------------------------------------------

def _synthetic_ticker_day():
    days = pd.bdate_range("2023-01-02", periods=20)
    rng = np.random.default_rng(7)
    rows = []
    for d in days:
        for t in ("AAA", "BBB", "CCC"):
            if rng.random() < 0.8:  # some ticker-days have no headlines
                rows.append({"ticker": t, "trading_day": d,
                             "sentiment": rng.normal(0, 0.3)})
    return pd.DataFrame(rows), days


def test_sentiment_index_lagged_one_day():
    ticker_day, days = _synthetic_ticker_day()
    sector_map = pd.DataFrame({
        "ticker": ["AAA", "BBB", "CCC"],
        "sector": ["Tech", "Tech", "Energy"],
    })
    lagged, pre_lag = sentiment.sector_sentiment_index(
        ticker_day, sector_map, days)
    # value on day t equals the pre-lag index on t-1, exactly
    pd.testing.assert_frame_equal(lagged.iloc[1:].reset_index(drop=True),
                                  pre_lag.iloc[:-1].reset_index(drop=True))
    # first day has no prior information -> neutral
    assert (lagged.iloc[0] == 0.0).all()


def test_finance_lexicon_extension_scores():
    analyzer = sentiment.make_analyzer()
    assert "plunge" in analyzer.lexicon  # added by the finance extension
    scored = sentiment.score_headlines(pd.DataFrame({
        "title": ["Shares plunge after downgrade",
                  "Profit surges to record high"],
        "trading_day": [pd.Timestamp("2023-01-03")] * 2,
        "ticker": ["AAA", "AAA"],
    }), analyzer)
    assert scored.loc[0, "compound"] < 0
    assert scored.loc[1, "compound"] > 0


# --------------------------------------------------------------------------
# 5. Fusion tilt preserves the weight budget and non-negativity
# --------------------------------------------------------------------------

def test_fusion_tilt_preserves_constraints():
    days = pd.bdate_range("2023-01-02", periods=10)
    tickers = ["AAA", "BBB", "CCC", "DDD"]
    sector_map = pd.DataFrame({
        "ticker": tickers,
        "sector": ["Tech", "Tech", "Energy", "Energy"],
    })
    base = pd.DataFrame(0.25, index=[days[5], days[8]], columns=tickers)
    sent = pd.DataFrame({"Tech": np.linspace(0.4, 0.6, 10),
                         "Energy": np.linspace(-0.3, -0.1, 10)}, index=days)
    tilted = fusion.apply_sentiment_tilt(base, sent, alpha=0.25,
                                         ticker_sector=sector_map)
    assert np.allclose(tilted.sum(axis=1), 1.0, atol=1e-6)
    assert (tilted.to_numpy() >= 0.0).all()
    # positive-sentiment sector gains weight, negative loses it
    assert tilted.loc[days[5], "AAA"] > base.loc[days[5], "AAA"]
    assert tilted.loc[days[5], "CCC"] < base.loc[days[5], "CCC"]


def test_fusion_tilt_uses_only_past_sentiment():
    """The tilt at a rebalance date must not react to sentiment rows AFTER it."""
    days = pd.bdate_range("2023-01-02", periods=10)
    sector_map = pd.DataFrame({"ticker": ["AAA"], "sector": ["Tech"]})
    base = pd.DataFrame(1.0, index=[days[5]], columns=["AAA"])
    sent_a = pd.DataFrame({"Tech": [0.1] * 6 + [9.9] * 4}, index=days)
    sent_b = pd.DataFrame({"Tech": [0.1] * 6 + [-9.9] * 4}, index=days)
    ta = fusion.apply_sentiment_tilt(base, sent_a, ticker_sector=sector_map)
    tb = fusion.apply_sentiment_tilt(base, sent_b, ticker_sector=sector_map)
    # future sentiment (after the rebalance date) differs wildly; the tilted
    # weight on the rebalance date must be identical either way
    assert ta.loc[days[5], "AAA"] == pytest.approx(tb.loc[days[5], "AAA"])


# --------------------------------------------------------------------------
# 6. News-to-trading-day mapping rules
# --------------------------------------------------------------------------

def test_headline_mapping_next_trading_day(clean_data):
    equity, _ = clean_data
    days = pd.DatetimeIndex(sorted(equity["date"].unique()))
    raw = pd.DataFrame({
        "ticker": ["AAA", "AAA", "AAA"],
        "date": pd.to_datetime(["2023-01-14", "2023-01-16", "2023-12-31"]),
        "title": ["t1", "t2", "t3"],
        "sector": ["Tech"] * 3,
    })
    # 2023-01-14 is a Saturday, 2023-01-16 was MLK Day (both -> Tue 17th);
    # 2023-12-31 has no next trading day in-sample -> dropped
    mapped = etl.map_headlines_to_trading_days(raw, days)
    assert len(mapped) == 2
    assert (mapped["trading_day"] == pd.Timestamp("2023-01-17")).all()
