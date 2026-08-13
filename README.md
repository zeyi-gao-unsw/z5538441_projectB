# HyperInvest — FinTech Project Part B (z5538441)

**Live app:** https://zeyi-gao-unsw-z5538441-projectb-streamlit-app-hssehq.streamlit.app/
**Public repo:** https://github.com/zeyi-gao-unsw/z5538441_projectB

Part B: funds, sentiment, and the app (DFF Stations 3–4), built on my own
Part A data foundation. This folder is also the public GitHub repository for
the deployed app; the app entrypoint is `streamlit_app.py` at the root.

HyperInvest is an evidence layer for novice self-directed investors: it
presents out-of-sample, backtested systematic funds and a news-sentiment
index with plain-language explanations, and never recommends a fund, an
allocation, or a buy/sell decision.

## How to run

    pip install -r requirements.txt -r requirements-dev.txt   # dev adds nltk (VADER) + finvader
    python scripts/run_part_b.py            # reproduces all results/ artifacts
    python scripts/build_sentiment_benchmark.py   # optional: validate our sentiment model against the course's finVADER benchmark
    streamlit run streamlit_app.py          # runs the app locally
    python -m pytest -q                     # tests
    python scripts/check_handin.py          # pre-submission check

Load raw data through `src/data_access.py` (see `context/DATA_GUIDE.md`);
never commit raw data. The deployed app reads only precomputed artifacts
from `results/` — those ARE committed.

## What is here

- `PROJECT_BRIEF.md` — the assignment brief (read first)
- `src/` — pipeline code (data_access.py is provided; the rest is mine)
- `scripts/` — runnable scripts that reproduce results
- `results/` — committed app artifacts, tables, and figures
- `context/` — provided data guide and project context (do not edit)
- `report/` — the written report (see OUTLINE.md)
- `ai/` — prompt log and AI-use notes (graded)
- `AGENTS.md` — my own agent instruction file (graded)

## Before you hand in

    python scripts/check_handin.py

Fix every [FAIL]. Then zip this whole folder and upload to Moodle; deploy
the app from a public GitHub repo (see docs/STUDENT_DEPLOY.md).
