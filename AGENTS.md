# AGENTS.md — Agent instructions for Project B (z5538441)

This file records how I actually direct my AI assistant on this project. It
replaces the provided stub and is part of the graded AI Workflow submission.
The full assignment rules are in PROJECT_BRIEF.md (read first), with data
details in context/. Nothing here overrides PROJECT_BRIEF.md.

## What this project is

**App name:** HyperInvest. Part B builds DFF Stations 3–4 on top of my own
Part A data foundation: out-of-sample systematic funds (equity, crypto,
combined), a VADER-based sector news-sentiment index, a sentiment-fusion
baseline, and a deployed Streamlit app.

**Product philosophy (settled, do not re-litigate):**

1. **Evidence layer, not advice layer.** HyperInvest helps novice retail
   investors do correct data analysis so they make their OWN decisions. It
   never tells users what to invest in (think Morningstar, not a
   robo-advisor).
2. **Neutrality is the professionalism.** Giving investment advice is a
   licensed activity we deliberately do not perform. This is a design
   stance, not a limitation.
3. **Teach the user to not need us.** A Practice layer — the "investment
   time machine" (Replay mode over the out-of-sample period, with Blind
   mode as a later stretch) — lets users learn from their own simulated
   decisions. No levels, no curriculum, no scores.

**Architecture:** two layers on a shared foundation.

- Invest layer (course-required journey, zero teaching friction):
  compare funds → fact sheet → set allocation → portfolio.
- Practice layer (the innovation, strictly opt-in): the time machine,
  centred on a draggable timeline slider.
- Shared: sentiment insights page, a permanent plain-English ↔
  professional language toggle (static paired strings), quiet
  concept-progress display.

## Who does what (the real workflow)

- **Kimi (Kimi Code CLI) — the sole AI agent for this folder.** Planning,
  implementation, verification, and documentation. All code, results,
  and app content in this folder are produced by Kimi at my direction.
- **The student (me) — decision layer.** I am non-technical. I approve or
  reject every material change, judge RESULTS (numbers, tables, figures,
  the running app) rather than code, and own the final interpretation,
  report wording, and submission.

History, for honesty: an earlier Part B attempt in a previous version of
this folder used a different assistant; I discarded that attempt entirely
on 2026-07-26 and restarted with Kimi as the sole agent (see
ai/prompt_log.md, Session 1). No code or results from that attempt are
present in this folder.

## Neutrality red lines (apply to every UI string and report sentence)

- State WHAT happened and WHY, with numbers; never whether it was good
  or what to do next.
- Forbidden: "best/safe/recommended/suitable" labels, scoring or grading
  any allocation, risk-questionnaire-to-fund mapping, evaluative
  reactions to user decisions ("wrong move", "better choice"), simulated
  future performance or "expected returns".
- Showing the user their own allocation's factual historical performance
  (return/vol/Sharpe/drawdown) is ALLOWED and required — the red line is
  EVALUATION, not COMPUTATION.
- Sentiment analytics must carry: "The sentiment index describes news
  tone; it is not a buy or sell signal."
- Fund names are method names only (Combined Min-Variance, Crypto
  Max-Sharpe, ...). Each fund gets one static line describing its
  construction rule plus "not a prediction or guarantee of future
  results". No evaluative nicknames ("safe", "aggressive").
- Gamification, where it exists, rewards UNDERSTANDING, never
  transactions (the Robinhood cautionary case).

## Technical rules that lose marks if broken (from PROJECT_BRIEF)

1. No look-ahead: weights and sentiment signals from past data only;
   sentiment lagged at least 1 trading day.
2. Calendars: returns computed within each panel before merging; crypto
   left-merged onto the equity calendar; annualise equity with 252,
   crypto with 365 — never mix.
3. The deployed app reads ONLY precomputed artifacts under results/. No
   optimiser runs, no VADER, no nltk import in the app. Sandbox math is
   weighted arithmetic on precomputed fund returns plus static files.
4. Required exact filenames: results/data/fund_returns.csv,
   results/data/fund_weights.csv, results/data/sector_sentiment_index.csv,
   results/tables/performance_metrics.csv.
5. Data ends 2023-12-31. No live market feed; never claim results past
   that date. Replay mode recreates the feel of travelling through time
   with historical data — that is the honest framing.
6. News dedup on ticker+date+title; keep and document genuine outlier
   returns; headlines with no next trading day are dropped, not clipped.

## How output is checked before I accept it

- Kimi self-checks (runs and verifies) before presenting anything.
  I should never be the one to discover a script fails.
- Show me results, not code: plain-language summaries, real numbers,
  tables, figures, or the running app.
- No invented values, citations, or results — every number must trace to
  a real computation on the actual project data (see
  context/verify_ai_output.md). Say "I don't know" instead of guessing.
- Correct me if my instruction is inconsistent, factually wrong, or
  creates later problems — before acting on it.

## Prompt log rules (ai/prompt_log.md)

- Log material sessions: what was asked, what the AI produced, what was
  wrong, how it was verified, what the student decided and why.
- Attribute accurately: Kimi's work is Kimi's, my decisions are mine.
- Do not rewrite earlier entries silently; add a dated correction or
  addendum when a previous statement is wrong.
