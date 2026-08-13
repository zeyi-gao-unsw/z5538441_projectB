"""Run the full Part B (Station 3) pipeline end to end.

    python scripts/run_part_b.py

Steps: ETL -> returns panels -> walk-forward OOS backtests (7 funds) ->
VADER sentiment + sector index -> sentiment-tilt fusion fund -> required
output CSVs -> exhibit figures. First run downloads ~11 MB of data once and
scores ~150k headlines with VADER, so it can take several minutes.
"""
from __future__ import annotations

import math
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import etl, features, fusion, portfolios, sentiment  # noqa: E402

RESULTS_DATA = ROOT / "results" / "data"
RESULTS_TABLES = ROOT / "results" / "tables"
RESULTS_FIGURES = ROOT / "results" / "figures"

# Muted FT-style palette: teal, maroon, gold, slate, charcoal + grey context.
PALETTE = ["#0F766E", "#990F3D", "#F2B701", "#4C78A8", "#262A33",
           "#6B9E8F", "#C0637F", "#D9A441", "#8FA8C8", "#7A7E87"]
GREY = "#9A9DA3"
TILT_FUND = "Equity+Sentiment Tilt"
BASE_FUND = "Equity Max-Sharpe"


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def _date_axis(ax, index, max_ticks=6):
    """Format a date axis: <= ~6 tick labels like 'Jan 2021', never crowded."""
    span_months = max(1, (index.max().year - index.min().year) * 12
                      + index.max().month - index.min().month)
    interval = max(1, math.ceil(span_months / max_ticks))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def _save(fig, name, caption, sample):
    """Save a PNG plus a small .caption.md stating the sample period."""
    fig.tight_layout()
    fig.savefig(RESULTS_FIGURES / f"{name}.png", dpi=150)
    plt.close(fig)
    full_caption = f"{caption} Sample period: {sample}."
    (RESULTS_FIGURES / f"{name}.caption.md").write_text(full_caption + "\n")
    print(f"      figure: results/figures/{name}.png")


# Method -> colour is FIXED across panels, so "what the method changes" is
# read off by colour within every family panel.
METHOD_COLOR = {
    "Equal-Weight": "#262A33",   # charcoal - the naive benchmark
    "Min-Variance": "#0F766E",   # teal
    "Max-Sharpe": "#990F3D",     # maroon
    "Risk-Parity": "#F2B701",    # gold
}
TILT_COLOR = "#4C78A8"           # slate, dashed - the fusion experiment
FAMILY_PANELS = [
    ("Combined - 50 shares + 10 coins",
     ["Combined Equal-Weight", "Combined Min-Variance",
      "Combined Max-Sharpe", "Combined Risk-Parity"]),
    ("Equity - 50 shares",
     ["Equity Equal-Weight", "Equity Min-Variance", "Equity Max-Sharpe",
      "Equity Risk-Parity", TILT_FUND]),
    ("Crypto - 10 coins (own calendar)",
     ["Crypto Equal-Weight", "Crypto Min-Variance", "Crypto Max-Sharpe",
      "Crypto Risk-Parity"]),
]


def _short_name(fund: str) -> str:
    """'Combined Max-Sharpe' -> 'Max-Sharpe'; the tilt fund -> 'Sentiment Tilt'."""
    if fund == TILT_FUND:
        return "Sentiment Tilt"
    for prefix in ("Combined ", "Equity ", "Crypto "):
        if fund.startswith(prefix):
            return fund[len(prefix):]
    return fund


def _spread(values: list[float], min_gap: float) -> list[float]:
    """Label y-positions: sorted terminal values pushed >= min_gap apart."""
    order = np.argsort(values)
    out = np.empty(len(values))
    prev = -np.inf
    for rank, idx in enumerate(order):
        out[idx] = max(values[idx], prev + min_gap)
        prev = out[idx]
    return list(out)


