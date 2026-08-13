"""Validate the project's sentiment model against the course's finVADER.

The project's required index (results/data/sector_sentiment_index.csv) scores
headlines with VADER + a custom ~60-term finance lexicon (src/sentiment.py).
The convener confirmed finVADER (taught in week 9) may be used, so this script
builds the COURSE's finVADER - VADER extended with the SentiBigNomics lexicon
(scores x0.1) and Henry's (2008) earnings-release word list - as an independent
benchmark, and compares the two models on identical inputs.

Only the lexicon differs. Cleaning (src/etl.py), the headline->trading-day
mapping, and the index construction (src/sentiment.sector_sentiment_index:
ticker-day average -> 5-day EMA -> equal-weight sector average -> ffill up to
10 trading days -> lag 1 trading day) are shared with the main pipeline, so
any divergence in the outputs is attributable to the lexicon alone.

    python scripts/build_sentiment_benchmark.py

Outputs (the required sector_sentiment_index.csv is NEVER overwritten):
  results/data/sector_sentiment_index_finvader.csv    finVADER sector index (lagged)
  results/tables/sentiment_model_comparison.csv       per-sector + ALL metrics
  results/tables/sentiment_disagreement_examples.csv  6 largest headline gaps
  results/figures/sentiment_model_comparison.png      overlays + correlation bars

The same headline is often attached to several tickers, so each DISTINCT title
is scored once per model and mapped back to rows - identical scores, much
faster. finVADER's analyser is also built once and reused: the finvader
package rebuilds its combined lexicon on every finvader() call, which is far
too slow for ~50k distinct titles (verified: the reused analyser returns
byte-identical compounds to finvader()).
"""
from __future__ import annotations

import pathlib
import sys
import time

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import etl, fusion, sentiment  # noqa: E402
from scripts.run_part_b import GREY, PALETTE, _date_axis, _save  # noqa: E402

RESULTS_DATA = ROOT / "results" / "data"
RESULTS_TABLES = ROOT / "results" / "tables"

TEAL = PALETTE[0]   # #0F766E - the project's custom-lexicon model
BENCH_GREY = GREY   # #9A9DA3 - the finVADER benchmark

OURS_COL = "our_compound"
FV_COL = "finvader_compound"


def make_finvader_analyzer() -> "sentiment.SentimentIntensityAnalyzer":
    """The course's finVADER analyser, built once and reused.

    VADER + SentiBigNomics entries scaled x0.1 (finVADER's tuning constant:
    SentiBigNomics scores run -1..1 against VADER's -4..4) + Henry's entries.
    """
    from finvader.Henry import lexicon2
    from finvader.SentiBignomics import lexicon1

    analyzer = sentiment.SentimentIntensityAnalyzer()
    sentibignomics = {term: value * 0.1 for term, value in lexicon1().items()}
    analyzer.lexicon.update({**sentibignomics, **lexicon2()})
    return analyzer


def score_distinct_titles(news_mapped: pd.DataFrame) -> pd.DataFrame:
    """Score every distinct title with BOTH models; one row per title."""
    titles = pd.Index(news_mapped["title"].astype(str).unique(), name="title")
    print(f"[benchmark] scoring {len(titles):,} distinct titles with each model")

    t0 = time.time()
    ours = sentiment.make_analyzer()
    our_scores = [ours.polarity_scores(t)["compound"] for t in titles]
    print(f"      custom lexicon done in {time.time() - t0:.0f}s")

    t0 = time.time()
    finvader = make_finvader_analyzer()
    fv_scores = [finvader.polarity_scores(t)["compound"] for t in titles]
    print(f"      finVADER done in {time.time() - t0:.0f}s "
          f"(combined lexicon: {len(finvader.lexicon):,} terms)")

    return pd.DataFrame({"title": titles, OURS_COL: our_scores,
                         FV_COL: fv_scores})


def build_finvader_index(
    scored: pd.DataFrame,
    sector_map: pd.DataFrame,
    equity_days: pd.DatetimeIndex,
) -> pd.DataFrame:
    """finVADER sector index via the project's own pipeline (identical params)."""
    fv_scored = scored.rename(columns={FV_COL: "compound"})
    fv_ticker_day = sentiment.ticker_day_sentiment(fv_scored)
    fv_lagged, _ = sentiment.sector_sentiment_index(
        fv_ticker_day, sector_map, equity_days)
    return fv_lagged


