# AI Prompt Log — Part B (z5538441)

This log records the AI-assisted work on Part B: **Kimi (Kimi Code CLI) as
the sole AI agent** for this folder, and me (the student) as the final
decision-maker for every product, writing, and submission choice. It is
part of the graded AI Workflow submission.

---

## Session 1 — Fresh restart with a single agent (2026-07-29)

**What I decided, and why.** An earlier Part B attempt lived in a previous
version of this folder. That attempt was built with a different assistant
(Claude Code, Stages 1–3: Station 3 pipeline fixes, an Invest-layer app,
and a first Practice-layer build). Over the course of that work I concluded
that (a) the result diverged from my product vision in both interaction
design and visual quality, and (b) I was uncertain whether the course
permitted multi-tool AI workflows, and I was not willing to carry that
uncertainty into a graded submission. On 2026-07-26 I decided to discard
that attempt ENTIRELY and rebuild from scratch with Kimi as the sole agent.
I communicated this decision to Kimi in English from this point onward so
this log can record our sessions faithfully.

**What was kept vs discarded.**

- Discarded: ALL code, results, figures, tables, app content, report
  drafts, and the previous AI records from that attempt. The previous
  folder was renamed to an archive folder OUTSIDE this submission folder;
  nothing from it was copied into this folder except the course-provided
  files listed below. This folder — the new, clean rebuild — is the
  submission.
- Kept (course-provided starter files only, none of them produced by any
  AI assistant on my behalf): PROJECT_BRIEF.md, SUBMISSION_CHECKLIST.md,
  context/ (DATA_GUIDE.md, project_context.md, verify_ai_output.md),
  src/data_access.py, src/__init__.py, scripts/check_handin.py,
  ai/README.md, ai/prompt_log_template.md, docs/STUDENT_DEPLOY.md,
  report/OUTLINE.md, tests/test_smoke.py, requirements.txt.
- Carried over as DECISIONS (not code): the product vision and confirmed
  design parameters, which were developed in planning sessions with Kimi
  BEFORE any implementation — the HyperInvest philosophy (evidence layer,
  not advice layer; neutrality as professionalism; teach-to-graduation),
  the two-layer architecture (Invest / Practice), the fund matrix and
  backtest parameters (252-day window, monthly rebalance on the last
  trading day, long-only, rf = 0, zero transaction costs stated), the
  sentiment design (VADER + finance lexicon, EMA smoothing, 1-day lag,
  forward-fill capped at 10 trading days then neutral), the fusion
  baseline (z-scored sector sentiment tilt, α = 0.25, sector mapping
  derived from the real data at runtime — never a hardcoded sector-name
  dict), the event-driven time engine for the Practice layer (monthly
  flow, daily inside turbulent windows), the neutrality wording red lines,
  and the chart standards (one-sentence test, no overlapping date labels,
  "Other" always grey, near-uniform holdings shown as a sentence not a
  chart).

**Why the fusion and sentiment parameters above are stated so precisely:**
during the discarded attempt, independent review (by Kimi, at my
direction) had found two real defects in that attempt's code — a
hardcoded sector-name dictionary ("Comm/Telecom", "Real Estate") that
silently mismatched the real data labels ("Comm", "RealEstate"), leaving
10 of 50 equities permanently untilted, and an unlimited sentiment
forward-fill. Those findings inform the design of THIS rebuild, but every
line of code here is newly written by Kimi and will be verified against
the real data in this folder.

**Workflow going forward.** Kimi plans, implements, verifies, and
documents; I approve or reject every material change and judge results
(numbers, tables, figures, the running app), never code I cannot read.
Material sessions are logged here in English.

**Status at end of session:** clean folder created with the provided files
listed above; my own AGENTS.md written (single-agent workflow);
requirements-dev.txt, .gitignore, .streamlit/config.toml, README.md
rewritten fresh. Next: rebuild the Station 3 pipeline.

---

## Session 2 — Station 3 pipeline rebuilt and verified (2026-07-29)

**What I asked for.** After Session 1 I told Kimi to "please start
processing" — i.e. begin rebuilding the Station 3 pipeline in the new
folder. I also gave a standing instruction about this log itself: record
what I actually said and asked, do not overstate my role or Kimi's —
"you don't need to overrate what I have said, just keep it honest".

**What Kimi did.** Wrote the five pipeline modules fresh (src/etl.py,
features.py, portfolios.py, sentiment.py, fusion.py), scripts/
run_part_b.py, and tests/test_pipeline.py, using the design parameters
carried over from our planning sessions (252-day estimation window,
monthly rebalance on the last trading day, long-only, rf = 0, four
optimisers; VADER + a 90-term finance lexicon, 5-day EMA, ffill ≤ 10
trading days then neutral, 1-day lag; fusion tilt α = 0.25 with the
ticker→sector map derived from the real data at runtime). The mechanical
implementation was done by Kimi's internal coder subagent; Kimi then
reported the results to me. For transparency: the subagent was forbidden
from reading the archived folder, so no code from the discarded attempt
was reused.

**What went wrong and how it was caught (the important part).** The first
pipeline run's maximum-Sharpe optimiser silently STALLED: SLSQP failed on
all 72 equity/combined estimation windows and collapsed onto
minimum-variance weights, which would have made two "different" funds
identical. It was caught because the sanity check compared weight
differences across methods and found equal drawdowns where there should
be none — the exact "solver scaling" trap PROJECT_BRIEF.md Section 8
warns about. Kimi rewrote max-Sharpe as the convex QP reformulation
(min y'Σy s.t. μ'y=1), re-ran everything, and now saves
results/tables/weights_sanity_check.csv proving the methods differ.

**Verification before I accepted the numbers.** Kimi did not just trust
its own subagent's report: it re-read results/tables/
performance_metrics.csv and fusion_comparison.csv directly, re-ran
python -m pytest -q (11 passed) and scripts/check_handin.py. The
subagent's report contained one wrong claim — that check_handin fails on
the agent file; Kimi's re-run showed the agent-file check passes and the
only FAIL is the not-yet-built streamlit_app.py, which is expected at
this stage.

**The honest headline numbers (OOS backtest, 2021-02-01 → 2023-12-29 for
equity-calendar funds, 734 days):**
- Best Sharpe: Combined Risk-Parity 0.91; Combined Max-Sharpe 0.83;
  Combined Equal-Weight 0.76. Combined Min-Variance 0.57.
- Crypto Max-Sharpe (own 365-day calendar, 1187 days): Sharpe 0.56 with
  an -85.9% max drawdown.
- Fusion (Equity Max-Sharpe + sentiment tilt) slightly UNDERPERFORMS its
  base: Sharpe 0.575 vs 0.614, ann. return 9.2% vs 9.8%. A negative
  baseline result, which the brief treats as acceptable when reported
  honestly — no re-tuning was done to make it look better.
- Sector sentiment means are all positive (+0.13 to +0.23); only ~1-3%
  of daily readings are negative — headline tone skews upbeat, so the
  app must not present zero as the neutral midpoint.

**My decisions recorded:** proceed to rebuild streamlit_app.py (Invest +
Practice layers) next. The visual design pass stays scheduled after all
functionality is built, per my earlier decision.

---

## Session 3 — Streamlit app rebuilt (Invest + Practice layers) (2026-07-29)

**What I asked for.** After accepting the pipeline results, I told Kimi to
proceed with the remaining build steps, starting with streamlit_app.py.
My product decisions carried into this build: four tabs with a first-visit
landing; the Practice time machine centred on a DRAGGABLE TIMELINE SLIDER
directly beneath the portfolio chart (the interaction model the discarded
attempt lacked); plain-English mode as default; the measured three-tier
holdings rule; sentiment as a user-controlled multi-select; the pinned
light theme in .streamlit/config.toml; and every neutrality red line in
AGENTS.md.

**What Kimi produced.** A fresh ~1,560-line streamlit_app.py (landing +
Funds / My Allocation / Sentiment / Practice), src/events.py (four named
market events), scripts/build_event_calendar.py producing
results/data/event_calendar.csv (7 turbulent windows from a 2-sigma rule
on the Combined Equal-Weight fund plus the named events), and
tests/test_app.py (5 AppTest tests). Implementation was again done by
Kimi's internal coder subagent under a written spec; the subagent never
read the archived folder.

**Verification before I accepted it.** Kimi independently re-ran the
checks: python -m pytest -q → 16 passed; scripts/check_handin.py →
"All checks passed - ready to zip and deploy" (0 FAIL; the two WARNs are
the not-yet-written report and pycache clutter, both expected);
streamlit_app.py contains no nltk or scipy import; the app boots headless
with a clean log; the neutrality grep shows only the rule docstring and
the mandated "not a guarantee" line; every chart type was rendered to PNG
and inspected during the build.