def fig_growth_of_1(fund_returns: pd.DataFrame, sample: str) -> None:
    """Growth of $1, one panel per asset family (13 lines never share an
    axis - the all-in-one version was unreadable). Line ends carry the
    method name and terminal value; panels use independent value scales."""
    growth = (1.0 + fund_returns).cumprod()
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6))
    for ax, (panel_title, cols) in zip(axes, FAMILY_PANELS):
        for col in cols:
            s = growth[col].dropna()
            is_tilt = col == TILT_FUND
            color = TILT_COLOR if is_tilt else METHOD_COLOR[_short_name(col)]
            ax.plot(s.index, s, color=color, lw=1.4,
                    ls="--" if is_tilt else "-")
        ends = [(col, float(growth[col].dropna().iloc[-1])) for col in cols]
        lo, hi = ax.get_ylim()
        label_x = growth.index.max() + pd.Timedelta(days=12)
        for (col, val), y in zip(ends, _spread([v for _, v in ends],
                                               0.05 * (hi - lo))):
            ax.annotate(f"{_short_name(col)}  ${val:.2f}", xy=(label_x, y),
                        fontsize=8, va="center",
                        color=TILT_COLOR if col == TILT_FUND
                        else METHOD_COLOR[_short_name(col)])
        ax.set_xlim(growth[col].dropna().index.min(),
                    label_x + pd.Timedelta(days=170))
        ax.set_title(panel_title, fontsize=10)
        ax.tick_params(labelsize=8)
        _date_axis(ax, growth[col].dropna().index, max_ticks=4)
    fig.suptitle("Growth of $1 invested - HyperInvest funds by family "
                 "(out-of-sample; panels scaled independently)", fontsize=12)
    _save(fig, "growth_of_1_all_funds",
          "Cumulative out-of-sample growth of $1 for every fund, one panel "
          "per asset family; method colours are shared across panels and "
          "line ends carry terminal values (panels scaled independently). "
          "Daily returns, monthly rebalancing, no transaction costs.",
          sample)


def fig_weights_over_time(weights: pd.DataFrame, days: pd.DatetimeIndex,
                          sample: str) -> None:
    """Step-filled top-5 holdings per rebalance. No 'Other' band: it
    dominated diversified funds and squashed the named holdings; the axis
    is fitted to the holdings actually shown."""
    w_daily = weights.reindex(days, method="ffill") * 100.0
    top5 = w_daily.mean().nlargest(5).index.tolist()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stackplot(w_daily.index, [w_daily[t] for t in top5], labels=top5,
                 colors=PALETTE[:5])
    ax.set_title("Portfolio weights over time - Combined Max-Sharpe fund")
    ax.set_xlabel("Date")
    ax.set_ylabel("Weight (%)")
    ax.set_ylim(0, w_daily[top5].sum(axis=1).max() * 1.08)
    ax.legend(loc="upper right", fontsize=8)
    _date_axis(ax, w_daily.index)
    _save(fig, "weights_combined_max_sharpe",
          "Target weights of the Combined Max-Sharpe fund at each monthly "
          "rebalance; top 5 holdings shown individually with the axis "
          "fitted to them, the remainder spread across all other assets "
          "(not shown).", sample)


def fig_sector_sentiment(lagged_index: pd.DataFrame, sample: str) -> None:
    """Sector sentiment index as a 2x5 small-multiple grid. One shared
    y-axis across panels is what makes the 'thinner-news sectors are
    noisier' claim visible; the zero line is dashed in every panel."""
    fig, axes = plt.subplots(2, 5, figsize=(13.5, 4.8), sharex=True,
                             sharey=True)
    for i, (ax, sector) in enumerate(zip(axes.flat, lagged_index.columns)):
        ax.plot(lagged_index.index, lagged_index[sector],
                color=PALETTE[i % len(PALETTE)], lw=0.7)
        ax.axhline(0, color=GREY, lw=0.7, ls="--")
        ax.set_title(sector, fontsize=9)
        ax.tick_params(labelsize=7)
    for ax in axes[-1]:
        _date_axis(ax, lagged_index.index, max_ticks=4)
    fig.suptitle("Daily sector news-sentiment index (VADER + finance "
                 "lexicon, lagged 1 trading day)", fontsize=12)
    fig.supylabel("Sentiment (compound score)", fontsize=10)
    _save(fig, "sector_sentiment_index",
          "Daily news-sentiment index per equity sector (one panel each, "
          "shared scale): VADER with an extended finance lexicon, averaged "
          "per ticker-day, 5-day EMA, equal-weighted within sector, lagged "
          "one trading day.", sample)