def check_shipped_index_reproducible(
    scored: pd.DataFrame,
    sector_map: pd.DataFrame,
    equity_days: pd.DatetimeIndex,
    shipped: pd.DataFrame,
) -> None:
    """Rebuild OUR index from this run's scores and compare with the shipped CSV.

    Guards against silent environment drift (e.g. an nltk/VADER version change
    altering the custom model's scores): if the rebuilt index matches the
    shipped artifact, comparing the benchmark against the shipped CSV is sound.
    """
    our_scored = scored.rename(columns={OURS_COL: "compound"})
    our_ticker_day = sentiment.ticker_day_sentiment(our_scored)
    our_lagged, _ = sentiment.sector_sentiment_index(
        our_ticker_day, sector_map, equity_days)
    our_lagged = our_lagged[shipped.columns]  # align column order
    max_diff = (our_lagged - shipped).abs().to_numpy().max()
    print(f"[benchmark] reproducibility check: rebuilt custom-lexicon index vs "
          f"shipped CSV - max |diff| = {max_diff:.2e}")
    if not np.allclose(our_lagged.to_numpy(), shipped.to_numpy(), atol=1e-9):
        print("      WARNING: rebuilt index differs from the shipped CSV beyond "
              "float noise; comparison below still uses the shipped artifact.")


def compare_indices(ours: pd.DataFrame, fv: pd.DataFrame) -> pd.DataFrame:
    """Per-sector Pearson r, mean |diff|, and sign-agreement % + an ALL row.

    Both inputs are LAGGED indices, compared on their overlapping date range.
    Sign agreement excludes days where either score is exactly 0.0: those are
    the neutral gap-fill (or day 1 after the lag), not a directional reading,
    so they carry no sign information.
    """
    common = ours.index.intersection(fv.index)
    print(f"[benchmark] comparing on {len(common)} overlapping trading days "
          f"({common.min().date()} -> {common.max().date()})")
    ours_c, fv_c = ours.loc[common], fv.loc[common]

    def _row(name: str, o: pd.Series, f: pd.Series) -> dict:
        nonzero = (o != 0.0) & (f != 0.0)
        agree = (np.sign(o[nonzero]) == np.sign(f[nonzero])).mean() * 100.0
        return {"sector": name,
                "pearson_r": o.corr(f),
                "mean_abs_diff": (o - f).abs().mean(),
                "sign_agreement_pct": agree,
                "n_days": len(o),
                "n_sign_days": int(nonzero.sum())}

    rows = [_row(sec, ours_c[sec], fv_c[sec]) for sec in fv_c.columns]
    rows.append(_row("ALL", ours_c.stack(), fv_c.stack()))
    return pd.DataFrame(rows)


def disagreement_examples(
    scores: pd.DataFrame, scored: pd.DataFrame, n: int = 6
) -> pd.DataFrame:
    """The n distinct headlines with the largest |our score - finVADER score|.

    Ranked per distinct title (the same wire story attached to 5 tickers is
    one headline); date/ticker are the first-seen row for that title.
    """
    top = scores.assign(abs_diff=(scores[OURS_COL] - scores[FV_COL]).abs()) \
                .nlargest(n, "abs_diff")
    first_seen = scored.sort_values("trading_day") \
                       .drop_duplicates("title")[["title", "date", "ticker"]]
    out = top.merge(first_seen, on="title", how="left")
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out = out[["date", "ticker", "title", OURS_COL, FV_COL, "abs_diff"]]
    return out.round({OURS_COL: 4, FV_COL: 4, "abs_diff": 4})