**Two build decisions I noted for review.** (1) Navigation uses a
horizontal radio instead of st.tabs because only a radio lets the landing
buttons set the starting page programmatically. (2) The Practice
simulation calendar is the union calendar of fund_returns.csv
(2021-02-01 start bound, when all 8 funds first have returns).

**Still my job, not delegated:** the visual pass — I will click through
every tab myself in the browser (especially the Practice slider, which
was my original complaint about the discarded attempt), and I will read
every PRACTICE_COPY card and metric gloss; the wording is mine to
approve. Then: unified design polish, the report, and deployment.

---

## Session 4 — My visual review of the app; comprehension fixes queued (2026-07-29)

**What I did.** I ran the app myself and clicked through it. Overall the
visual quality matched my expectations this time. I reported three
comprehension issues and one chart issue to Kimi:

1. Combined Equal-Weight shows no "target weights per rebalance" chart
   and no Top-10 holdings — I asked why, and noted some other funds also
   lack the weights plot.
2. Some weights-per-rebalance area charts look messy (I sent the Crypto
   Max-Sharpe screenshot as an example).
3. In plain mode, a fund name like "Combined Min-Variance" still means
   nothing to a new investor — I asked for a short, simple explanation
   beside each fund.
4. I asked whether volatility figures in the funds table should carry a
   "+/-" prefix, and said the metric definitions are still not simple
   enough for people with zero financial knowledge — we cannot assume a
   new investor knows what a Sharpe ratio is.

**Kimi's analysis, which I reviewed.** (1) is the approved three-tier
rule working as designed (Equal-Weight's weights never change, so the
chart is replaced by a factual sentence) — but the sentence does not say
WHY no chart appears, so it looks broken; fix queued. (2) is partly the
honest data (max-Sharpe weights swing 0-90% monthly) and partly a
rendering flaw: weights are constant between monthly rebalances, but the
chart draws fake diagonal ramps between them; fix = step-style rendering.
(3) and (4) share one root cause: we translated labels but not meaning.
For "+/-", Kimi recommended putting it in the plain-mode header and gloss
("Yearly swing (±%)") rather than inside the numeric cells, which would
break numeric sorting; I accepted this reasoning.

**Decisions I made.** Proceed with: eight plain-language fund one-liners
(new "What does each fund do?" expander + fact-sheet line), the ± header
and gloss change, metric explanations rewritten around concrete $100
examples in everyday words, step-style area charts, and the "why no
chart" sentence. Kimi drafted all copy; final wording approval is mine
before it ships. All strings are static paired professional/plain — no
live text generation.

---

## Session 5 — Chart fixes from my visual review, implemented (2026-07-29)

**What I reported after running the app myself.** (a) The event labels on
top of the fact-sheet charts were cluttered: seven markers, three of them
repeating the generic word "Turbulent", and I could not tell which label
belonged to which dotted line. (b) The weights and holdings charts needed
a short explanation of what they represent. Earlier in the same review I
had also reported the messy weights-per-rebalance area chart.

**What Kimi implemented, with my approval:**
1. Step-style rendering for the weights area chart (weights are constant
   between monthly rebalances; the chart now reindexes to a daily grid
   and forward-fills, so each month is a flat block with one vertical
   jump per rebalance). Kimi rendered the Crypto Max-Sharpe chart before
   and after and inspected both; the zigzag is gone.
2. Tier-1/tier-2 holdings sentences now state WHY no chart is shown, so
   a missing chart no longer looks like a bug.
3. Event markers decluttered: only the four NAMED market events (Crypto
   sell-off, Bear market, FTX collapse, Banking stress) get a dotted
   line and label; generic "Turbulent stretch" windows no longer draw
   anything on Invest-layer charts (they still appear as shaded bands in
   Practice, where they drive the simulation). Verified visually: with
   the app's two-row stagger, the four labels render without collisions.
4. "How to read this chart" captions (plain mode only) under the
   growth-of-$1, drawdown, weights-area, top-10-holdings, and sentiment
   charts. All copy lives in the COPY dictionary; professional mode stays
   minimal.

**Verification:** python -m pytest -q → 16 passed. Kimi inspected the
rendered marker strip and the before/after weights chart itself.

**Still pending my wording approval:** the eight fund one-liners, the
volatility "+/-" header, and the $100-based metric explanations drafted
in Session 4.

---

## Session 6 — Session 4 copy items implemented after my approval (2026-07-29)

**What I approved.** The three copy items drafted in Session 4, unchanged:
eight fund one-liners, the volatility "+/-" approach, and the $100-based
metric explanations.

**What Kimi implemented (streamlit_app.py only, all static paired strings):**
1. FUND_ONELINER dictionary - eight standalone plain-language lines
   describing each fund's METHOD (never an outcome promise), shown in a
   new "What does each fund do?" expander under the funds table and in
   bold at the top of each fact sheet in plain mode.
2. metric_name() - in plain mode the volatility metric is named
   "Yearly swing (±%)" everywhere it appears (table header, fact-sheet
   and allocation metric rows); professional mode keeps "Annualised
   volatility". One name per metric within each mode. The ± stays out of
   the numeric cells so sorting still works.