def main():
    for d in (RESULTS_DATA, RESULTS_TABLES, RESULTS_FIGURES):
        d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ ETL
    print("[1/6] ETL: loading and cleaning data")
    equity = etl.load_clean_equity()
    crypto = etl.load_clean_crypto()
    news = etl.load_clean_news()
    equity_days = pd.DatetimeIndex(sorted(equity["date"].unique()))
    news_mapped = etl.map_headlines_to_trading_days(news, equity_days)

    # ------------------------------------------------------------- features
    print("[2/6] Features: returns panels and daily text panel")
    equity_returns = features.daily_returns(equity)
    crypto_returns = features.daily_returns(crypto)          # own 365 calendar
    combined = features.combined_returns_panel(equity_returns, crypto_returns)
    text_panel = features.daily_news_panel(news_mapped, equity_days)
    print(f"      combined panel: {combined.shape[1]} assets x "
          f"{combined.shape[0]} equity trading days; "
          f"text panel: {len(text_panel)} ticker-days")

    panels = {
        "combined": combined.dropna(),
        "equity": equity_returns.dropna(),
        "crypto": crypto_returns.dropna(),                   # 365-day calendar
    }

    # ------------------------------------------------------------- backtest
    print("[3/6] Walk-forward OOS backtests (252-day window, monthly "
          "rebalance, rf=0, no transaction costs)")
    funds = portfolios.backtest_all(panels)

    print("      weight sanity check (solver stall guard):")
    sanity = portfolios.weights_sanity_check(funds)
    for _, row in sanity.iterrows():
        print(f"      {row['fund_a']} vs {row['fund_b']}: "
              f"mean |weight diff| = {row['mean_abs_weight_diff']:.4f}")
    assert (sanity["mean_abs_weight_diff"] > 1e-6).all(), \
        "weights identical across methods - solver stalled"
    sanity.to_csv(RESULTS_TABLES / "weights_sanity_check.csv", index=False)

    # ------------------------------------------------------------ sentiment
    print("[4/6] Sentiment: VADER + finance lexicon on "
          f"{len(news_mapped)} headlines")
    scored = sentiment.score_headlines(news_mapped)
    ticker_day = sentiment.ticker_day_sentiment(scored)
    sector_map = fusion.ticker_sector_map()
    lagged_index, pre_lag_index = sentiment.sector_sentiment_index(
        ticker_day, sector_map, equity_days)

    # --------------------------------------------------------------- fusion
    print("[5/6] Fusion: sentiment tilt on Equity Max-Sharpe "
          f"(alpha={fusion.DEFAULT_ALPHA})")
    base_weights = funds[BASE_FUND]["weights"]
    tilt_weights = fusion.apply_sentiment_tilt(base_weights, lagged_index)
    tilt_returns = portfolios.portfolio_returns(panels["equity"], tilt_weights)
    funds[TILT_FUND] = {"returns": tilt_returns, "weights": tilt_weights,
                        "family": "equity"}
    print(f"      {TILT_FUND}: OOS {tilt_returns.index.min().date()} -> "
          f"{tilt_returns.index.max().date()} ({len(tilt_returns)} days)")

    # -------------------------------------------------------------- outputs
    print("[6/6] Writing results/ outputs and figures")
    fund_returns = pd.DataFrame({name: f["returns"]
                                 for name, f in funds.items()})
    fund_returns.index.name = "date"
    fund_returns.to_csv(RESULTS_DATA / "fund_returns.csv")

    long_frames = []
    for name, f in funds.items():
        s = f["weights"].stack().rename("weight")
        s.index = s.index.set_names(["date", "ticker"])
        long_frames.append(
            s.reset_index().assign(fund=name)[["date", "fund", "ticker", "weight"]])
    weights_long = pd.concat(long_frames, ignore_index=True)
    weights_long.to_csv(RESULTS_DATA / "fund_weights.csv", index=False)

    lagged_index.to_csv(RESULTS_DATA / "sector_sentiment_index.csv")

    metrics_rows = []
    for name, f in funds.items():
        m = portfolios.performance_metrics(
            f["returns"], portfolios.annualisation_for(f["family"]))
        metrics_rows.append({"fund": name, **m})
    metrics = pd.DataFrame(metrics_rows)
    metrics.to_csv(RESULTS_TABLES / "performance_metrics.csv", index=False)
    print("\n" + metrics.to_string(index=False))

    comp = metrics[metrics["fund"].isin([BASE_FUND, TILT_FUND])] \
        .set_index("fund").T
    comp.columns = ["base_equity_max_sharpe", "equity_sentiment_tilt"]
    comp["difference"] = comp["equity_sentiment_tilt"] - comp["base_equity_max_sharpe"]
    comp.index.name = "metric"
    comp.to_csv(RESULTS_TABLES / "fusion_comparison.csv")
    print("\n" + comp.to_string())

    # -------------------------------------------------------------- figures
    oos_sample = (f"{fund_returns.index.min():%d %b %Y} - "
                  f"{fund_returns.index.max():%d %b %Y}")
    full_sample = f"{equity_days.min():%d %b %Y} - {equity_days.max():%d %b %Y}"

    # 1. growth of $1, all funds (one panel per family - see fig function)
    fig_growth_of_1(fund_returns, oos_sample)

    # 2. drawdown, Combined Max-Sharpe
    rets = funds["Combined Max-Sharpe"]["returns"]
    wealth = (1.0 + rets).cumprod()
    dd = wealth / wealth.cummax() - 1.0
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.fill_between(dd.index, dd * 100, 0, color=PALETTE[1], alpha=0.8)
    ax.set_title("Drawdown - Combined Max-Sharpe fund (out-of-sample)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    _date_axis(ax, dd.index)
    _save(fig, "drawdown_combined_max_sharpe",
          "Underwater plot (peak-to-trough loss) of the Combined Max-Sharpe "
          "fund over the out-of-sample period.", oos_sample)

    # 3. weights over time, Combined Max-Sharpe (top 5, axis fitted)
    fig_weights_over_time(funds["Combined Max-Sharpe"]["weights"],
                          rets.index, oos_sample)

    # 4. Sharpe barplot across funds
    fig, ax = plt.subplots(figsize=(9, 5))
    order = metrics.sort_values("sharpe", ascending=False)
    ax.bar(order["fund"], order["sharpe"],
           color=[PALETTE[i % len(PALETTE)] for i in range(len(order))])
    ax.axhline(0, color=PALETTE[4], lw=0.8)
    ax.set_title("Out-of-sample Sharpe ratio by fund (risk-free rate = 0)")
    ax.set_xlabel("Fund")
    ax.set_ylabel("Sharpe ratio (annualised)")
    ax.tick_params(axis="x", rotation=30)
    for tick in ax.get_xticklabels():
        tick.set_ha("right")
    _save(fig, "sharpe_by_fund",
          "Annualised out-of-sample Sharpe ratios for every fund, ranked. "
          "252-day annualisation for equity-containing funds, 365 for the "
          "pure-crypto fund.", oos_sample)

    # 5. sector sentiment index time series (2x5 grid, shared scale)
    fig_sector_sentiment(lagged_index, full_sample)

    # 6. fusion before vs after
    fig, ax = plt.subplots(figsize=(9, 5))
    g_base = (1.0 + funds[BASE_FUND]["returns"]).cumprod()
    g_tilt = (1.0 + funds[TILT_FUND]["returns"]).cumprod()
    ax.plot(g_base.index, g_base, label=BASE_FUND + " (base)",
            color=PALETTE[3], lw=1.5)
    ax.plot(g_tilt.index, g_tilt, label=TILT_FUND + f" (alpha={fusion.DEFAULT_ALPHA})",
            color=PALETTE[0], lw=1.5)
    ax.set_title("Fusion before vs after - growth of $1 (out-of-sample)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Value of $1 (USD)")
    ax.legend(fontsize=9)
    _date_axis(ax, g_base.index)
    _save(fig, "fusion_growth_of_1",
          "Growth of $1 for the base Equity Max-Sharpe fund versus the same "
          "fund with the sector-sentiment tilt applied at each rebalance.",
          oos_sample)

    # sector sentiment summary for the report
    summary = pd.DataFrame({
        "mean": lagged_index.mean(),
        "pct_below_zero": (lagged_index < 0).mean() * 100.0,
    })
    summary.to_csv(RESULTS_TABLES / "sector_sentiment_summary.csv")
    print("\nsector sentiment summary (lagged index):")
    print(summary.round(4).to_string())
    print(f"index range: {lagged_index.index.min().date()} -> "
          f"{lagged_index.index.max().date()}")

    print("\nDone. Outputs written to results/data, results/tables, "
          "results/figures.")


if __name__ == "__main__":
    main()