def make_figure(ours: pd.DataFrame, fv: pd.DataFrame,
                comparison: pd.DataFrame, sample: str) -> None:
    """Panel A: overlays for highest/median/lowest-r sectors. Panel B: r bars."""
    comp = comparison[comparison["sector"] != "ALL"] \
        .sort_values("pearson_r").reset_index(drop=True)
    picks = [(comp.index[-1], "highest correlation"),
             (comp.index[len(comp) // 2], "median correlation"),
             (comp.index[0], "lowest correlation")]

    fig = plt.figure(figsize=(11, 8))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.6, 1.0], hspace=0.45,
                          wspace=0.25)
    axes = [fig.add_subplot(gs[i, 0]) for i in range(3)]
    for k, (ax, (idx, label)) in enumerate(zip(axes, picks)):
        sector, r = comp.loc[idx, "sector"], comp.loc[idx, "pearson_r"]
        ax.plot(ours.index, ours[sector], color=TEAL, lw=1.3,
                label="Custom finance lexicon (project)")
        ax.plot(fv.index, fv[sector], color=BENCH_GREY, lw=1.1,
                label="finVADER (course benchmark)")
        ax.axhline(0, color=BENCH_GREY, lw=0.8, ls="--")
        ax.set_title(f"A{k + 1} - {sector}: {label} (r = {r:.2f})", fontsize=10)
        ax.set_ylabel("Sentiment (compound score)")
        _date_axis(ax, ours.index)
        if k == 0:
            ax.legend(fontsize=8, loc="lower right")
        if k < 2:
            plt.setp(ax.get_xticklabels(), visible=False)
        else:
            ax.set_xlabel("Date")

    ax_b = fig.add_subplot(gs[:, 1])
    order = comp.sort_values("pearson_r", ascending=False)
    ax_b.bar(order["sector"], order["pearson_r"], color=TEAL)
    ax_b.axhline(0, color=PALETTE[4], lw=0.8)
    ax_b.set_title("B - Pearson r by sector", fontsize=10)
    ax_b.set_xlabel("Sector")
    ax_b.set_ylabel("Pearson r (custom lexicon vs finVADER)")
    ax_b.tick_params(axis="x", rotation=45)
    for tick in ax_b.get_xticklabels():
        tick.set_ha("right")
    fig.suptitle("Sentiment model validation: custom finance lexicon vs "
                 "finVADER benchmark (daily sector indices, lagged 1 trading "
                 "day)", fontsize=12)

    _save(fig, "sentiment_model_comparison",
          "Validation of the project's sector news-sentiment index (VADER + a "
          "custom finance lexicon) against the course's finVADER benchmark "
          "(VADER + SentiBigNomics x0.1 + Henry 2008 word list) on identical "
          "headlines. Panel A overlays the two lagged daily indices for the "
          "highest-, median- and lowest-correlation sectors; panel B shows the "
          "per-sector Pearson correlation. Both indices use the same pipeline: "
          "ticker-day average, 5-day EMA, equal-weight sector average, "
          "forward-fill up to 10 trading days, lagged 1 trading day.", sample)


def main():
    for d in (RESULTS_DATA, RESULTS_TABLES):
        d.mkdir(parents=True, exist_ok=True)

    # Same cleaning and trading-day mapping as the main pipeline.
    print("[benchmark] ETL: loading and cleaning data (same as run_part_b.py)")
    equity = etl.load_clean_equity()
    news = etl.load_clean_news()
    equity_days = pd.DatetimeIndex(sorted(equity["date"].unique()))
    news_mapped = etl.map_headlines_to_trading_days(news, equity_days)

    # Score every distinct title with both models, map back to headline rows.
    scores = score_distinct_titles(news_mapped)
    scored = news_mapped.copy()
    scored["title"] = scored["title"].astype(str)
    scored = scored.merge(scores, on="title", how="left",
                          validate="many_to_one")
    assert scored[[OURS_COL, FV_COL]].notna().all().all()

    # finVADER sector index through the project's own pipeline (identical
    # parameters: EMA 5, ffill <= 10 trading days, lag 1) -> separate CSV.
    sector_map = fusion.ticker_sector_map()
    fv_lagged = build_finvader_index(scored, sector_map, equity_days)
    fv_path = RESULTS_DATA / "sector_sentiment_index_finvader.csv"
    fv_lagged.to_csv(fv_path)
    print(f"[benchmark] wrote {fv_path.relative_to(ROOT)} "
          f"({fv_lagged.shape[0]} days x {fv_lagged.shape[1]} sectors)")

    # The project's index of record is the shipped CSV; verify this run's
    # custom-lexicon scores would reproduce it before comparing against it.
    shipped_path = RESULTS_DATA / "sector_sentiment_index.csv"
    shipped = pd.read_csv(shipped_path, index_col=0, parse_dates=True)
    check_shipped_index_reproducible(scored, sector_map, equity_days, shipped)

    # Comparison tables.
    comparison = compare_indices(shipped, fv_lagged)
    comp_path = RESULTS_TABLES / "sentiment_model_comparison.csv"
    comparison.to_csv(comp_path, index=False)
    print(f"\nsentiment model comparison (lagged indices, overlapping days):")
    print(comparison.round(4).to_string(index=False))

    examples = disagreement_examples(scores, scored)
    ex_path = RESULTS_TABLES / "sentiment_disagreement_examples.csv"
    examples.to_csv(ex_path, index=False)
    print(f"\nlargest headline disagreements:")
    print(examples.to_string(index=False))

    # Figure (+ .caption.md via the shared _save helper).
    sample = (f"{equity_days.min():%d %b %Y} - {equity_days.max():%d %b %Y}")
    make_figure(shipped, fv_lagged, comparison, sample)

    print("\nDone. Wrote results/data/sector_sentiment_index_finvader.csv, "
          "results/tables/sentiment_model_comparison.csv, "
          "results/tables/sentiment_disagreement_examples.csv, "
          "results/figures/sentiment_model_comparison.png(+.caption.md).")


if __name__ == "__main__":
    main()
