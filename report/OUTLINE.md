# Report outline — HyperInvest Part B (map of the final report)

This file began as a planning aid for the AI-written sample. It now maps the
finished `report/report.docx` — the student's own rewrite (~4,800 words of
narrative plus exhibits; limit: max 10 pages / ~5,000 words excluding
appendix and references). `report.docx` remains the editable source; submit
the exported `report.pdf`.

## Structure

1. **The funds and the backtest design** — the 12-fund matrix (3 universes ×
   4 methods) plus the sentiment-tilt variant; bullet list of the four
   construction rules; walk-forward OOS backtest (252-day window, monthly
   rebalance, rebalance day excluded, 734 / 1,187 evaluated days); 252 vs 365
   annualisation; stated decisions (long-only, rf = 0, zero transaction
   costs, convex max-Sharpe reformulation + shrinkage after the silent
   solver stall); Part A data foundation.
2. **Out-of-sample results and fund fact sheets** — Table 1, Figure 2,
   Figure 3; family decides the extremes, method shapes the ride;
   diversification helps the optimised methods but hurts equal-weight
   (crypto = 1/6 of the combined equal-weight fund); turnover evidence
   (A2, A2b — incl. months with a single coin); the fact-sheet construction
   block and sidebar explainer.
3. **The news-sentiment index** — 149,683 raw headlines → 146,830 modelled;
   VADER + 115-word custom finance lexicon (48.5% zero-score under plain
   VADER, human-approved entries); five-step pipeline (ticker-day average,
   5-day EMA, sector equal-weight, ≤10-day carry-forward, 1-day lag);
   level bias and the standardised view; finVADER validation (per-sector
   r 0.48–0.69); two documented weaknesses (negation in concessions,
   promotional vocabulary); parameter justifications.
4. **Extensions and innovations** — five extensions: the Practice time
   machine (Replay / Blind walk, storm-guard rule, 7 turbulent windows),
   the sentiment-tilt fusion with its negative result reported as found
   (Figure 5, Table 2: Sharpe 0.575 vs 0.614), the custom lexicon, the
   design system, the permanent plain/professional language toggle;
   neutrality engineered via audited static copy.
5. **The app and the investor journey** — precomputed-artifact deployment;
   turbulent-window construction (2σ rule on Combined Equal-Weight, named
   events padded ±5 trading days); learning cards (10%/20% drawdown,
   biggest single-day move, 5 pp drift, 21-day warm-up); journey:
   Compare → Inspect → Allocate → Explore, plus My Portfolio and the
   two-way bridge into the time machine (Product views 1–5).
6. **Critical reflection and recommendations** — discipline over results;
   the failed tilt's post-mortem; three stated simplifications; the
   settlement page (designed, deliberately unbuilt); three recommendations
   (transaction-cost/turnover model, nightly data refresh, mean-CVaR as a
   fifth method); process lesson: checks before models.
- **AI workflow statement** — single agent (Kimi Code CLI) under the
  student's direction; AI draft + full student rewrite; Grammarly
  disclosure; curated record in `ai/prompt_log.md`; agent file `AGENTS.md`.
- **Appendix** — A1 drawdown, A2/A2b weights, A3 sentiment benchmark,
  A4 learning cards.
- **References** — five Harvard-style entries, student-verified (VADER,
  Henry, SentiBigNomics, FinVADER, Robinhood/MSD complaint).

## Exhibit index

| Ref | Content | Source |
|---|---|---|
| Table 1 | Out-of-sample performance, all 13 funds | `results/tables/performance_metrics.csv` |
| Figure 2 | Growth of $1, one panel per family | `results/figures/growth_of_1_all_funds.png` |
| Figure 3 | Sharpe ratio by fund, ranked | `results/figures/sharpe_by_fund.png` |
| Figure 4 | Sector sentiment index, 2×5 sector grid | `results/figures/sector_sentiment_index.png` |
| Figure 5 | Fusion before vs after, growth of $1 | `results/figures/fusion_growth_of_1.png` |
| Table 2 | Fusion before vs after, table | `results/tables/fusion_comparison.csv` |
| Product view 1 | Fund shelf (marketplace) | `results/figures/app_marketplace.png` |
| Product view 2 | Fund fact sheet | `results/figures/app_fact_sheet.png` |
| Product view 3 | Allocation step | `results/figures/app_allocate.png` |
| Product view 4 | Sentiment tab | `results/figures/app_sentiment.png` |
| Product view 5 | Practice time machine (Blind walk) | `results/figures/app_blind_walk.png` |
| A1 | Drawdown, Combined Max-Sharpe | `results/figures/drawdown_combined_max_sharpe.png` |
| A2 | Weights over time, Combined Max-Sharpe | `results/figures/weights_combined_max_sharpe.png` |
| A2b | Weights over time, Crypto Max-Sharpe | `results/figures/weights_crypto_max_sharpe.png` |
| A3 | Custom lexicon vs finVADER benchmark | `results/figures/sentiment_model_comparison.png` |
| A4 | Learning cards firing in a Replay run | student-captured screenshot (embedded in report.docx) |

## Required-exhibit coverage (PROJECT_BRIEF.md, Section 5)

All present: performance-metrics table (Table 1), growth-of-$1 (Figure 2),
drawdown (A1), weights-over-time (A2 + A2b), Sharpe barplot (Figure 3),
sentiment-index series (Figure 4), fusion before/after table and figure
(Table 2 + Figure 5).

## Pending before submission

- Export `report/report.pdf` from Word (checklist hard requirement).
- Insert the live Streamlit URL and the public repo link in Section 5
  (and optionally README.md).
- Make the GitHub repo PUBLIC at hand-in and confirm the live app loads.
- Zip-time housekeeping: delete `__pycache__/`, `.DS_Store`, and exclude
  `.git/` from the zip.