3. "How to read these numbers" rewritten around concrete $100 examples
   ("$100 would have become about $115"; "91 cents of yearly return for
   every $1.00 of bumpiness"; "$100 invested right at the top was worth
   $14 at the worst moment") and the four fact-sheet metric glosses
   updated to match. Dollar signs are escaped (\$) so Streamlit does not
   read them as LaTeX math.

**Verification:** python -m pytest -q → 16 passed; Kimi also drove the
app via AppTest and confirmed the Funds tab renders the one-liners, the
rewritten explanations, and the ± strings with no exceptions.

**My remaining review job:** read the new wording in the running app
(my eyes, my approval of tone). Next: unified visual design pass, then
the report and deployment.

---

## Session 7 — Unified visual design pass (2026-07-29)

**What I asked for.** After my final visual review I told Kimi the app's
functions looked promising but the design was too simple, and asked what
the maximum achievable within Streamlit was. I approved Kimi's proposal:
custom typography, warm surface colours, card components, hidden
Streamlit chrome, and one unified chart style.

**What Kimi implemented (three parts, per the rubric's "colour, type, and
figure language"):**
1. .streamlit/config.toml [theme] - pinned light theme, teal primary,
   warm paper background (#FAF7F2), ink text.
2. A DESIGN_CSS block in streamlit_app.py - Google Fonts (Source Serif 4
   headings + Inter body), metric cards with hover lift, rounded buttons
   with brand hover states, card borders on expanders/dataframes/alerts,
   Streamlit chrome hidden (#MainMenu and footer; header kept
   transparent so the sidebar toggle still works).
3. apply_chart_style() - one rcParams figure language for every chart
   (no top/right spines, subtle y-grid, charcoal ink, white plot panels
   on the paper background). Charts keep DejaVu Sans because matplotlib
   renders server-side PNGs and cannot rely on a browser-loaded font
   existing on the deployment machine - chart polish comes from the
   rcParams, not the font.

**Verification.** python -m pytest -q → 16 passed. Kimi installed
Playwright Chromium (dev-only, never an app dependency), booted the app
headless, and inspected real screenshots of the landing and Funds pages:
serif headings render, paper background applies, table and expanders are
carded, the $100 explanations and ± header display correctly with no
LaTeX breakage. Final taste judgement is mine - I will review the
running app myself.

**Addendum (2026-07-29):** I reviewed the redesigned app myself in the
browser and approved the visual direction ("it looks promising"). The
design system stands as built. Next milestones: the report and
deployment.

---

## Session 8 — finVADER benchmark: our augmented lexicon, validated (2026-08-01)

**What I saw and asked.** On 01/08 I saw an ed-forum post asking the
course convener (Alex) whether the Week 9 finVADER can be used for
Project B. Alex's reply did not stop at "yes" - it encouraged designing
"your own augmented finVADER with AI". I brought the full post to Kimi
and asked: what is finVADER, and what can we take from the weekly content
into Project B to show understanding?

**What we designed together.** Kimi's analysis: our sentiment model
(VADER + a custom ~60-term finance lexicon, FINANCE_LEXICON) already IS
"an augmented finVADER of our own design" - which is exactly what Alex
encouraged and what the brief lists as an innovation example. Its
weakness was that we had never validated it against anything. So rather
than switching models, we designed this solution together: keep our
lexicon as the project's model, build the course's finVADER
(SentiBigNomics x0.1 + Henry's list) as a validation BENCHMARK on the
identical pipeline, and let the evidence decide. This is my improved
solution, designed with Kimi: validation instead of blind trust, and it
directly answers the rubric's "a validated standalone sentiment index".

**What Kimi built.** scripts/build_sentiment_benchmark.py (scores the
105,330 distinct headlines with finVADER once, reuses the project's own
etl/sentiment pipeline parameters so the comparison is lexicon-only),
producing results/data/sector_sentiment_index_finvader.csv,
results/tables/sentiment_model_comparison.csv,
results/tables/sentiment_disagreement_examples.csv, and
results/figures/sentiment_model_comparison.png. The required
sector_sentiment_index.csv was never touched. finvader was added to
requirements-dev.txt as dev-only tooling (never imported by the app);
pip resolved it with nltk 3.8.1 and the run verified our own index
rebuilds to the shipped CSV with max |diff| = 9.7e-17.

**The evidence.** Over 1,006 overlapping trading days: per-sector
Pearson r = 0.48-0.69 (ALL = 0.58); sign agreement = 94.3% overall
(86-98% by sector). The two models tell the same directional story on
~19 of 20 days and differ in magnitude/timing - our 60 full-scale terms
move compounds more than 7,300 terms scaled to a tenth. Kimi traced the
six largest single-headline disagreements to exact lexicon entries:
(a) a VADER negation-rule quirk around "despite" that the two lexicons
trigger differently; (b) promotional finance vocabulary ("dividend",
"buy") where ours reads direction better; (c) context-free Henry words
("higher", "down") firing against meaning - e.g. "profits to tumble on
higher bad loan reserves" scores negative with ours (correct) and
positive with finVADER; (d) SentiBigNomics entries neutralising strong
base-VADER valences ("cancer", "killer" ≈ 0), which happened to help
finVADER on a pharma headline where ours inherited VADER's
general-language bias. One honest weakness of OUR model is in that
table too (the OXY "despite weak crude" headline scoring positive) -
it stays in the report.

**Kimi's recommendation:** keep the custom lexicon - it tracks the
benchmark (94% sign agreement), its divergences are mostly by design and
directionally better for finance text, and switching has no supporting
evidence. **My decision: [pending my confirmation - I am reviewing the
comparison table].** Tests: 16 passed.

---

## Session 9 — Course-content sweep + Week 9 standardisation view (2026-08-01)

**What I asked.** Following the finVADER work, I asked Kimi to survey ALL
weekly course content (weeks 0-9) for anything else we could apply in
Project B to show understanding of the course.

**What the survey found (Kimi's report, reviewed by me).** Already
embodied in the project: Week 1 data-integrity checks, Week 2 figure
grammar and date-alignment rules, Week 4 in-sample portfolio construction
and √252 annualisation, Week 5's OOS engine (formation/return-date
discipline, monthly re-estimation, buy-and-hold drift - the time
machine's drift mechanic is that concept made interactive), Week 7 text
ETL and coverage analysis, Week 8 VADER discipline and lexicon
governance, Week 9 finVADER. Not yet used and worth citing in the
report: Week 3's evaluation discipline (horse race, OOS metrics), Week
5's mean-CVaR as a considered alternative, Week 7/9's coverage analysis
as the justification for a sector-level index, and Week 8's
human-approval gate as our lexicon's governance model. Also noted:
Ledoit-Wolf shrinkage and the sentiment-tilt fusion are NOT taught in
any week - they are beyond-course extensions and will be flagged as such
in the report.

**The one feature I approved adding: the Week 9 standardisation view.**
Week 9 teaches that headline sentiment sits above neutral on ~94% of
days, so the index should be standardised before a fearful day stands
out. Our own data shows the same bias (sector means +0.13 to +0.23).
Kimi added a "Compare each sector against its own usual level
(standardise)" toggle to the Sentiment tab: each sector's series is
z-scored on its own full-sample mean/std, the axis label switches to a
z-score wording, a plain caption explains "0 is that sector's usual
level; +2 or -2 is very unusual", and the raw-index positive-bias
caption is hidden in standardised view (it would confuse there, since
standardisation removes that bias by construction).

**Verification:** python -m pytest -q → 16 passed; AppTest drive of the
Sentiment tab confirmed the toggle renders and switches without
exceptions.

**Addendum (2026-08-01):** I reviewed the comparison table and Kimi's
recommendation, and confirmed: **KEEP the custom lexicon** as the
project's sentiment model. My reasons: it validates externally against
the course finVADER benchmark (94.3% sign agreement, r = 0.48-0.69 per
sector), its divergences are mostly by design and directionally better
for finance text, there is no evidence the benchmark is the better
index, and a custom augmented model is exactly what the convener
encouraged. The model's honest weak spots (e.g. the "despite" negation
quirk) stay documented for the report's limitations discussion.

---

## Session 10 — Report scaffold built to the HD rubric standard (2026-08-01)

**What I asked.** "Use the HD level marking rubric as the standard to
generate the scaffold of the report."

**What Kimi built.** scripts/build_report_scaffold.py generates
report/report.docx: the brief's six-section structure, each section
annotated with (a) a [RUBRIC] block quoting what the HD band of its
criterion actually requires, (b) an [EVIDENCE] block with the real,
verified numbers read programmatically from the committed results/ CSVs
at generation time (no hand-transcribed figures), and (c) a [WRITE]
block stating what I must argue in my own words - including where to
cite weekly course content and where to flag beyond-course extensions.
Seven exhibits are embedded (body: growth of $1, Sharpe barplot, sector
sentiment index, fusion comparison; appendix: drawdown, weights over
time, model-comparison figure), with the fusion and metrics tables
flagged for Word-table formatting. The six sections map to the rubric:
S1-2 -> Funds 15%; S3 -> Sentiment 10%; S4 -> Innovation 30%; S5 -> App
15%; S6 -> Reflection 10%; the AI-workflow statement points to this log
and AGENTS.md (20%).

**The rule that governs the next step:** the interpretation must be MY
own words (mandatory requirement). Kimi built the structure and the
evidence pack; I write the prose and delete every bracketed guidance
block before submission. Word limit 5,000 / 10 pages excluding appendix
and references. My three recommendations for Section 6 are mine to pick
(Kimi's candidates: transaction-cost model, nightly data refresh,
mean-CVaR as a 5th optimiser).

---

## Session 11 — Full AI-written draft of the report (2026-08-01)

**What I asked.** After approving the HD-mapped scaffold, I asked Kimi to
fill in the full report content first; I will then replace all of it with
my own writing.

**What Kimi produced.** scripts/build_report_draft.py generates
report/report.docx as a COMPLETE draft (~2,100 words of prose plus the
deletable [RUBRIC]/[EVIDENCE] guidance blocks, 7 embedded exhibits): six
sections mapped to the rubric criteria, every number injected
programmatically from the committed results/ CSVs at generation time, the
honest limitations included (fusion's negative result, the sentiment
model's negation/promotional-language weak spots, stated simplifications),
and a references section where every entry is marked [VERIFY] - per
context/verify_ai_output.md I must open each source myself before
submission.

**Recorded for honesty (this is the rule that governs the rewrite):**
this draft is AI-written scaffolding. The course requires the written
analysis and economic interpretation to be MY OWN words; verbatim AI
prose submitted as my reasoning is penalised. My workflow: rewrite each
section in my own words using the [EVIDENCE] numbers (which are verified
real), keep the structure, delete every bracketed block, then have Kimi
check the result against the rubric cells, neutrality rules, and word
limit. The draft deliberately sits well under the 5,000-word cap to
leave me room to expand in my own voice.

---

## Session 12 — Full-length sample report (~4,800 words) (2026-08-01)

**What I asked.** The Session 11 draft was a short skeleton; I told Kimi
I wanted a full-length sample report, not a simple draft, and I will
rewrite it myself.

**What Kimi produced.** scripts/build_report_full.py regenerates
report/report.docx as a ~4,800-word complete sample report (words counted
at generation; excludes appendix references list). All figures are
computed from the committed results/ CSVs at generation time - including
derived quantities like each fund's growth-of-$1 endpoint and the exact
dates of the worst drawdowns - so no number in the prose is
hand-transcribed. Expansions over the Session 11 skeleton: the Part A
data-foundation paragraph in S1 (row counts, duplicate counts, the kept
outliers including the 9 March 2020 -52% energy-stock day); a fact-sheet
walk-through and the Sharpe-ordering observation in S2; the EMA-5 /
ffill-10 parameter justifications and the sector-profile reading in S3;
the two honesty-engineering paragraphs (data boundary, audited copy
structure) in S4; the landing-gate, language-toggle and automated-testing
paragraph in S5; and a process reflection (checks before models; design
before code) in S6.

**The standing rule, recorded again because it matters most here:** this
is an AI-written SAMPLE for me to rewrite. The course penalises verbatim
AI prose submitted as my own analysis. My job: rewrite every section in
my own words, keep the verified numbers, delete the bracketed blocks and
the STATUS banner, then have Kimi audit my version against the rubric.

---

## Session 13 — Design refinement pass (2026-08-01)

**Context (integrity decision recorded):** I asked Kimi whether we could
reference public GitHub repos for design inspiration. Kimi's analysis
said it is allowed (the brief only forbids reading another student's
project), but I decided NOT to use any external repo references - zero
tolerance on integrity risk. The design work in this session is Kimi's
own judgement plus the official Streamlit documentation only.

**What I asked for.** After reviewing the app I told Kimi the design was
still too simple. Kimi did a first-person review of every tab (its own
screenshots) and reported six issues by priority; I approved the fix
plan.

**What Kimi implemented (visual only; no data, chart-logic, or copy
changes):**
- Landing hero: teal kicker ("Evidence, not advice"), large serif
  display title, subtitle, and the two entry choices as large card
  buttons with hover lift - the page no longer reads as empty.
- Sidebar identity: HyperInvest wordmark + tagline, language toggle,
  then data coverage, assumptions, and the neutrality line - the sidebar
  was previously just a lonely radio.
- Practice chart: the boxed default-matplotlib legend (which collided
  with the "You are here" marker) replaced with a frameless legend
  pinned upper-right.
- Pill navigation: the section radio now renders as a segmented pill
  control with a teal selected state.
- Sentiment disclaimer restyled from default Streamlit blue to the
  themed neutral card.
- My Allocation: a teal progress bar now shows allocation completion at
  a glance; metric-value font size reduced to 1.6rem after Kimi's
  screenshot review caught "01 Feb 20..." truncating inside the card.

**Verification:** 16 tests pass; Kimi screenshot-reviewed the landing,
Funds, and Practice pages itself, twice (the second run caught and fixed
the truncation). My own review is next.

---

## Session 14 — Progressive-disclosure redesign (text density) (2026-08-01)

**What I reported.** After reviewing the redesigned app I told Kimi it
was still too text-heavy: real products are clean, with everything in
its place, and the amount of visible content made the journey confusing.

**Kimi's diagnosis, which I approved:** we had answered "novices need
explanation" by putting ALL the explanation ON the page - two auto-opened
text walls plus a caption under nearly every component. The fix is
progressive disclosure: nothing visible unless needed for the immediate
decision; explanations live one click away.

**What Kimi implemented (structure only; no data or wording changes):**
- Four global rules applied app-wide: captions that answer "what is
  this" moved into info popovers/tooltips; expanders default CLOSED
  (reversing the earlier plain-mode auto-open decision); max one visible
  supporting line per component; duplicate captions merged.
- Funds: sample period + backtest basis moved into an "ⓘ About the data
  & assumptions" popover; "What does each fund do?" and "How to read
  these numbers" now default-collapsed; fact-sheet metric glosses moved
  into the cards' ⓘ tooltips; construction/universe details moved into a
  collapsed "How this fund is built" expander. The one-line neutrality
  captions (sorting note, guarantee line inside the expander) were kept
  deliberately - they are safeguards, not clutter.
- My Allocation: the two stacked chart captions merged into one; the
  progress bar kept.
- Sentiment: smoothing explanation moved into the slider's ⓘ tooltip;
  positive-bias + start-date captions folded into a collapsed "ⓘ About
  this index" expander; the mandatory disclaimer stays visible by design.
- Practice: the long slider explanation moved into the slider's ⓘ
  tooltip; status-card glosses moved into card ⓘ tooltips.

**Verification:** 16 tests pass; Kimi screenshot-reviewed Funds,
Sentiment and Practice after the change - each page now reads as
heading + one line + the interactive core. My own visual review follows.

---

## Session 15 — Sidebar collapse, event-label alignment, real language modes (2026-08-01)

**What I reported after my review.** (1) The sidebar was still full of
content. (2) On the fact-sheet charts, the "Banking stress" event label
sat alone on a second row - misaligned with the other event names.
(3) The language toggle felt useless - flipping modes barely changed the
page. I asked Kimi whether that is really a strong feature.

**Kimi's analysis and fixes (approved by me):**
1. Sidebar: Data + Assumptions now sit inside a collapsed "ⓘ About the
   data & assumptions" expander; the sidebar shows only the brand, the
   language toggle, and the one-line neutrality statement.
2. Event labels: root cause was a conservative text-width estimate
   (4.0pt/char) that staggered labels which actually fit. The estimate
   was tightened (3.4pt/char) and the layout logic rewritten: one clean
   row when labels fit; a DELIBERATE 0-1-0-1 checkerboard when they
   genuinely collide (a lone second-row label reads as a bug; an
   alternating pattern reads as design); numbered markers with a caption
   as the dense fallback. Verified visually on the Combined Equal-Weight
   chart.
3. Language toggle - Kimi agreed with me and called it design debt:
   Session 14's progressive disclosure had hidden the plain-English
   extras, so the modes looked identical. The toggle is the product's
   graduation story, so the modes were made visibly different again:
   plain mode now uses everyday metric names everywhere (Yearly return /
   Yearly swing (±%) / Return per swing / Worst fall vs Annualised
   return / Annualised volatility / Sharpe ratio / Maximum drawdown),
   and auto-opens "What does each fund do?" while professional mode
   strips the teaching layer entirely. Verified with side-by-side
   screenshots of both modes.

**Verification:** 16 tests pass; Kimi inspected rendered screenshots of
both language modes and the fixed label strip. My review is next.

---

## Session 16 — "News exposure": connecting allocation and sentiment (2026-08-11)

**What I asked.** I told Kimi the Allocation and Sentiment tabs felt
disconnected: individually good, but nothing showed how news relates to
where a user's money sits. I explicitly allowed hardcoding if needed to
ship a good product, and approved Kimi's plan.

**What Kimi built (My Allocation, after a complete blend):** a "Your mix
and the news" panel - horizontal bars showing the blend's sector shares
(computed from each fund's latest target weights x the user's fund
percentages), with each sector's latest news tone beside it as a
full-sample z-score label ("about usual" / "unusually positive" /
"unusually negative"). Crypto has its own grey bar marked "no news data",
because headlines cover only the 50 equities - a data fact we state
rather than hide. The caption carries the neutrality line: "This
describes the past; it does not predict returns, and it is not advice."
No red/green colouring anywhere in the feature: the tone marker is a
teal dot on a grey scale, so colour carries no judgement.

**On the hardcoding question (recorded because it was my explicit
decision):** I allowed hardcoding. Kimi's counter-proposal, which I
accepted: the 50-ticker sector map is hardcoded BUT verified against the
real hosted data at build time (50/50 exact match) and guarded by a new
test (test_sector_map_matches_real_data) that reloads the data and fails
loudly if the map ever drifts. Hardcode + tripwire, not hardcode + hope.

**Bug caught by Kimi's own screenshot review:** the My Allocation value
caption's dollar signs were being swallowed by markdown math mode
("$1,000 ... $992" rendered as "1,000 ... 992"). Escaped; verified fixed.

**Verification:** 18 tests pass (including the new tripwire and
exposure-math tests); Kimi inspected the rendered panel itself.

---

## Session 17 — Full 4x3 fund matrix (2026-08-11)

**What I noticed and asked.** The fund shelf was asymmetric: 4 combined
methods, 2 equity, 1 crypto. I asked whether that was a design or a
flaw, and how we would explain it in the report.

**Kimi's honest answer, which I accepted:** it was an inherited default,
not a design - no principled explanation existed, so the fix was cheaper
than the justification. I approved the full 4x3 matrix: every method
(Equal-Weight, Min-Variance, Max-Sharpe, Risk-Parity) across every
family (Combined, Equity, Crypto) = 12 funds + the tilt variant.

**What Kimi implemented.** src/portfolios.py FUND_METHODS expanded to 12
funds; full pipeline rerun (existing funds' results verified unchanged);
app metadata for the 5 new funds (one-liners, construction lines,
universe text); PERIODS_PER_YEAR now derived from fund names so a future
matrix change cannot silently misalign the 252/365 split; the Funds
heading changed to "The fund shelf" (count-free, so it never goes stale
again). Two bugs caught by the expanded tests: "Split evenly" produced
100.1% for 13 funds (the first fund now takes the rounding remainder),
and a hardcoded 8-fund assertion in the test suite (now count-agnostic).
A .DS_Store found by check_handin was removed.

**The result changed the story (recorded honestly):** Crypto
Min-Variance posts the best Sharpe on the shelf (1.28; 86.9% ann.
return, -71.1% max drawdown), and adding crypto IMPROVED every optimised
method but made equal-weight WORSE (0.86 equity-only -> 0.76 combined).
The report's Section 2 narrative was rewritten to match the new
evidence ("family decides the extremes, method shapes the ride;
diversification is not a free lunch without a sizing rule; no single
measure ranks the shelf"). All numbers in report/report.docx regenerate
from the committed CSVs; narrative claims were reviewed against the new
metrics table.

**Verification:** 18 tests pass; check_handin clean; Kimi inspected the
rendered 13-row marketplace table.

---

## Session 18 — Asset-family grouping for allocation inputs (2026-08-11)

**What I asked.** After the matrix expansion, I pointed at the allocation
input list and asked for family grouping by background colour, so users
can see which funds belong together (I noted my example colours were
illustrative, not the final palette).

**What Kimi implemented.** Allocation inputs (My Allocation and the
Practice setup share one renderer now) are grouped into four tinted,
labelled containers: Combined in soft teal, Equity in soft slate, Crypto
in soft gold, the Sentiment Tilt fund in soft maroon (marking it as "the
experiment"). Each container carries a small family label ("Combined -
shares + crypto together", "Crypto - coins only", ...). The family of a
fund is derived from its name, so a future matrix change cannot
misalign the grouping; session-state keys are unchanged, so no logic was
touched. Colours are organisational only - no red/green value judgements,
consistent with the neutrality rules.

**Verification:** 18 tests pass; Kimi inspected the rendered allocation
page (all four tinted groups present and correctly populated).

---

## Session 19 — Matrix explainer replaces the 13-bullet list (2026-08-11)

**What I reported.** With 13 funds, the "What does each fund do?"
expander had become a wall of near-identical bullets that would
overwhelm new investors.

**Kimi's proposal, which I approved:** stop listing funds and teach the
structure instead - the 13 one-liners were ~90% repetition because every
fund is one family x one method. The expander now shows two short lists
(Step 1 - what to hold: Combined/Equity/Crypto; Step 2 - how it is
built: Equal-Weight/Min-Variance/Max-Sharpe/Risk-Parity) plus one closer
line explaining that every fund is a combination and the Tilt fund is
the experiment. The per-fund one-liners still appear in bold on each
fund's own fact sheet, so no content is lost. This also makes the app
tell the same story as the report's Section 1 (the matrix as a
comparison instrument).

**Verification:** 18 tests pass; Kimi inspected the rendered expander.

---

## Session 20 — Blind walk mode for the Practice time machine (2026-08-11)

**What I reported.** Replay mode shows the full timeline and trend up
front, so the user already knows what happens - "that isn't really
practice". I asked for a mode that brings the user back into the
timeline to experience events and sentiment as they happen, and I asked
what the sentiment z-scores are FOR ("then what?").

**Kimi's answers, approved by me.** (1) This is the Blind mode from our
original two-mode design, deferred as the stretch goal - my usage
confirmed it was needed, so we built it. (2) Sentiment is context, not a
signal: the honest answer to "then what" is "nothing automatically -
news tone and prices are different things", and our own Tilt fund's
negative result is the standing proof. The Tilt fund stays on the shelf
as "the experiment with its test result attached" - the test killed the
CLAIM, not the fund.

**What Kimi built:**
- Mode choice at setup: Replay (full timeline) vs Blind walk (future
  hidden), with neutral descriptions of each.
- Blind walk: the chart draws only up to the current date (no
  continuation dashes, no future window shading, no unreached event
  markers); the slider travels only within the revealed range; forward
  movement is stepwise - monthly in calm periods, landing on (never
  over) a turbulent window's start, then daily inside the window.
- "The news mood right now" panel: the top sectors of the user's current
  mix with tone z-scores computed from PAST-ONLY expanding statistics,
  and fund weights as of the simulation date - no look-ahead in the
  lesson itself.
- The debrief at the end of the data: the user's path vs never touching
  the starting mix (buy-and-hold counterfactual), decision count, and
  factual numbers only - "what it means is yours to judge".
- Bug caught by screenshot review: Streamlit's select_slider crashes
  with a single option (the very start of a blind walk reveals exactly
  one date); the slider now renders only when 2+ dates are revealed.

**Verification:** 20 tests pass (new: blind-step rules - monthly in
calm, land on window starts, daily inside windows, stop at data end -
and the debrief counterfactual math). Kimi screenshot-verified a live
blind walk reaching the May 2021 crypto sell-off window.

---

## Session 21 — Blind-walk early-game fixes (2026-08-11)

**What I reported after playing the blind walk.** (1) At the very start
the chart was one dot on an empty canvas with the marker overlapping
everything. (2) A "large single-day move" card fired on 1-2 Feb -
before I had any context, which made no sense to me.

**What Kimi found and fixed (three items, the third found while fixing
the first two):**
1. Chart at walk start: the blind chart's x-axis view is now capped ~60
   days ahead of the frontier and grows as you travel, instead of
   showing one point on a 3-year empty canvas. Verified visually.
2. Premature cards: threshold cards (drawdown -10%/-20%, large
   single-day move) now have a warm-up - they cannot fire in the first
   21 trading days of a run, because an alert before the user has any
   baseline is noise, not teaching. Window-entry and end-of-data cards
   stay ungated.
3. A real simulation-semantics bug: the engine applied the start date's
   own return on day 1 (the portfolio showed $1,015 immediately after
   investing $1,000) and, more subtly, applied same-day returns to
   same-day decisions (a mild look-ahead inside the sandbox). The loop
   now compounds first and applies decisions at the close of their date:
   money earns a return only for days it was actually invested, and a
   decision earns from the NEXT day. Verified numerically: day 1 =
   exactly the amount paid in; day 2 matches a hand computation to the
   cent (1000 x 1.02140 = 1021.40).

**Verification:** 20 tests pass; day-by-day values cross-checked by hand.

---

## Session 22 — User-paced blind travel (pace switch + guarded jump) (2026-08-11)

**What I reported.** In blind walk, every forward click jumps a month -
a user who wants day-by-day travel loses that experience, and a
"large single-day move" card after a monthly jump felt wrong. I also
asked whether a user should be able to jump a whole year.

**Kimi's plan, approved by me:** three gears of travel (day by day / a
month at a time / jump to a date), all governed by one rule - any
forward travel stops at the next turbulent window's start ("you can
skip a calm year, but a storm still finds you"). Plus one honesty fix:
the big-day card now checks the whole travelled STRETCH since the last
check and names the true biggest day in it, instead of checking only
the landing day after a jump.

**What Kimi implemented.** A pace radio and a jump-to-date input on the
blind walk; _blind_next is pace-aware (daily inside windows regardless
of pace); _blind_jump_target enforces the storm guard for jumps (within
the revealed range, jumping back is free travel and reveals nothing);
the stretch-based card. The 21-day warm-up stays.

**Verification:** 22 tests pass (new: day-pace stepping, jump stops at
window start, jump lands on target in calm stretches, the card names
the stretch's true biggest day). End-to-end UI check: jumping to
1 Sep 2021 landed on 05 May 2021 - the crypto sell-off window start -
exactly as the storm rule requires.

---

## Session 23 — Dollar-based allocation (2026-08-11)

**What I asked.** The percentage-based allocation confused new investors
- entering weights for 13 funds and hitting "must equal exactly 100%" is
mechanic-thinking, not money-thinking. I proposed entering dollar
amounts with the percentage shown, and asked Kimi's opinion first.

**Kimi's analysis, which I accepted.** Yes, with one caveat: percentages
must stay VISIBLE (just not editable), because blended performance is
proportional - hiding percentages would lose the dollar-to-share link we
want novices to absorb. Boundary noted: we can simplify mechanics, never
choices (no pre-selected "beginner funds" - that would be curation and
break neutrality).

**What Kimi implemented (all three allocation surfaces):**
- Inputs are now dollar amounts ($0 min, step $50); each label shows the
  live share ("Combined Equal-Weight - 7.6% of your mix").
- The "must equal exactly 100%" constraint is gone everywhere - any
  positive total works, proportions are derived, and no error state
  exists. The total line reads "Total: $X".
- The principal is the dollar total (the separate "investment amount"
  input is gone from My Allocation; the Practice starting amount is the
  mix's total).
- Practice mix-change uses dollars too, defaulting to the current
  effective dollars; amounts express proportions applied to the
  portfolio's current value (a caption says so).
- Split evenly splits the current dollar total ($1,000 if empty), first
  fund takes the rounding remainder.

**Verification:** 22 tests pass; Kimi screenshot-verified the rendered
allocation page (live shares in every label, family tints intact).

---

## Session 24 — Daily summary digest (2026-08-11)

**What I asked.** After reviewing the improved Practice mode, I asked
for a daily summary - each step showed a chart point but no digest of
the day.

**What Kimi built.** A "Today: {date}" panel in both Practice modes,
placed directly under the travel controls: the market move in dollars
and percent ("Your portfolio rose $7 (+0.7%) to $1,080"), the biggest
single-fund driver (yesterday's effective weight x today's fund return,
in percentage points), and any cash flow from decisions dated that day.
Directions are factual (rose/fell), never evaluative. Day one reads
"Day one: you set off with $1,000." The digest uses the market-only
daily return, so deposits/withdrawals never masquerade as market moves.

**Verification:** 22 tests pass; Kimi screenshot-verified the panel
rendering inside a live day-by-day blind walk.

---

## Session 25 — Amount-first flow + restart walk (2026-08-11)

**What I asked.** (1) Reorder the allocation flow: enter how much to
invest FIRST, then distribute - "Split evenly" inventing $1,000 out of
nowhere was backwards. (2) A reset for blind walk: once you jump forward
you cannot un-see the future, so a misclicked pace choice could not be
undone. I also proposed preference-based fund RECOMMENDATIONS, which
Kimi refused: a preference-to-fund mapping is investment advice and
violates the neutrality red line we set at the start. I accepted the
refusal - the neutral alternative (user-driven sorting, teaching what
each method means) stays.

**What Kimi implemented:**
- "Amount to invest ($)" field now sits above the fund inputs in both My
  Allocation and Practice setup; Split evenly divides that amount (first
  fund takes the rounding remainder), and the total line always follows
  the per-fund boxes.
- "Restart walk" button in the blind-walk controls: same start date,
  mix and mode, but the frontier returns to day one, later decisions
  cleared, fired cards forgotten - the only true way to re-live a
  stretch, since dragging back cannot un-reveal the future.

**Verification:** 23 tests pass (new: restart re-hides everything and
clears decisions/cards). Kimi screenshot-verified both surfaces; the
stretch-based big-day card was observed naming the true biggest day
(23 Feb 2021) after a monthly jump.

---

## Session 26 — Widget-state persistence across tab switches (2026-08-11)

**What I reported.** Starting a blind walk, switching to another section
and coming back reset the walk to day one - a bad experience for anyone
who just wants to check another page mid-walk.

**Kimi's diagnosis.** A genuine Streamlit behaviour, not our logic: a
widget's session-state entry is deleted whenever the widget is not
rendered in a run, so unmounting the Practice tab discarded the walk's
position (and, the same class of bug, My Allocation's entries when
leaving that tab). The simulation itself (decisions, frontier) survived
because it is ordinary session state, not widget state.

**The fix.** A widget-state mirror: after each run, the values that
matter (walk position, pace, jump date, allocation amounts, setup
choices) are copied into an ordinary session key, which survives;
before rendering, any widget keys discarded while their tab was
unmounted are restored. Intentional resets (Start again) clear the
mirror entry too, so a reset can never be resurrected by the restore
logic.

**Verification:** 24 tests pass (new: position and simulation survive a
round-trip to another tab and back).

---

## Session 27 — The amount field becomes the contract (2026-08-11)

**What I reported.** I entered $10,000 as my amount, placed only $5,000
in one fund, and the plot and results popped out before I had finished -
"doesn't make sense". I asked whether that was design or an issue.

**Kimi's answer, which I accepted.** A design flaw introduced when the
"any positive total works" rule replaced the 100% constraint: the app
treated "placed so far" as complete, while the amount-first field had
created a contract in the user's head ("I said $10,000; I'm not done").
The fix makes the amount field the contract: a neutral progress line
("Placed: $5,000 of $10,000 - Not yet placed: $5,000"), and results plus
the plot appear only once the full declared amount is placed; over-placement
gets the mirror note ("Over by $500 - reduce a fund or raise the amount").
This constraint is acceptable where the 100% rule was not, because the
target is the user's own declared number, not abstract arithmetic.

**Scope:** My Allocation and the Practice setup (same field, same rule).
The mid-walk mix-change keeps the proportion model (any positive total,
applied to current value) since no declared amount exists there.

**Verification:** 24 tests pass (the gate test now also asserts a
partially placed amount keeps Start disabled); Kimi screenshot-verified
the partial state - no results render until the amount is fully placed.

---

## Session 28 — My Portfolio rebuilt (2026-08-11)

**What I asked.** The My Portfolio section was just text receipts -
"useless". I asked Kimi what the current design was, what it was
supposed to be, and how to improve it.

**Kimi's assessment, which I approved.** As built, it was a receipt log
("Saved at ... - fund percents"), not a portfolio. The original vision
was the destination of the investor journey and the bridge between the
Practice and Invest layers; neither was being done.

**What Kimi implemented:**
1. Receipts became CARDS: each saved mix shows its name, timestamp,
   amount, top-3 funds, and its four blended metrics computed from
   precomputed returns - a mini fact sheet for the user's own mix.
2. "Load into editor" refills the allocation boxes with a saved mix
   (scaled to the current amount field), so saved ideas can be tweaked
   instead of rebuilt.
3. A side-by-side comparison table appears when 2+ mixes are saved -
   factual columns only, no ranking, with the caption "the differences
   come from the mixes, nothing else".
4. The Practice bridge: "Save this starting mix to My Portfolio" in the
   decision history and on the blind-walk debrief, carrying the mix's
   own start amount.
- A flaw found by the new tests: the saved section vanished when the
  editor's amount gate was unsatisfied (the early return skipped it).
  The portfolio now renders regardless of editor state.

**Verification:** 26 tests pass (new: save + load-back round-trip,
practice bridge saves the start mix); Kimi screenshot-verified the
two-mix comparison table and cards.

---

## Session 29 — "Your whole portfolio" aggregate view (2026-08-11)

**What I asked.** With several saved mixes (an even split, an all-in
single fund, etc.), there was no way to see the TOTAL performance of the
whole portfolio - each mix was only evaluated separately. I asked for
the combined view.

**What Kimi built.** When 2+ mixes are saved, a "Your whole portfolio"
block now heads My Portfolio: total placed across the mixes, the four
metrics computed on the AGGREGATE value path (each mix's dollar growth
summed day by day), and a growth chart against a total-placed reference
line, captioned "Historical only - not a projection". Order in the
section: aggregate view, then the side-by-side comparison table, then
the per-mix cards. A duplicate COPY key (total_line reused for two
different captions) was caught by a KeyError in the tests and renamed;
an AST-level duplicate-key guard now runs as a check.

**Verification:** 27 tests pass; Kimi screenshot-verified the aggregate
chart, metrics, compare table and cards together.

---

## Session 30 — Editor auto-clears after saving a mix (2026-08-11)

**What I reported.** I saved a $2,000 evenly-split mix, then tried to
build a second one ($1,900 all-in on one fund) - but the app showed
"Placed: $3,900 of $1,900" and I could not complete it. The first mix's
amounts were still in the boxes and my new entries accumulated on top.

**Kimi's diagnosis and fix.** Not a calculation bug - a missing workflow
step: the editor never cleared after a save, so building mix #2 started
from mix #1's leftovers unless the user manually hit Reset to zero. Now
saving a mix COMPLETES it: the editor auto-clears to zero (with the
"Saved to My Portfolio" toast confirming), and the next mix starts from
a clean sheet. Revisiting a saved mix stays deliberate via "Load into
editor".

**Verification:** 27 tests pass (the save/load test now also asserts the
editor is zeroed after saving).

---

## Session 31 — The reverse bridge: saved mix -> time machine (2026-08-11)

**What I asked.** Can a user invest MORE into a previously saved mix, or
take money out of it, like real apps allow? I asked for Kimi's thinking
first.

**Kimi's analysis, which I accepted.** A live "current balance" would be
fiction (the data ends 2023-12-31), but the need is real - and the
honest mechanism already exists: the Practice layer's add/withdraw at
any date. So the answer is the reverse bridge rather than fake balances.
What was refused and recorded: any "live balance" framing.

**What Kimi implemented.** Each saved-mix card now has "Test in the time
machine": it loads the mix (its own amount + proportions) into the
Practice setup and navigates to the Practice tab; nothing starts until
Start travelling. From there the user can add or withdraw money at any
date and see what that would have done. The two-way loop is now
complete: My Allocation -> save to My Portfolio -> test in the time
machine -> save the starting mix back to My Portfolio.

**Verification:** 28 tests pass (new: the reverse bridge loads the mix
into the setup and lands on the Practice tab).

---

## Session 32 — News exposure follows the money (2026-08-11)

**What I asked.** After building multiple portfolios, I asked what the
sentiment display actually shows - and expected each mix to have its own
sentiment view. Kimi confirmed the gap: the exposure panel existed only
for the editor's current mix, and My Portfolio (cards, compare table,
aggregate) had none. Also clarified for me: news covers SECTORS, not
funds, so the honest unit is "the tone of the sectors your money sits
in".

**What Kimi implemented (approved plan: exposure follows the money):**
1. The whole-portfolio aggregate view now has its own news-exposure
   panel - sector shares dollar-weighted across ALL saved mixes, with
   latest tone labels.
2. Every saved-mix card carries a compact tone line: its top 2 sectors
   and their latest tone, dated ("as of 29 Dec 2023"), with an explicit
   "no news tone" note for share-free mixes.
3. Nothing became a time series, deliberately: a tone-over-time chart
   for a mix would imply a signal, and our own fusion result already
   showed that framing fails. Snapshots stay context, never prediction.

**Verification:** 28 tests pass; Kimi screenshot-verified the aggregate
panel and per-card tone lines.

---

## Session 33 — Three review fixes: reset, dead chart, weights chart (2026-08-11)

**What I reported.** (1) "Reset to zero" cleared the fund boxes but not
the Amount-to-invest field. (2) An all-crypto mix shows a giant grey
"no news data" bar - a useless plot. (3) The stacked-areas weights chart
still looked bad: the grey "Other" band dominated diversified funds and
squashed the named holdings into unreadable strips.

**What Kimi fixed:**
1. Reset now clears the boxes AND the amount field (a true clean slate),
   with guards so a 0/0 state shows a neutral "enter an amount" caption
   instead of opening the results gate, and a 0-amount Practice setup
   cannot start.
2. A mix with no equity exposure now gets a factual sentence ("this mix
   holds no shares - headlines cover the 50 US shares only, so there is
   no news tone to show") instead of the grey-wall chart. The rule
   holds: a chart must earn its place by carrying information.
3. The weights chart drops the "Other" band entirely and fits the y-axis
   to the top-5 holdings it actually shows; the caption now states the
   remainder is spread across all other assets. Verified visually on
   Combined Min-Variance - the bands now fill the canvas and the
   composition shifts are clearly readable.

**Verification:** 29 tests pass (new: all-crypto mix gets the sentence).

---

## Session 34 — Per-mix performance view inside each card (2026-08-12)

**What I reported.** A saved mix card showed four numbers but there was
no way to see the mix's full performance. What I wanted: click a mix and
see everything, in place.

**What Kimi built.** Each saved-mix card now has a "View performance"
expander that opens INSIDE the card: that mix's own value-over-time
chart (its amount x its blend, with the starting-amount reference line
and the full period caption - "ranged from $988 to $2,523 and ended at
$2,263; assumes you held; not a projection"). No navigation away, no
lost context. The same render path as the editor's chart, so numbers
always agree.

**Verification:** 29 tests pass; Kimi screenshot-verified the expanded
card rendering the correct chart.

---

## Session 35 — Sentiment panel inside the per-mix performance view (2026-08-12)

**What I asked.** The per-mix "View performance" expander showed the
value chart but no sentiment view. I asked for it to be added, with
flexibility: crypto-heavy mixes without news coverage should not render
an empty chart.

**What Kimi implemented.** The "Your mix and the news" exposure panel
now renders inside the card's expanded view, beneath the value chart.
The existing earn-its-place rule applies unchanged: a mix with no
equity exposure gets the factual sentence ("headlines cover the 50 US
shares only") instead of a chart. The panel keeps its neutrality
caption everywhere it appears.

**Verification:** 29 tests pass; Kimi screenshot-verified the expanded
card showing both the value chart and the exposure panel.

---

## Session 36 — Test the WHOLE portfolio in the time machine (2026-08-12)

**What I reported.** My Allocation lets me build several saved mixes and
see the combined whole-portfolio view, but Practice could only test one
saved mix at a time - the aggregate portfolio was not testable.

**What Kimi built.** A "Test my whole portfolio in the time machine"
button on the aggregate block: all saved mixes are combined
dollar-weighted across funds and loaded into the Practice setup with the
combined amount, so the entire portfolio becomes walkable (blind walk,
add/withdraw, debrief). The loop is now complete at both levels: single
mix -> Practice, and whole portfolio -> Practice.

**Verification:** 30 tests pass (new: the aggregate bridge loads the
combined amount and lands on the Practice tab).

---

## Session 37 — End-of-walk crash fix (2026-08-12)

**What I reported.** (1) After travelling a whole blind walk to the end,
the app crashed with a StreamlitAPIException (the jump-to-date widget's
value 2023-12-31 exceeded its max 2023-12-29). (2) The tab-switch reset
seemed to be back.

**Kimi's diagnosis.** One bug, not two. The union calendar runs to
2023-12-31 (crypto trades the year-end weekend), so a completed walk's
frontier sat past the widget's cap and every Practice render threw. The
state mirror saves at the end of a run - and a crashed run never reaches
that save, so the last saved position was stale (the start), which is
what looked like the tab-switch regression returning. Fixed: the jump
field now allows the true data end and clamps its default into range.

**Verification:** 31 tests pass (new: reaching the data end in blind
mode does not crash).

---

## Session 38 — The real tab-switch fix (2026-08-12)

**Correction to Session 37 (logged as a dated correction, per the log
rules).** Session 37 claimed the tab-switch reset was a shadow of the
end-of-walk crash. The student re-tested and proved that wrong: the
reset persisted with the crash fixed. Kimi then reproduced it live
(blind walk to 01 Apr, switch to Sentiment, return -> position reset to
01 Feb; replay mode unaffected) and instrumented the running app.

**Root cause (verified from the live state trace, not theory).** The
mirror held the correct position, but on tab remount Streamlit's widget
lifecycle overwrote the restored slider value with the widget's
first-ever default (the start date). The earlier on_change-based jump
widget contributed a second, spurious-jump path. AppTest never deletes
unmounted widget state, which is why the unit tests passed while the
real app failed - the lesson: widget-state behaviour must be verified
against the real server, not only AppTest.

**The fix (structural, not patched).** The walk position now lives in
the sim dict as sim["view_date"] - plain session state with no widget
lifecycle - and the timeline slider is a STATELESS view of it (value
read from view_date each run; drags written straight back). The jump
field's on_change was replaced by an explicit "Jump" button, so no
state reconciliation can fire a phantom jump. The end-of-walk clamp
from Session 37 stays.

**Verification:** 31 tests pass; the failing Playwright scenario now
preserves the position (01 Apr -> Sentiment -> 01 Apr), and a jump to
Sep 2021 still lands on 05 May 2021 (storm rule intact).

---

## Session 39 — My triage policy for the rest of the project (2026-08-12)

**My decision, stated to Kimi:** from this point, only bugs or flaws that
cause real harm - a function not working as intended - get fixed.
Everything else (minor visual imperfections, nice-to-have polish,
small UX frictions that do not break a flow) is no longer fixed in code;
it becomes material for the report's critical-reflection section.

**Why (my reasoning):** it stops the endless polish loop, and the
rubric's reflection criterion rewards honest "what didn't work and why",
not a pretend-perfect product.

**Agreed operating rule from here:** when I raise an issue, Kimi first
classifies it as FUNCTION-BREAKING (fix now) or REFLECTION-MATERIAL
(record for the report), and tells me which before doing anything.

---

## Session 40 — Full stress test (2026-08-12)

**What I asked.** A full recheck of the product: debug and stress-test
extreme and rare situations so the product holds up beyond happy paths.

**What was done (Kimi commissioned a dedicated test pass; I reviewed its
findings).** 32 new tests in tests/test_stress.py covering engine edge
cases (withdraw more than the balance, withdraw EVERYTHING, add after
total withdrawal, start at the last day of data, travel back over
decisions and re-replay for determinism, month-end boundaries, jump
guards) and UI flows (amount-gate states, remove/reload mixes, restart
twice, walk to the data end and keep pressing forward, language switch
mid-walk, all 13 fact sheets, sentiment extremes).

**The one real bug found and fixed:** forcing a zero-total mix change
(possible only by bypassing the disabled button) appended NaN weights
and silently poisoned every later value in the walk with NaN. Fixed
with a 7-line guard in _apply_mix; regression test added. Two initial
"failures" were test-script bugs, not app bugs - recorded as such.

**Reflection material for the report (cosmetic, deliberately not
fixed):** "$0 rose $0" wording on a zero-balance day; negative net
paid-in renders as "$-146"; the all-crypto caption shows on an empty
portfolio; duplicate mixes save without a dedup note.

**Verification:** 63 tests pass (Kimi re-ran independently);
check_handin zero FAIL. Chart pixels and the deployed environment
remain visual/manual checks.

---

## Session 41 — UX simplification pass (2026-08-12)

**What I asked.** Functions are solid; now improve the experience. Kimi
walked the app as two personas (first-time investor and pro) and came
back with friction points; I approved the four-item plan.

**What Kimi implemented:**
1. Numbered setup flow - Practice setup now reads ① pick your start
   date ② how much ③ spread it across the funds (Split evenly lives in
   step 3) ④ choose how to travel; My Allocation got the same light
   numbering. A first-timer no longer wonders what to do first.
2. De-jargoning - "sandbox" replaced with "practice area" everywhere a
   user sees it.
3. First-walk orientation card - a dismissible three-line intro at the
   top of the walk (drag to travel / shaded stretches slow time / cards
   explain what happened), shown once per session.
4. The blue default alert boxes (sentiment disclaimer, turbulent
   banner) were never actually themed - the earlier CSS targeted a
   selector Streamlit had changed; alerts are now pinned to the
   teal-tinted card style with stronger selectors.
- Two test files had hardcoded the old button label and failed after
  the wording change; updated (a reminder that copy changes are code
  changes when tests assert on strings).

**Verification:** 63 tests pass; Kimi screenshot-verified the numbered
setup, the orientation card, and the themed disclaimer.

---

## Session 42 — Pure design polish pass (2026-08-12)

**What I asked.** Functions done; make the product more beautiful, no
function changes. I flagged the disclaimer box as ugly and the sidebar
as empty/unbalanced, and asked Kimi for the rest. I also asked that the
pass be reversible - a backup of streamlit_app.py was taken first
(/tmp/streamlit_app_pre_design_pass.py).

**What Kimi implemented (its own design judgement, no external repos):**
1. The disclaimer and the turbulent banner lost their boxes - they are
   now quiet text lines with a thin teal accent bar.
2. The sidebar gained a "Your journey" map: the four sections listed
   with the current one marked, filling the dead space with wayfinding.
3. Every chart now renders inside a white card (border, radius,
   padding), matching the metric cards - the single biggest finish
   upgrade.
4. Page headings gained the thin teal editorial rule.
5. The landing gained a quiet stat strip (12 funds · 3 years · ~147,000
   headlines · 10 sectors).
- One test updated: the disclaimer moved from st.info to styled
  markdown, so the test now asserts on the rendered text instead.

**Verification:** 63 tests pass; Kimi screenshot-verified the landing,
Funds, and Sentiment pages after the pass.

---

## Session 43 — "How every fund is built" mechanism transparency (2026-08-12)

**What I asked.** Users should see that the funds are not randomly put
together and given a fund name - show the calculation behind each fund.
We settled on a split design: a shared sidebar explainer, plus per-fund
depth in the existing fact-sheet expander (formulas in professional
mode, worked real-number examples in plain mode).

**What Kimi implemented:**
1. New sidebar expander "How every fund is built" - the shared 5-step
   recipe (252-row estimation window on each panel's own calendar,
   shrunk covariance, one of four long-only fully-invested rules,
   monthly walk-forward, stated assumptions), paired plain/pro wording,
   closed by the mandated not-a-guarantee line.
2. Fact-sheet upgrade - the existing "How this fund is built" expander
   now shows the method's formula as LaTeX in professional mode
   (verified against src/portfolios.py optimisers and src/fusion.py's
   alpha = 0.25 tilt) or, in plain mode, a worked example with the
   fund's REAL latest-rebalance numbers (e.g. Equal-Weight: 100% / 60 =
   1.67% in every asset; Equity Max-Sharpe: 7 of 50 assets, GE at
   39.7%). Numbers are computed live from the committed
   fund_weights.csv by _mechanism_stats() - no optimiser runs in the
   app (brief rule 3).
3. Three new AppTest tests: sidebar expander present; plain mode
   renders the 1.67% worked example and no LaTeX; pro mode renders
   LaTeX.

**Verification:** 66 tests pass (63 + 3 new). The weight numbers were
cross-checked against results/data/fund_weights.csv before writing any
wording. A scripted neutrality sweep over all new strings found no
evaluative wording; the mandated closing lines render in both the new
sidebar expander and per fund.

---

## Session 44 — Report redo: content alignment + design + settlement page (2026-08-12)

**What I asked.** Three things: (1) my new Practice idea - a settlement
page ("you adjusted X times; because you adjusted, you made $X extra vs
the original mix") - goes into the report's critical-thinking section,
NOT into the app (no time to build it); (2) rewrite everything in the
report that no longer matches the current product; (3) add visual design
- the old report was "too clean".

**Key facts Kimi surfaced before writing.** The report text predated
Sessions 19-43 (blind walk, dollar-first allocation, My Portfolio, daily
digest, news exposure, mechanism transparency, design polish, stress
suite - all missing). A settlement-page ancestor ALREADY exists: the
Session-20 blind-walk debrief (path vs never-touched counterfactual +
decision count), so the report frames the idea as its designed
extension, not a new invention. And my own Session-39 policy said
unfixed cosmetic flaws are reflection material - that list is now in
Section 6.

**What Kimi implemented (all in scripts/build_report_full.py; the docx
is regenerated, never hand-edited):**
1. Content: new title ("sandbox" -> practice area per Session 41);
   Section 2 fact-sheet description now covers the construction block
   (pro formula / plain worked example) and the sidebar explainer;
   Section 4 describes both travel modes (Replay + Blind walk with the
   storm-guard rule), the daily digest, and the end-of-walk debrief;
   Section 5 journey rewritten (dollar-first allocation with the amount
   contract, My Portfolio cards/compare/aggregate, two-way bridge,
   exposure-follows-the-money) and reliability updated (66 tests incl.
   the 32-test stress suite, widget-state mirror); Section 6 gains the
   deliberately-unfixed cosmetic list, the AppTest-vs-real-server
   lesson, and the settlement-page paragraph - which discusses the
   neutrality tension head-on ("you made $X extra" is a verdict; the
   honest version reports arithmetic and stops).
2. Design: Georgia display headings in app-teal with the thin teal
   editorial rule, designed title block ("Evidence, not advice."
   tagline), maroon-led exhibit captions, centred figures, page-number
   footer + muted header (title page kept clean), and two REAL styled
   tables - Exhibit 1 (all 13 funds' metrics) and Exhibit 6 (fusion
   before/after) - replacing two open [EVIDENCE] placeholders.

**Verification:** docx re-parsed programmatically: all 10 headings, 2
tables, 7 embedded images; zero stale terms ("sandbox", "sets
percentages"); all new content present; narrative ~5,320 words excl.
guidance/appendix/references (slightly above the ~5,000 guide - flagged
to the student, whose own-words rewrite will absorb it). check_handin:
22 pass, zero FAIL. LibreOffice is not installed, so page rendering was
NOT pixel-verified - the student should open the docx in Word and check
the 10-page narrative limit visually (exhibits can move to the appendix
if needed).

---

## Session 45 — Exhibit redesign + product screenshots in the report (2026-08-12)

**What I reported.** The 13-fund growth-of-$1 chart is unreadable
(spaghetti); I proposed replacing some report plots with screenshots of
the product, and asked Kimi to verify the idea first, not just agree.

**Kimi's verdict (which I accepted).** The diagnosis was right, the cure
half-right: the brief REQUIRES a growth-of-$1 comparison figure (no
screenshot can satisfy it - the app never shows all funds on one chart,
and screenshots carry UI chrome + are not reproducible artifacts). So:
redesign the bad figures as real exhibits, AND add product screenshots
where they belong (Section 5, the app journey). Both, not either/or.

**What Kimi implemented:**
1. growth_of_1_all_funds.png rebuilt as small multiples - one panel per
   family, fixed colour per method across panels, line-end labels with
   terminal values (no legend), panels scaled independently. The figure
   now shows the report's own thesis (family = extremes, method = the
   ride) instead of hiding it.
2. sector_sentiment_index.png rebuilt as a 2x5 sector grid with one
   shared y-axis - the level bias and the "thinner-news sectors are
   noisier" claim are now actually visible.
3. weights_combined_max_sharpe.png: dropped the grey "Other" band and
   fitted the axis (same fix as the app's Session-33 chart); also fixed
   a genuine reindex bug (leading NaN month: first rebalance 2021-01-29
   fell outside the return calendar; now method="ffill").
4. Four product screenshots captured with Playwright against a locally
   running app (marketplace, fact sheet with the construction block
   expanded, blind walk inside the May-2021 storm window, sentiment
   tab) and inserted into Section 5 as "Product view 1-4", replacing
   the [INSERT screenshots] placeholder. Saved under
   report/screenshots/.
5. All three redesigned figures live in scripts/run_part_b.py as named
   functions (fig_growth_of_1, fig_sector_sentiment,
   fig_weights_over_time), so the full pipeline still reproduces them;
   regenerated from committed CSVs for speed (no full re-run).

**Verification:** every new figure/screenshot was viewed before
acceptance (growth panels, sentiment grid, weights chart, all four
product views). The white strips in the weights chart were checked
against data: real zero-holding periods (Feb 2021 held BTC 41%/NVDA
26%/XLM 18% - none of the top-5-by-mean), not a bug. Report rebuilt: 11
images, 2 tables, zero stale placeholders; check_handin 22 pass, zero
FAIL. One capture bug found and fixed along the way: Streamlit's date
input mangles typed dates - the walk was driven with the forward-step
button instead, which is also why the blind-walk screenshot sits inside
the crypto sell-off window (storm guard working as designed).
