"""HyperInvest - Part B Streamlit app (z5538441_projectB).

Run from the project folder:

    streamlit run streamlit_app.py

The app reads ONLY the precomputed artifacts committed under results/ (fund
returns, fund weights, the sector sentiment index, performance metrics, and
the event calendar built by scripts/build_event_calendar.py). It never runs
an optimiser or VADER. All portfolio math in the app is weighted arithmetic
on the committed fund returns.

Neutrality rules (from AGENTS.md): the app states WHAT happened and WHY, with
numbers; it never says whether anything was good or what to do next. All
plain-English wording lives in the two static paired-strings structures
below (COPY for general text, PRACTICE_COPY for the Practice learning cards),
each holding a professional and a plain version. Nothing is generated live.
"""
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import streamlit as st

from src.events import NAMED_EVENTS  # noqa: F401  (kept for reference/annotations)

ROOT = Path(__file__).resolve().parent
RESULTS_DATA = ROOT / "results" / "data"
RESULTS_TABLES = ROOT / "results" / "tables"

# ---------------------------------------------------------------------------
# Design constants (muted FT-style palette)
# ---------------------------------------------------------------------------
TEAL = "#0F766E"
MAROON = "#990F3D"
GOLD = "#F2B701"
SLATE = "#4C78A8"
CHARCOAL = "#262A33"
MUTED = "#6B625C"
GREY = "#9A9DA3"          # reserved for "Other" bands and context lines
LIGHT_GREY = "#D9D9D9"    # turbulent-window shading

PALETTE = [TEAL, MAROON, GOLD, SLATE, CHARCOAL,
           "#6B9E8F", "#C0637F", "#D9A441", "#8FA8C8", "#7A7E87"]
STACK_COLORS = [SLATE, TEAL, GOLD, MAROON, CHARCOAL]  # top-5; Other is grey

# ---------------------------------------------------------------------------
# Design system (see AGENTS.md: the rubric rewards an original, coherent
# design system - colour, type, and figure language). Three parts:
#   1. .streamlit/config.toml [theme] - page surfaces and the teal primary
#   2. DESIGN_CSS below              - typography, components, hidden chrome
#   3. apply_chart_style()           - one rcParams figure language
# Surfaces: warm paper background (#FAF7F2), white cards, hairline borders.
# Type: Source Serif 4 for headings and metric values (editorial feel),
# Inter for body text. Charts keep DejaVu Sans because matplotlib renders
# server-side PNGs and cannot rely on a browser-loaded font existing on the
# deployment machine - chart polish comes from the rcParams, not the font.
# ---------------------------------------------------------------------------
SURFACE = "#FAF7F2"
SURFACE_SIDEBAR = "#F3EFE8"
CARD = "#FFFFFF"
BORDER = "#E8E2D8"
INK = "#1A1D24"

DESIGN_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');

/* --- chrome: a product, not a demo (header kept transparent so the
       sidebar toggle stays usable) --- */
#MainMenu, footer {{ visibility: hidden; }}
[data-testid="stHeader"] {{ background: transparent; }}

/* --- typography --- */
html, body, [class*="css"], p, li, label, .stMarkdown {{
    font-family: 'Inter', -apple-system, sans-serif;
    color: {CHARCOAL};
}}
h1, h2, h3, h4 {{
    font-family: 'Source Serif 4', Georgia, serif !important;
    color: {INK};
    letter-spacing: -0.01em;
}}

/* --- surfaces --- */
[data-testid="stAppViewContainer"] {{ background: {SURFACE}; }}
[data-testid="stSidebar"] {{
    background: {SURFACE_SIDEBAR};
    border-right: 1px solid {BORDER};
}}

/* --- metric cards --- */
[data-testid="stMetric"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 14px 16px 10px;
    box-shadow: 0 1px 2px rgba(38,42,51,0.04);
    transition: box-shadow .15s ease, transform .15s ease;
}}
[data-testid="stMetric"]:hover {{
    box-shadow: 0 3px 10px rgba(38,42,51,0.08);
    transform: translateY(-1px);
}}
[data-testid="stMetricLabel"] p {{
    font-weight: 600;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: {MUTED};
}}
[data-testid="stMetricValue"] {{
    font-family: 'Source Serif 4', Georgia, serif;
    color: {INK};
    /* 1.6rem keeps long values (e.g. "01 Feb 2021") inside the card
       instead of truncating with an ellipsis. */
    font-size: 1.6rem !important;
    white-space: normal !important;
}}

/* --- buttons --- */
.stButton button {{
    border-radius: 8px;
    font-weight: 600;
    transition: box-shadow .15s ease, transform .15s ease;
}}
.stButton button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(15,118,110,0.25);
}}

/* --- content cards: expanders, dataframes, alerts, inputs --- */
[data-testid="stExpander"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
}}
/* Alert boxes: Streamlit's default blue reads as off-brand on the warm
   paper surface, so both the testid wrapper and the inner themed body
   are pinned to the teal-tinted card (the inner element carries the
   framework's own background class and needs !important). */
[data-testid="stAlert"],
[data-testid="stAlertContainer"],
[data-testid="stAlert"] > div,
[data-testid="stAlertContainer"] > div {{
    background-color: #EEF4F2 !important;
    border: 1px solid #CBDFDA !important;
    border-radius: 10px;
}}
[data-testid="stAlert"] p, [data-testid="stAlertContainer"] p {{
    color: {CHARCOAL} !important;
}}
hr {{ border-color: {BORDER}; }}

/* --- landing hero: the product's front door --- */
.hero {{ padding: 5vh 0 1vh; }}
.hero-kicker {{
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.22em;
    text-transform: uppercase; color: {TEAL}; margin-bottom: 10px;
}}
.hero-title {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 4.4rem; font-weight: 700; color: {INK};
    line-height: 1.04; letter-spacing: -0.02em;
}}
.hero-sub {{
    font-size: 1.12rem; color: {MUTED}; max-width: 46rem;
    margin-top: 16px; line-height: 1.65;
}}

/* --- the two landing choices as large cards --- */
.st-key-choice_funds button, .st-key-choice_practice button {{
    width: 100%; min-height: 96px; background: {CARD};
    border: 1px solid {BORDER}; border-radius: 14px;
    font-size: 1.05rem; font-weight: 600; color: {INK};
    box-shadow: 0 1px 2px rgba(38,42,51,0.05);
    transition: transform .15s ease, box-shadow .15s ease,
                border-color .15s ease;
}}
.st-key-choice_funds button:hover, .st-key-choice_practice button:hover {{
    transform: translateY(-2px);
    border-color: {TEAL};
    box-shadow: 0 6px 18px rgba(15,118,110,0.16);
}}

/* --- sidebar identity --- */
.sidebar-brand {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.45rem; font-weight: 700; color: {INK};
}}
.sidebar-tag {{ font-size: 0.8rem; color: {MUTED}; margin-bottom: 4px; }}

/* --- pill navigation (main section radio) --- */
[data-testid="stRadio"] [role="radiogroup"] {{
    background: {SURFACE_SIDEBAR}; border: 1px solid {BORDER};
    border-radius: 999px; padding: 4px; gap: 2px;
}}
[data-testid="stRadio"] [role="radiogroup"] label {{
    border-radius: 999px; padding: 3px 12px;
    transition: background .12s ease;
}}
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {{
    background: {TEAL};
}}
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p {{
    color: #FFFFFF !important; font-weight: 600;
}}

/* --- asset-family containers (allocation inputs) --- */
.st-key-fam_combined, .st-key-fam_equity, .st-key-fam_crypto,
.st-key-fam_tilt {{
    border-radius: 12px; border: 1px solid;
    padding: 4px 14px 12px; margin-bottom: 10px;
}}
.st-key-fam_combined {{ background: #E7F2F0; border-color: #BFDDD8; }}
.st-key-fam_equity   {{ background: #ECEFF5; border-color: #C9D4E4; }}
.st-key-fam_crypto   {{ background: #FAF3DF; border-color: #E8D9A8; }}
.st-key-fam_tilt     {{ background: #F5EDF1; border-color: #DCC3D1; }}

/* --- saved-mix cards (My Portfolio) --- */
[class*="st-key-mixcard"] {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 8px 16px 12px; margin-bottom: 10px;
}}

/* --- first-walk orientation card --- */
.st-key-walk_intro {{
    background: #EEF4F2; border: 1px solid {TEAL};
    border-radius: 12px; padding: 10px 16px 12px; margin-bottom: 12px;
}}

/* --- quiet notes: disclaimers/banners without the heavy box --- */
.quiet-note {{
    color: {MUTED};
    font-size: 0.86rem;
    border-left: 3px solid {TEAL};
    padding: 2px 0 2px 10px;
    margin: 2px 0 12px;
}}

/* --- sidebar journey map --- */
.journey-item {{
    color: {MUTED}; font-size: 0.9rem; padding: 3px 0 3px 12px;
    border-left: 2px solid {BORDER};
}}
.journey-item.current {{
    color: {TEAL}; font-weight: 700; border-left-color: {TEAL};
}}

/* --- charts as cards --- */
[data-testid="stImage"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 10px 14px;
}}

/* --- editorial rule under page headings --- */
h2 {{
    border-bottom: 2px solid {TEAL};
    padding-bottom: 6px;
}}

/* --- landing stat strip --- */
.stat-strip {{
    color: {MUTED};
    font-size: 0.88rem;
    letter-spacing: 0.04em;
    border-top: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 8px 0;
    margin: 18px 0 8px;
}}
</style>
"""


def apply_chart_style() -> None:
    """One figure language for every chart in the app."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "text.color": CHARCOAL,
        "axes.edgecolor": "#D8D2C8",
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#E5DFD5",
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "axes.labelcolor": "#4A443E",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "figure.facecolor": CARD,
        "axes.facecolor": CARD,
        "savefig.facecolor": CARD,
    })

FUND_ORDER = [
    "Combined Equal-Weight", "Combined Min-Variance", "Combined Max-Sharpe",
    "Combined Risk-Parity",
    "Equity Equal-Weight", "Equity Min-Variance", "Equity Max-Sharpe",
    "Equity Risk-Parity",
    "Crypto Equal-Weight", "Crypto Min-Variance", "Crypto Max-Sharpe",
    "Crypto Risk-Parity",
    "Equity+Sentiment Tilt",
]
N_FUNDS = len(FUND_ORDER)
# Periods per year used to annualise each fund (252 for anything holding
# equities, 365 only for the pure-crypto funds - never mixed). Derived
# from the fund name so a future matrix change cannot silently misalign.
PERIODS_PER_YEAR = np.array(
    [365.0 if f.startswith("Crypto") else 252.0 for f in FUND_ORDER])
UNIVERSE = {
    "Combined Equal-Weight": "60 assets (50 US large-cap shares + 10 cryptocurrencies)",
    "Combined Min-Variance": "60 assets (50 US large-cap shares + 10 cryptocurrencies)",
    "Combined Max-Sharpe": "60 assets (50 US large-cap shares + 10 cryptocurrencies)",
    "Combined Risk-Parity": "60 assets (50 US large-cap shares + 10 cryptocurrencies)",
    "Equity Max-Sharpe": "50 US large-cap shares",
    "Equity Min-Variance": "50 US large-cap shares",
    "Equity Equal-Weight": "50 US large-cap shares",
    "Equity Risk-Parity": "50 US large-cap shares",
    "Crypto Max-Sharpe": "10 cryptocurrencies",
    "Crypto Equal-Weight": "10 cryptocurrencies",
    "Crypto Min-Variance": "10 cryptocurrencies",
    "Crypto Risk-Parity": "10 cryptocurrencies",
    "Equity+Sentiment Tilt": "50 US large-cap shares",
}
METRIC_KEYS = ["ann_return", "ann_vol", "sharpe", "max_drawdown"]
METRIC_NAMES = {
    "ann_return": "Annualised return",
    "ann_vol": "Annualised volatility",
    "sharpe": "Sharpe ratio",
    "max_drawdown": "Maximum drawdown",
}


def metric_name(key: str) -> str:
    """One name per metric WITHIN each language mode. Plain mode speaks
    everyday language for every metric; professional mode keeps the
    standard terms. The two modes must be visibly different - the toggle
    is the product's graduation story, not decoration."""
    if lang() == "plain":
        return {"ann_return": "Yearly return",
                "ann_vol": "Yearly swing (±%)",
                "sharpe": "Return per swing",
                "max_drawdown": "Worst fall"}[key]
    return METRIC_NAMES[key]


# Plain-language one-liners: what each fund tries to do, in everyday words.
# Each describes the METHOD (a fact about construction), never an outcome
# (a promise) - see AGENTS.md neutrality rules. Every line is standalone.
FUND_ONELINER = {
    "Combined Equal-Weight": "Puts the same amount of money into every one "
                             "of the 60 assets - no favourites.",
    "Combined Min-Variance": "Chooses the mix of shares and crypto that, "
                             "looking at the past year, would have moved up "
                             "and down the least.",
    "Combined Max-Sharpe": "Chooses the mix of shares and crypto that, "
                           "looking at the past year, gave the most return "
                           "for the size of its ups and downs.",
    "Combined Risk-Parity": "Spreads money across the 60 assets so each one "
                            "contributes a similar amount of up-and-down "
                            "movement.",
    "Equity Max-Sharpe": "Chooses the mix of the 50 US shares (no crypto) "
                         "that, looking at the past year, gave the most "
                         "return for the size of its ups and downs.",
    "Equity Min-Variance": "Chooses the mix of the 50 US shares (no crypto) "
                           "that, looking at the past year, would have "
                           "moved up and down the least.",
    "Equity Equal-Weight": "Puts the same amount of money into every one "
                           "of the 50 US shares - no favourites.",
    "Equity Risk-Parity": "Spreads money across the 50 US shares so each "
                          "one contributes a similar amount of up-and-down "
                          "movement.",
    "Crypto Max-Sharpe": "Chooses the mix of the 10 cryptocurrencies (no "
                         "shares) that, looking at the past year, gave the "
                         "most return for the size of its ups and downs.",
    "Crypto Equal-Weight": "Puts the same amount of money into every one "
                           "of the 10 cryptocurrencies - no favourites.",
    "Crypto Min-Variance": "Chooses the mix of the 10 cryptocurrencies (no "
                           "shares) that, looking at the past year, would "
                           "have moved up and down the least.",
    "Crypto Risk-Parity": "Spreads money across the 10 cryptocurrencies so "
                          "each one contributes a similar amount of "
                          "up-and-down movement.",
    "Equity+Sentiment Tilt": "Starts from the Equity Max-Sharpe mix, then "
                             "shifts a little toward sectors whose recent "
                             "news headlines sounded more positive.",
}
# The construction rule of each method, as math. Shown in professional mode
# on the fund fact sheet (plain mode shows a worked numeric example instead).
# Verified against src/portfolios.py (optimisers, long-only fully invested)
# and src/fusion.py (alpha = 0.25 multiplicative sector-sentiment tilt).
METHOD_FORMULA = {
    "equal_weight": r"w_i = \frac{1}{N}",
    "min_variance": (r"\min_{w}\; w^{\top}\Sigma w \quad \text{s.t. } "
                     r"\textstyle\sum_i w_i = 1,\; w_i \ge 0"),
    "max_sharpe": (r"\max_{w}\; \frac{w^{\top}\mu}"
                   r"{\sqrt{w^{\top}\Sigma w}} \quad \text{s.t. } "
                   r"\textstyle\sum_i w_i = 1,\; w_i \ge 0"),
    "risk_parity": (r"\mathrm{RC}_i = \frac{w_i\,(\Sigma w)_i}"
                    r"{w^{\top}\Sigma w} = \frac{1}{N} \;\; \forall\, i"),
    "tilt": r"w_i \propto w^{\mathrm{MS}}_i \left(1 + 0.25\, z_{s(i)}\right)",
}
TABS = ["Funds", "My Allocation", "Sentiment", "Practice"]
SECTORS = ["Comm", "Consumer", "Energy", "Financials", "Healthcare",
           "Industrials", "Materials", "RealEstate", "Tech", "Utilities"]
SECTOR_DISPLAY = {"Comm": "Communication", "Tech": "Technology",
                  "RealEstate": "Real Estate"}
SECTOR_COLORS = dict(zip(SECTORS, PALETTE))

# Ticker -> sector map for the "News exposure" feature. Hardcoded because
# the sample is frozen (data ends 2023-12-31), but VERIFIED against the
# real data on 2026-08-11 (50/50 tickers match exactly) and guarded by
# tests/test_app.py::test_sector_map_matches_real_data, which reloads the
# hosted data and fails loudly if this map ever drifts from it.
SECTOR_MAP: dict[str, str] = {}
for _sector, _tickers in {
    "Tech": ["NVDA", "AMD", "INTC", "QCOM", "ADBE"],
    "Financials": ["GS", "MS", "WFC", "V", "USB"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "OXY"],
    "Consumer": ["DIS", "WMT", "NKE", "SBUX", "KO"],
    "Industrials": ["GE", "BA", "CAT", "UPS", "MMM"],
    "Healthcare": ["MRK", "ABBV", "AMGN", "GILD", "ABT"],
    "Comm": ["T", "CMCSA", "TMUS", "EA", "TTWO"],
    "Materials": ["SHW", "NEM", "DOW", "NUE", "DD"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP"],
    "RealEstate": ["AMT", "O", "PLD", "CCI", "PSA"],
}.items():
    for _t in _tickers:
        SECTOR_MAP[_t] = _sector
DATA_START = pd.Timestamp("2021-02-01")   # first day all 8 funds have returns
DATA_END = pd.Timestamp("2023-12-31")
PRACTICE_START_MIN = DATA_START
PRACTICE_START_MAX = pd.Timestamp("2023-12-29")

# ---------------------------------------------------------------------------
# COPY - the single static paired-strings structure for all app wording.
# Every entry has a "plain" and a "pro" version; placeholders like {x} are
# filled with numbers computed from the committed CSVs at render time.
# ---------------------------------------------------------------------------
GUARANTEE_LINE = ("This describes how the fund is built - it is not a "
                  "prediction or guarantee of future results.")

COPY = {
    # --- landing ---------------------------------------------------------
    "landing_tagline": {
        "plain": "Eight systematic funds, three years of real history "
                 "(2021-2023), and a practice area that lets you travel through "
                 "that history day by day. This app shows what happened; "
                 "it does not give investment advice.",
        "pro": "HyperInvest presents out-of-sample backtests of eight "
               "systematic funds (2021-2023), a sector news-sentiment "
               "index, and a historical replay area. It reports "
               "evidence; it does not provide investment advice.",
    },
    "landing_btn_funds": {"plain": "Explore the funds", "pro": "Explore the funds"},
    "landing_btn_practice": {"plain": "Start in the practice area",
                             "pro": "Start in the Practice area"},
    "landing_cap_funds": {
        "plain": "Opens the Funds page: the comparison table, fund fact "
                 "sheets, and holdings. Either choice only sets your "
                 "starting page.",
        "pro": "Opens the Funds section: the metrics table, fact sheets, "
               "and holdings. Either choice only sets your starting page.",
    },
    "landing_cap_practice": {
        "plain": "Opens the practice area: replay history day by day "
                 "with a simulated portfolio. Either choice only sets your "
                 "starting page.",
        "pro": "Opens the practice area: a day-by-day replay of the "
               "sample with a simulated portfolio. Either choice only "
               "sets your starting page.",
    },
    # --- funds tab --------------------------------------------------------
    "funds_heading": {"plain": "The fund shelf", "pro": "Fund comparison"},
    "sample_period": {
        "plain": "Sample period: 1 February 2021 to 31 December 2023 (734 "
                 "trading days) for every fund except Crypto Max-Sharpe, "
                 "which trades on its own 365-day calendar from 1 October "
                 "2020 (1,187 days). This applies to every table and chart "
                 "on this page.",
        "pro": "Out-of-sample period: 2021-02-01 to 2023-12-31 (734 trading "
               "days); Crypto Max-Sharpe: 2020-10-01 to 2023-12-31 (1,187 "
               "days, 365-day calendar). Applies to all exhibits on this "
               "page.",
    },
    "sorting_caption": {
        "plain": "Sorting changes the order shown. It does not rank the "
                 "funds by quality.",
        "pro": "Sorting changes the order shown. It does not rank the "
               "funds by quality.",
    },
    "howto_title": {"plain": "How to read these numbers",
                    "pro": "Metric definitions"},
    "howto_body": {
        "plain": "- **Yearly return** - if an average year from this "
                 "period repeated, \\$100 would have become about "
                 "\\${cew_100:.0f} (Combined Equal-Weight grew {cew_ret:.1f}% "
                 "per year). It is an average - individual years were "
                 "higher or lower.\n"
                 "- **Yearly swing (volatility)** - how bumpy the ride is. "
                 "±{rp_vol:.0f}% means the value typically moved up or down "
                 "about {rp_vol:.0f}% in a year. A bigger number means a "
                 "bumpier ride - in BOTH directions, not just down. "
                 "Combined Risk-Parity: about ±{rp_vol:.1f}%; Crypto "
                 "Max-Sharpe: about ±{cr_vol:.1f}%.\n"
                 "- **Sharpe ratio** - a way to compare funds fairly: how "
                 "much return came with each dollar of bumpiness. "
                 "{rp_sh:.2f} means about {rp_sh_cents:.0f} cents of yearly "
                 "return for every \\$1.00 of bumpiness (Combined "
                 "Risk-Parity). It means little on its own - use it to "
                 "compare two funds side by side.\n"
                 "- **Maximum drawdown** - the worst fall from a peak "
                 "during the period. {cr_dd:.1f}% means \\$100 invested "
                 "right at the top was worth \\${cr_dd_usd:.0f} at the worst "
                 "moment (Crypto Max-Sharpe). The fund recovered later - "
                 "this measures the worst point, not the ending.",
        "pro": "- **Annualised return**: geometric average growth rate over "
               "the sample, annualised with 252 periods for equity-calendar "
               "funds and 365 for the crypto fund.\n"
               "- **Annualised volatility**: standard deviation of daily "
               "returns, scaled by the square root of periods per year.\n"
               "- **Sharpe ratio**: mean daily return divided by daily "
               "standard deviation, scaled by the square root of periods "
               "per year (risk-free rate 0).\n"
               "- **Maximum drawdown**: the maximum peak-to-trough decline "
               "of the cumulative value series.",
    },
    "choose_fund": {"plain": "Choose a fund", "pro": "Choose a fund"},
    "backtest_basis": {
        "plain": "How the numbers were produced: every fund rebalances "
                 "monthly using only the past 252 trading days (the crypto "
                 "fund uses its 365-day calendar); risk-free rate 0; no "
                 "transaction costs.",
        "pro": "Backtest basis: walk-forward out-of-sample; 252-trading-day "
               "estimation window; monthly rebalancing; risk-free rate 0; "
               "no transaction costs.",
    },
    "gloss_ann_return": {"plain": "On average over the sample, \\$100 grew "
                                  "by about \\${v:.1f} per year.", "pro": ""},
    "gloss_ann_vol": {"plain": "Typically moved up or down about ±{v:.1f}% "
                               "in a year - in both directions.", "pro": ""},
    "gloss_sharpe": {"plain": "\\${v:.2f} of yearly return for every \\$1.00 "
                              "of bumpiness.", "pro": ""},
    "gloss_max_dd": {"plain": "\\$100 invested right at the top was worth "
                              "\\${usd:.0f} at the worst moment - a worst "
                              "moment, not the final result.", "pro": ""},
    "funds_explain_title": {"plain": "What does each fund do?",
                            "pro": "What does each fund do?"},
    # The matrix explainer: teach the STRUCTURE (family x method) instead
    # of listing 13 near-identical fund descriptions. Rendered in plain
    # mode only; per-fund one-liners still appear on each fact sheet.
    "funds_explain_body": {
        "plain": (
            "**Step 1 - what to hold:**  \n"
            "- **Combined** - shares and crypto together  \n"
            "- **Equity** - US shares only  \n"
            "- **Crypto** - coins only\n"
            "\n"
            "**Step 2 - how it is built:**  \n"
            "- **Equal-Weight** - the same amount in everything, no "
            "favourites  \n"
            "- **Min-Variance** - the mix that moved up and down the "
            "least  \n"
            "- **Max-Sharpe** - the most return for the size of its ups "
            "and downs  \n"
            "- **Risk-Parity** - every asset contributes a similar amount "
            "of movement\n"
            "\n"
            "Every fund is one family + one method. **Equity+Sentiment "
            "Tilt** is the experiment: the Equity Max-Sharpe mix, nudged "
            "toward sectors with more positive news tone."
        ),
        "pro": "",
    },
    "about_data_title": {"plain": "ⓘ About the data & assumptions",
                         "pro": "ⓘ About the data & assumptions"},
    # --- sidebar mechanism explainer (how every fund is built) ------------
    "mech_title": {"plain": "How every fund is built",
                   "pro": "How every fund is built"},
    "mech_body": {
        "plain": (
            "1. **Look back one year.** Each month, take each asset's "
            "daily returns for the past 252 days of its own trading "
            "calendar (shares trade on weekdays; crypto trades every "
            "day). Nothing from the future is used - the rebalance day "
            "itself is excluded.\n"
            "2. **Measure.** From those returns, estimate each asset's "
            "average return and how strongly every pair of assets moves "
            "together.\n"
            "3. **Apply the fund's rule.** Equal-Weight splits evenly; "
            "Min-Variance picks the mix that would have swung least; "
            "Max-Sharpe picks the most return per unit of swing; "
            "Risk-Parity sizes positions so each contributes similar "
            "swing. Every rule: no short selling, and weights always add "
            "to 100%.\n"
            "4. **Hold one month, then repeat.** 36 rebalances for "
            "share-based funds, 40 for crypto funds. New weights earn "
            "returns from the next trading day onward.\n"
            "5. **The name is the recipe.** Every fund is one universe "
            "(Combined 60 / Equity 50 / Crypto 10) plus one of these "
            "four rules - nothing is hand-picked."
        ),
        "pro": (
            "1. **Estimation window.** At each month-end rebalance, the "
            "trailing 252 rows of the panel's own trading calendar (the "
            "crypto panel trades daily, the equity panel on market "
            "days); the rebalance day itself is excluded.\n"
            "2. **Estimation.** Sample means and covariance of daily "
            "returns; the covariance is shrunk toward a scaled-identity "
            "target (Ledoit-Wolf-style) so 50-60 assets can be estimated "
            "from 252 observations.\n"
            "3. **Optimisation.** One of four long-only, fully invested "
            "rules: equal weight / minimum variance / maximum Sharpe / "
            "risk parity. Every fund name is one universe + one rule.\n"
            "4. **Walk-forward.** Weights are held one month, then "
            "re-estimated (36 rebalances on the equity calendar, 40 on "
            "the crypto calendar). Weights earn returns from the next "
            "trading day - past data only.\n"
            "5. **Stated assumptions.** Risk-free rate 0; zero "
            "transaction costs."
        ),
    },
    "mech_guarantee": {
        "plain": "This describes how the funds are built - it is not a "
                 "prediction or guarantee of future results.",
        "pro": "This describes how the funds are built - it is not a "
               "prediction or guarantee of future results.",
    },
    "how_built_title": {"plain": "How this fund is built",
                        "pro": "How this fund is built"},
    "about_index_title": {"plain": "ⓘ About this index",
                          "pro": "ⓘ About this index"},
    # --- news exposure (My Allocation x Sentiment bridge) -------------------
    "news_exp_title": {"plain": "Your mix and the news",
                       "pro": "News exposure of the blend"},
    "news_exp_chart_title": {
        "plain": "Where your money sits, and the latest news tone there",
        "pro": "Blend sector exposure vs latest standardised sector sentiment",
    },
    "news_exp_caption": {
        "plain": "Bars: how much of your mix sits in each sector, from each "
                 "fund's latest holdings. Right side: how that sector's "
                 "latest news tone compares with its own history. This "
                 "describes the past; it does not predict returns, and it "
                 "is not advice.",
        "pro": "Bars: blend sector shares from the funds' latest target "
               "weights. Labels: latest sector sentiment as a full-sample "
               "z-score. Descriptive only; not a forward-looking signal.",
    },
    "news_exp_crypto_bucket": {"plain": "Crypto (no news data)",
                               "pro": "Crypto (no news data)"},
    "news_exp_none": {"plain": "no news data", "pro": "no news data"},
    "news_exp_all_crypto": {
        "plain": "This mix holds no shares - headlines cover the 50 US "
                 "shares only, so there is no news tone to show. A chart "
                 "here would tell you nothing.",
        "pro": "No equity exposure; the headline data covers only the "
               "equity universe, so no exposure chart is drawn.",
    },
    "placed_empty": {
        "plain": "Enter an amount to invest, then place it across the "
                 "funds.",
        "pro": "Enter an amount to invest, then place it across the "
               "funds.",
    },
    "card_tone": {
        "plain": "News tone where this mix sits: {sectors} (as of {date}).",
        "pro": "Mix news exposure: {sectors} (as of {date}).",
    },
    "card_tone_crypto": {
        "plain": "This mix holds no shares, so there is no news tone to "
                 "show (headlines cover the 50 shares only).",
        "pro": "No equity exposure; headlines cover the equity universe "
               "only.",
    },
    "tone_usual": {"plain": "about usual for this sector",
                   "pro": "in line with its history"},
    "tone_unusually_negative": {"plain": "unusually negative",
                                "pro": "unusually negative"},
    "tone_unusually_positive": {"plain": "unusually positive",
                                "pro": "unusually positive"},
    # --- asset-family group labels (allocation inputs) ----------------------
    "fam_combined": {"plain": "Combined - shares + crypto together",
                     "pro": "Combined (60 assets)"},
    "fam_equity": {"plain": "Equity - US shares only",
                   "pro": "Equity (50 US shares)"},
    "fam_crypto": {"plain": "Crypto - coins only",
                   "pro": "Crypto (10 coins)"},
    "fam_tilt": {"plain": "The sentiment experiment (share-based)",
                 "pro": "Equity + sentiment tilt (fusion variant)"},
    "growth_title": {"plain": "Growth of $1 - {fund}",
                     "pro": "Growth of $1 - {fund}"},
    "drawdown_title": {"plain": "Falls from the previous peak - {fund}",
                       "pro": "Drawdown - {fund}"},
    "holdings_tier1": {
        "plain": "Across its {n_reb} monthly rebalances the target weights "
                 "changed by {ch:.2f} percentage points in total, on "
                 "average - this fund holds the same weight in every asset "
                 "all the time. No chart is shown because the weights never "
                 "change: a flat line would add nothing.",
        "pro": "Mean total absolute weight change per rebalance: {ch:.2f} "
               "pp over {n_reb} rebalances - weights are constant by "
               "construction, so no over-time chart is drawn.",
    },
    "holdings_tier2": {
        "plain": "Across its {n_reb} monthly rebalances the target weights "
                 "changed by {ch:.1f} percentage points in total, on "
                 "average - too little movement for an over-time chart to "
                 "show anything useful, so the current holdings are shown "
                 "below instead.",
        "pro": "Mean total absolute weight change per rebalance: {ch:.1f} "
               "pp over {n_reb} rebalances - below the threshold for an "
               "over-time chart. Current holdings shown below.",
    },
    "holdings_chart_title": {
        "plain": "Target weights at each monthly rebalance - top holding "
                 "averages {top:.0f}% of the fund",
        "pro": "Target weights per rebalance - top 5 holdings; all others "
               "pooled in grey (top holding mean {top:.0f}%)",
    },
    "current_equal": {"plain": "All {n} assets held equally at {w:.2f}% "
                               "each, as of {date}.",
                      "pro": "All {n} assets held equally at {w:.2f}% "
                             "each, as of {date}."},
    "current_bar_title": {"plain": "Top 10 holdings as of {date}",
                          "pro": "Top 10 holdings as of {date}"},
    # --- fund construction lines (one static line per fund) ---------------
    "line_Combined Equal-Weight": {
        "plain": "Holds all 60 assets at the same weight, reset to equal "
                 "at each monthly rebalance.",
        "pro": "Equal weights across the 60-asset combined universe, "
               "rebalanced monthly.",
    },
    "line_Combined Min-Variance": {
        "plain": "Each month, picks the mix of all 60 assets that would "
                 "have swung the least over the past 252 trading days.",
        "pro": "Monthly weights across all 60 assets that minimise "
               "estimated portfolio variance over the trailing 252 trading "
               "days.",
    },
    "line_Combined Max-Sharpe": {
        "plain": "Each month, picks the mix of all 60 assets that would "
                 "have given the highest return per unit of swing over the "
                 "past 252 trading days.",
        "pro": "Monthly weights across all 60 assets that maximise the "
               "estimated Sharpe ratio over the trailing 252 trading days.",
    },
    "line_Combined Risk-Parity": {
        "plain": "Each month, sizes positions in all 60 assets so that "
                 "each asset contributes a similar share of the fund's "
                 "total swing.",
        "pro": "Monthly weights across all 60 assets such that each "
               "asset's contribution to estimated portfolio volatility is "
               "equalised.",
    },
    "line_Equity Max-Sharpe": {
        "plain": "Each month, picks the mix of the 50 shares that would "
                 "have given the highest return per unit of swing over the "
                 "past 252 trading days.",
        "pro": "Monthly weights across the 50 shares that maximise the "
               "estimated Sharpe ratio over the trailing 252 trading days.",
    },
    "line_Equity Min-Variance": {
        "plain": "Each month, picks the mix of the 50 shares that would "
                 "have swung the least over the past 252 trading days.",
        "pro": "Monthly weights across the 50 shares that minimise "
               "estimated portfolio variance over the trailing 252 trading "
               "days.",
    },
    "line_Crypto Max-Sharpe": {
        "plain": "Each month, picks the mix of the 10 cryptocurrencies "
                 "that would have given the highest return per unit of "
                 "swing, estimated on the 365-day crypto calendar.",
        "pro": "Monthly weights across the 10 cryptocurrencies that "
               "maximise the estimated Sharpe ratio, estimated on the "
               "365-day crypto calendar.",
    },
    "line_Equity Equal-Weight": {
        "plain": "Holds all 50 shares at the same weight, reset to equal "
                 "at each monthly rebalance.",
        "pro": "Equal weights across the 50-share equity universe, "
               "rebalanced monthly.",
    },
    "line_Equity Risk-Parity": {
        "plain": "Each month, sizes positions in the 50 shares so that "
                 "each share contributes a similar amount to the fund's "
                 "total swing.",
        "pro": "Monthly weights across the 50 shares with approximately "
               "equal risk contributions, estimated over the trailing 252 "
               "trading days.",
    },
    "line_Crypto Equal-Weight": {
        "plain": "Holds all 10 cryptocurrencies at the same weight, reset "
                 "to equal at each monthly rebalance.",
        "pro": "Equal weights across the 10-cryptocurrency universe, "
               "rebalanced monthly.",
    },
    "line_Crypto Min-Variance": {
        "plain": "Each month, picks the mix of the 10 cryptocurrencies "
                 "that would have swung the least over the past 252 "
                 "trading days.",
        "pro": "Monthly weights across the 10 cryptocurrencies that "
               "minimise estimated portfolio variance over the trailing "
               "252 trading days.",
    },
    "line_Crypto Risk-Parity": {
        "plain": "Each month, sizes positions in the 10 cryptocurrencies "
                 "so that each coin contributes a similar amount to the "
                 "fund's total swing.",
        "pro": "Monthly weights across the 10 cryptocurrencies with "
               "approximately equal risk contributions, estimated over "
               "the trailing 252 trading days.",
    },
    "line_Equity+Sentiment Tilt": {
        "plain": "Starts from the Equity Max-Sharpe weights, then shifts "
                 "weight toward sectors whose recent news tone is above "
                 "average and away from those below average.",
        "pro": "Equity Max-Sharpe weights, tilted at each rebalance by "
               "(1 + 0.25 x the sector's cross-sectional sentiment "
               "z-score) and renormalised.",
    },
    # --- worked construction examples (plain mode only; {x} placeholders --
    # filled at render time by _mechanism_stats from the committed weights)
    "worked_equal_weight": {
        "plain": ("At the last rebalance ({date}): 100% ÷ {n} assets = "
                  "**{eq_w:.2f}% in every asset**. Every rebalance looks "
                  "exactly like this - the rule never favours anything."),
        "pro": "",
    },
    "worked_min_variance": {
        "plain": ("At the last rebalance ({date}) the rule gave money to "
                  "**{n_held} of {n} assets** and left {n_zero} at 0%. "
                  "Biggest position: {top} at {top_w:.1f}%. The mix is "
                  "uneven because that is what minimised the past year's "
                  "swings."),
        "pro": "",
    },
    "worked_max_sharpe": {
        "plain": ("At the last rebalance ({date}) the rule concentrated "
                  "on **{n_held} of {n} assets**; the biggest was {top} "
                  "at {top_w:.1f}%, and {n_zero} assets got 0%. "
                  "Concentration is what the rule produces when few "
                  "assets carried the past year's return per unit of "
                  "swing."),
        "pro": "",
    },
    "worked_risk_parity": {
        "plain": ("At the last rebalance ({date}) **all {n} assets got "
                  "money**, sized from {min_w:.1f}% to {max_w:.1f}% (an "
                  "even split would be {eq_w:.2f}%). Steadier assets get "
                  "more, jumpier ones less, so each contributes a similar "
                  "share of the fund's swing."),
        "pro": "",
    },
    "worked_tilt": {
        "plain": ("At the last rebalance ({date}): start from the Equity "
                  "Max-Sharpe weights, then nudge each position up or "
                  "down by 0.25 × its sector's news-tone z-score (lagged "
                  "one day). Biggest position after the nudge: {top} at "
                  "{top_w:.1f}%."),
        "pro": "",
    },
    # --- formula-block captions (professional mode only) -------------------
    "formula_symbols": {
        "plain": "",
        "pro": ("μ, Σ estimated from the trailing 252 rows of the "
                "panel's calendar (covariance shrunk); long-only, fully "
                "invested."),
    },
    "formula_note_equal_weight": {"plain": "", "pro": ""},
    "formula_note_min_variance": {"plain": "", "pro": ""},
    "formula_note_max_sharpe": {
        "plain": "",
        "pro": "rf = 0; solved as an equivalent convex quadratic program.",
    },
    "formula_note_risk_parity": {
        "plain": "",
        "pro": ("RC_i is asset i's share of portfolio variance, equalised "
                "across assets."),
    },
    "formula_note_tilt": {
        "plain": "",
        "pro": ("z = lagged cross-sectional sector sentiment z-score; "
                "clipped at 0 and renormalised."),
    },
    # --- allocation tab ----------------------------------------------------
    "alloc_heading": {"plain": "My Allocation", "pro": "Allocation"},
    "alloc_intro": {
        "plain": "Enter a dollar amount for each fund - each one shows its "
                 "share of your mix as you go. The blended history appears "
                 "once the total is above $0.",
        "pro": "Enter a dollar amount per fund; shares of the mix are "
               "derived. The blended backtest renders once the total is "
               "above $0.",
    },
    "split_evenly": {"plain": "Split evenly", "pro": "Split evenly"},
    "reset_zero": {"plain": "Reset to zero", "pro": "Reset to zero"},
    "total_amount_label": {"plain": "Amount to invest ($)",
                           "pro": "Amount to invest ($)"},
    "total_amount_help": {
        "plain": "Split evenly spreads this amount across the funds; "
                 "editing individual funds updates the total below.",
        "pro": "Split evenly distributes this amount; the total follows "
               "the per-fund entries.",
    },
    "placed_line": {"plain": "Placed: \\${total:,.0f} of \\${target:,.0f}",
                    "pro": "Placed: \\${total:,.0f} of \\${target:,.0f}"},
    "placed_remaining": {"plain": "Not yet placed: \\${rem:,.0f}.",
                         "pro": "Unplaced: \\${rem:,.0f}."},
    "placed_over": {"plain": "Over by \\${over:,.0f} - reduce a fund or "
                             "raise the amount.",
                    "pro": "Over by \\${over:,.0f} - reduce a fund or "
                           "raise the amount."},
    "total_line": {"plain": "Total: \\${total:,.0f}",
                   "pro": "Total: \\${total:,.0f}"},
    "assumption_caption": {
        "plain": "Assumes you held these exact percentages for the whole "
                 "period, with no further buying or selling. Historical "
                 "performance; not a projection.",
        "pro": "Assumes you held these exact percentages for the whole "
               "period, with no further buying or selling. Historical "
               "performance; not a projection.",
    },
    "value_range_caption": {
        "plain": "Between {start} and {end}, \\${amount:,.0f} in this mix "
                 "ranged from \\${mn:,.0f} to \\${mx:,.0f} and ended at "
                 "\\${last:,.0f}.",
        "pro": "Sample path {start} to {end}: minimum \\${mn:,.0f}, maximum "
               "\\${mx:,.0f}, final \\${last:,.0f} on a \\${amount:,.0f} start.",
    },
    "value_chart_title": {"plain": "Value of this mix over the sample",
                          "pro": "Blended portfolio value"},
    "starting_ref": {"plain": "Starting amount ${amount:,.0f}",
                     "pro": "Starting amount ${amount:,.0f}"},
    "save_button": {"plain": "Save this allocation to My Portfolio",
                    "pro": "Save this allocation to My Portfolio"},
    "save_caption": {
        "plain": "Saving records the mix for this session only. No money "
                 "moves and nothing is bought.",
        "pro": "Saving records the mix for this session only. No money "
               "moves and nothing is bought.",
    },
    "saved_heading": {"plain": "My Portfolio - your saved mixes (this "
                               "session only)",
                      "pro": "Saved allocations (session state)"},
    "mix_name": {"plain": "Mix {i}", "pro": "Mix {i}"},
    "load_mix": {"plain": "Load into editor", "pro": "Load into editor"},
    "compare_caption": {
        "plain": "Same period and same assumptions for every mix - the "
                 "differences come from the mixes, nothing else. Shown "
                 "side by side, not ranked.",
        "pro": "Identical period and assumptions across mixes; side by "
               "side, not ranked.",
    },
    "save_from_practice": {"plain": "Save this starting mix to My "
                                    "Portfolio",
                           "pro": "Save starting mix to portfolio"},
    "test_in_practice": {"plain": "Test in the time machine",
                         "pro": "Open in the Practice area"},
    "test_total": {"plain": "Test my whole portfolio in the time machine",
                   "pro": "Test the aggregate in the Practice area"},
    "test_in_practice_help": {
        "plain": "Loads this mix into the Practice setup - nothing starts "
                 "until you press Start travelling.",
        "pro": "Loads the mix into the Practice setup; the simulation "
               "starts only on Start travelling.",
    },
    "saved_toast": {"plain": "Saved to My Portfolio.",
                    "pro": "Saved to My Portfolio."},
    "view_perf": {"plain": "View performance", "pro": "View performance"},
    "total_title": {"plain": "Your whole portfolio",
                    "pro": "Aggregate of saved mixes"},
    "total_placed_line": {"plain": "Total placed: {amount} across {n} saved "
                            "mixes.",
                   "pro": "Total placed: {amount} across {n} mixes."},
    "total_ref": {"plain": "Total placed ({amount})",
                  "pro": "Total placed ({amount})"},
    "total_caption": {
        "plain": "Every saved mix held over the same period, combined "
                 "into one view. Historical only - not a projection.",
        "pro": "All saved mixes combined over the same sample. Historical; "
               "not a projection.",
    },
    "saved_entry": {"plain": "Saved at {ts} - backtest period {period} - "
                             "{alloc}",
                    "pro": "Saved at {ts} - backtest period {period} - "
                           "{alloc}"},
    "remove": {"plain": "Remove", "pro": "Remove"},
    # --- sentiment tab ------------------------------------------------------
    "sent_heading": {"plain": "Sector news tone over time",
                     "pro": "Sector news-sentiment index"},
    "sent_sectors_label": {"plain": "Sectors to draw",
                           "pro": "Sectors to draw"},
    "sent_grey": {"plain": "Show the other sectors as grey background",
                  "pro": "Show the other sectors as grey background"},
    "sent_empty": {"plain": "Choose at least one sector to draw its line.",
                   "pro": "Choose at least one sector to draw its line."},
    "smooth_label": {"plain": "Averaging window (trading days)",
                     "pro": "Averaging window (trading days)"},
    "smooth_caption": {
        "plain": "1 draws every single day; 21 averages about a month. "
                 "This changes only the drawing, never the data.",
        "pro": "1 draws every single day; 21 averages about a month. "
               "This changes only the drawing, never the data.",
    },
    "sent_ylabel": {"plain": "News tone score (-1 to +1)",
                    "pro": "Sentiment score (VADER compound, lagged)"},
    "sent_standardise": {
        "plain": "Compare each sector against its own usual level (standardise)",
        "pro": "Standardise each sector (z-score over the full sample)",
    },
    "sent_standardise_caption": {
        "plain": "0 is that sector's usual level over the period; +2 or -2 "
                 "is very unusual for it. Headline tone is positive most of "
                 "the time, so comparing against zero misleads - comparing "
                 "against each sector's own history is the fairer reading.",
        "pro": "Each series is z-scored on its own full-sample mean and "
               "standard deviation. The raw index is level-biased positive, "
               "so standardisation makes departures from a sector's own "
               "norm legible.",
    },
    "sent_ylabel_z": {"plain": "How unusual the tone is (z-score)",
                      "pro": "Standardised score (z)"},
    "sent_title": {"plain": "News tone by sector over time",
                   "pro": "Sector news-sentiment index (VADER compound, "
                          "lagged 1 trading day)"},
    "sent_disclaimer": {
        "plain": "The sentiment index describes news tone; it is not a "
                 "buy or sell signal.",
        "pro": "The sentiment index describes news tone; it is not a "
               "buy or sell signal.",
    },
    "posbias_caption": {
        "plain": "Every sector's average reading is positive (from "
                 "{lo:.2f} to {hi:.2f}), and only {pmin:.1f}%-{pmax:.1f}% "
                 "of daily readings fall below zero. Compare a sector "
                 "against its own usual level rather than against zero.",
        "pro": "All sector means are positive ({lo:.2f} to {hi:.2f}); "
               "{pmin:.1f}%-{pmax:.1f}% of daily readings are negative. "
               "Interpret readings relative to each sector's own "
               "distribution, not the zero line.",
    },
    "startdates_caption": {
        "plain": "The index starts 2020-01-02; the funds start 2021-02-01 "
                 "because the first 252 trading days are used to estimate "
                 "the first set of fund weights.",
        "pro": "The index starts 2020-01-02; the funds start 2021-02-01 "
               "because the first 252 trading days are used to estimate "
               "the first set of fund weights.",
    },
    # --- "how to read this chart" captions (plain mode only) ------------------
    "cap_growth": {
        "plain": "$1 invested on the first day, followed to the last. The "
                 "dotted lines mark named market events.",
        "pro": "$1 invested on the first day, followed to the last. The "
               "dotted lines mark named market events.",
    },
    "cap_drawdown": {
        "plain": "How far below its own previous high point the fund sat "
                 "on each day. 0% means it was at a new high.",
        "pro": "How far below its own previous high point the fund sat on "
               "each day. 0% means it was at a new high.",
    },
    "cap_weights_area": {
        "plain": "Each coloured band is one asset's share of the fund's "
                 "money; a thicker band means a bigger share. Weights "
                 "change only at monthly rebalances, so each flat block is "
                 "one month. The five largest holdings are shown; the rest "
                 "of the fund is spread across all other assets.",
        "pro": "Each band is one asset's share of the fund. Weights change "
               "only at monthly rebalances; each flat block is one month. "
               "Top 5 shown; the remainder is spread across all other "
               "assets.",
    },
    "cap_holdings_bar": {
        "plain": "The fund's ten largest positions at the most recent "
                 "rebalance, as a share of the fund's money.",
        "pro": "The fund's ten largest positions at the most recent "
               "rebalance, as a share of the fund's money.",
    },
    "cap_sentiment_chart": {
        "plain": "Each line is one sector you selected. Higher means more "
                 "positive news wording that day, averaged over your "
                 "chosen window.",
        "pro": "Each line is one selected sector. Higher means more "
               "positive news wording that day, smoothed over the chosen "
               "window.",
    },
    # --- practice tab -------------------------------------------------------
    "practice_heading": {"plain": "Practice - the investment time machine",
                         "pro": "Practice - historical replay"},
    "setup_intro": {
        "plain": "Pick a start date, an amount, and a starting mix. The "
                 "simulation then replays real history day by day, and you "
                 "can change the mix or add and take out money along the "
                 "way. No real money is involved.",
        "pro": "Configure a start date, capital, and target allocation. "
               "The engine replays realised fund returns day by day from "
               "that date; allocations and cash flows can be adjusted at "
               "any point on the timeline.",
    },
    "start_date_label": {"plain": "Start date", "pro": "Start date"},
    "start_mix_label": {"plain": "Starting mix ($)",
                        "pro": "Starting mix ($)"},
    "step1": {"plain": "① Pick your start date", "pro": "1. Start date"},
    "step2": {"plain": "② How much do you start with?",
              "pro": "2. Amount"},
    "step3": {"plain": "③ Spread it across the funds",
              "pro": "3. Allocation"},
    "step4": {"plain": "④ Choose how to travel", "pro": "4. Mode"},
    "alloc_step1": {"plain": "① How much do you want to invest?",
                    "pro": "1. Amount"},
    "alloc_step2": {"plain": "② Place it across the funds",
                    "pro": "2. Allocation"},
    "start_button": {"plain": "Start travelling", "pro": "Start travelling"},
    "you_are_here": {"plain": "You are here - {date}",
                     "pro": "Simulation date - {date}"},
    "continuation_label": {
        "plain": "Same holdings afterwards (not a forecast)",
        "pro": "Same holdings afterwards (not a forecast)",
    },
    "paidin_label": {"plain": "Paid in (net)", "pro": "Paid in (net)"},
    "practice_chart_title": {"plain": "Your portfolio value over time",
                             "pro": "Simulated portfolio value"},
    "slider_label": {"plain": "Timeline - drag to travel",
                     "pro": "Timeline"},
    # --- blind walk (the future is hidden) ---------------------------------
    "mode_label": {"plain": "Choose how to practise",
                   "pro": "Choose how to practise"},
    "mode_replay": {"plain": "Replay - see the whole timeline",
                    "pro": "Replay"},
    "mode_blind": {"plain": "Blind walk - the future is hidden",
                   "pro": "Blind walk"},
    "mode_replay_cap": {
        "plain": "Travel back and forth with the full timeline in view.",
        "pro": "Travel back and forth with the full timeline in view.",
    },
    "mode_blind_cap": {
        "plain": "Step forward through time without seeing what comes "
                 "next. Events and news reach you only when you reach "
                 "them - like living it for real.",
        "pro": "Forward movement is stepwise; the chart, events and "
               "sentiment are revealed only up to the current date.",
    },
    "pace_label": {"plain": "Pace", "pro": "Pace"},
    "pace_month": {"plain": "A month at a time", "pro": "Monthly"},
    "pace_day": {"plain": "Day by day", "pro": "Daily"},
    "jump_label": {"plain": "Jump to a date", "pro": "Jump to a date"},
    "jump_go": {"plain": "Jump", "pro": "Jump"},
    "walk_intro_title": {"plain": "New here? Three things to know",
                         "pro": "Orientation"},
    "walk_intro_body": {
        "plain": "① Drag the timeline (or press ▶) to travel through "
                 "time. ② Shaded stretches slow time to one day at a "
                 "time - that is where the interesting things happen. "
                 "③ Cards below explain what just happened, using your "
                 "own numbers.",
        "pro": "Drag or step the timeline; turbulent windows switch to "
               "daily steps; learning cards fire on thresholds.",
    },
    "walk_intro_dismiss": {"plain": "Got it", "pro": "Got it"},
    "jump_note": {
        "plain": "However you travel, forward movement always pauses when "
                 "a turbulent stretch begins - storms are part of the "
                 "practice.",
        "pro": "All forward travel halts at the next turbulent window's "
               "start date.",
    },
    "restart_walk": {"plain": "Restart walk", "pro": "Restart walk"},
    "restart_note": {
        "plain": "Back to your start date with the future hidden again.",
        "pro": "Reset to the start date; revealed range and decisions "
               "cleared.",
    },
    # --- daily summary (the "today at a glance" digest) --------------------
    "day_title": {"plain": "Today: {date}", "pro": "Date: {date}"},
    "day_first": {"plain": "Day one: you set off with {amount}.",
                  "pro": "Inception: {amount} invested."},
    "day_change": {
        "plain": "Your portfolio {direction} \\${abs_chg:,.0f} "
                 "({pct_chg:+.1f}%) to \\${value:,.0f}.",
        "pro": "Daily change {pct_chg:+.2f}% (\\${abs_chg:,.0f}) to "
               "\\${value:,.0f}.",
    },
    "day_driver": {
        "plain": "Biggest driver: {fund} ({fund_ret:+.1f}% that day, "
                 "moving your mix by {contrib:+.1f} percentage points).",
        "pro": "Largest contribution: {fund} ({fund_ret:+.2f}% x weight "
               "= {contrib:+.2f} pp).",
    },
    "day_driver_none": {"plain": "No single fund drove the move.",
                        "pro": "No dominant single-fund contribution."},
    "day_flow": {"plain": "You {verb} \\${flow:,.0f} today.",
                 "pro": "Cash flow: {verb} \\${flow:,.0f}."},
    "news_mood_title": {"plain": "The news mood right now",
                        "pro": "News mood at this date"},
    "news_mood_caption": {
        "plain": "Each sector's tone is compared with its own history UP "
                 "TO THIS DATE only - nothing from the future leaks in.",
        "pro": "Z-scores use expanding past-only statistics up to the "
               "simulation date.",
    },
    "news_mood_none": {
        "plain": "Not enough history yet to say how unusual the tone is.",
        "pro": "Insufficient history for a past-only z-score yet.",
    },
    "news_mood_empty": {
        "plain": "Your mix is all in crypto right now - headlines cover "
                 "only the 50 shares, so there is no news mood to show.",
        "pro": "The mix is fully in crypto; the headline data covers only "
               "the equity universe.",
    },
    "debrief_title": {"plain": "Your blind walk - the debrief",
                      "pro": "Blind-walk debrief"},
    "debrief_body": {
        "plain": "You made {n} change(s) after setting off. Your path "
                 "ended at {mine}. If you had never touched your starting "
                 "mix, it would have ended at {bh}. The gap between the two "
                 "numbers is the effect of your own choices - what it "
                 "means is yours to judge.",
        "pro": "{n} allocation/cash decisions after inception. Final value "
               "{mine}; untouched starting mix {bh}. The difference is the "
               "behavioural component of the result, stated without "
               "evaluation.",
    },
    "debrief_chart_title": {"plain": "Your path vs never touching the "
                                     "starting mix",
                            "pro": "Decision path vs buy-and-hold of the "
                                   "initial mix"},
    "debrief_you": {"plain": "Your path", "pro": "Decision path"},
    "debrief_bh": {"plain": "Starting mix, untouched",
                   "pro": "Buy-and-hold"},

    "slider_caption": {
        "plain": "The slider moves one day at a time over the days the "
                 "data covers: the crypto fund trades every day, so the "
                 "share funds simply stand still on days the stock market "
                 "is closed. Inside shaded turbulent stretches every day "
                 "is shown.",
        "pro": "The slider steps over every date in the sample (the crypto "
               "fund trades daily; equity funds are flat on non-trading "
               "days). Inside shaded turbulent stretches every day is "
               "shown.",
    },
    "turbulent_banner": {
        "plain": "Turbulent stretch: {label} ({start} to {end}). The "
                 "simulation marks this period as turbulent; every day is "
                 "shown on the slider.",
        "pro": "Turbulent window: {label} ({start} to {end}). The "
               "simulation marks this period as turbulent; every day is "
               "shown on the slider.",
    },
    "status_date": {"plain": "Current date", "pro": "Current date"},
    "status_value": {"plain": "Portfolio value", "pro": "Portfolio value"},
    "status_paid": {"plain": "Paid in (net)", "pro": "Paid in (net)"},
    "status_peak": {"plain": "Highest so far", "pro": "Running peak"},
    "status_date_gloss": {"plain": "Where you are in time", "pro": ""},
    "status_value_gloss": {"plain": "What the portfolio is worth on this "
                                    "date", "pro": ""},
    "status_paid_gloss": {"plain": "Money put in minus money taken out",
                          "pro": ""},
    "status_peak_gloss": {"plain": "The highest value reached so far",
                          "pro": ""},
    "change_heading": {"plain": "Make a change on this date",
                       "pro": "Make a change on this date"},
    "change_mix_tab": {"plain": "Change the mix", "pro": "Change the mix"},
    "change_money_tab": {"plain": "Add or take out money",
                         "pro": "Add or take out money"},
    "mix_apply": {"plain": "Apply the new mix", "pro": "Apply the new mix"},
    "mix_hint": {"plain": "The button activates once the total is above "
                          "$0.",
                 "pro": "The button activates once the total is above $0."},
    "mix_note": {
        "plain": "Amounts express proportions: the new mix is applied to "
                 "whatever your portfolio is worth on this date.",
        "pro": "Amounts are normalised and applied to the portfolio's "
               "current value.",
    },
    "money_amount": {"plain": "Amount ($)", "pro": "Amount ($)"},
    "money_add": {"plain": "Add money", "pro": "Contribute"},
    "money_take": {"plain": "Take out money", "pro": "Withdraw"},
    "money_apply": {"plain": "Apply", "pro": "Apply"},
    "withdraw_cap": {"plain": "Taking out is capped at the current "
                              "portfolio value (${val:,.0f}).",
                     "pro": "Withdrawals are capped at the current "
                            "portfolio value (${val:,.0f})."},
    "decisions_heading": {"plain": "Your decisions so far",
                          "pro": "Decision log"},
    "dec_start": {"plain": "Started with ${amount:,.0f} and the starting "
                           "mix",
                  "pro": "Initial allocation of ${amount:,.0f}"},
    "dec_mix": {"plain": "Changed the mix", "pro": "Rebalanced to a new "
                                                   "target mix"},
    "dec_add": {"plain": "Added ${amount:,.0f}", "pro": "Contributed "
                                                       "${amount:,.0f}"},
    "dec_withdraw": {"plain": "Took out ${amount:,.0f}",
                     "pro": "Withdrew ${amount:,.0f}"},
    "start_again": {"plain": "Start again", "pro": "Start again"},
}

# ---------------------------------------------------------------------------
# PRACTICE_COPY - the single static dictionary holding every learning-card
# string for the Practice tab, in professional and plain versions. Cards
# state facts about the user's own numbers only; they never evaluate a
# decision. Placeholders are filled with the user's own simulated figures.
# ---------------------------------------------------------------------------
PRACTICE_COPY = {
    "dd_10": {
        "title": {"plain": "A 10% fall from your peak",
                  "pro": "Drawdown beyond -10%"},
        "body": {
            "plain": "Your portfolio is worth ${value:,.0f}, which is "
                     "{dd:.0f}% below its highest point of ${peak:,.0f} "
                     "(reached {peak_date}). A fall from your own highest "
                     "point is called a drawdown. It is measured from your "
                     "peak, not from the money you put in.",
            "pro": "The portfolio has crossed a -10% drawdown: value "
                   "${value:,.0f} versus a running peak of ${peak:,.0f} on "
                   "{peak_date} ({dd:.1f}%). Drawdown is measured "
                   "peak-to-trough against the position's own high, not "
                   "against contributions.",
        },
    },
    "dd_20": {
        "title": {"plain": "A 20% fall from your peak",
                  "pro": "Drawdown beyond -20%"},
        "body": {
            "plain": "Your portfolio is worth ${value:,.0f}, now {dd:.0f}% "
                     "below its highest point of ${peak:,.0f} (reached "
                     "{peak_date}). This is the deepest fall from a peak in "
                     "your simulation so far.",
            "pro": "The portfolio has crossed a -20% drawdown: value "
                   "${value:,.0f} versus a running peak of ${peak:,.0f} on "
                   "{peak_date} ({dd:.1f}%).",
        },
    },
    "big_day": {
        "title": {"plain": "A large single-day move",
                  "pro": "Daily move beyond +/-2 standard deviations"},
        "body": {
            "plain": "On {date} your portfolio moved {move:+.1f}% in a "
                     "single day. Over the sample, the Combined "
                     "Equal-Weight fund's typical daily swing was about "
                     "+/-1.3%, so a move beyond +/-{band:.1f}% counts as "
                     "unusual in this dataset: it happened on {n} of {N} "
                     "trading days for that fund.",
            "pro": "The portfolio's daily change of {move:+.2f}% on "
                   "{date} lies beyond +/-2 standard deviations "
                   "(+/-{band:.2f}%) of the Combined Equal-Weight fund's "
                   "daily-return distribution; {n} of {N} sample days "
                   "exceeded that band.",
        },
    },
    "drift": {
        "title": {"plain": "Your mix has drifted",
                  "pro": "Weight drift beyond 5 percentage points"},
        "body": {
            "plain": "{fund} now makes up {actual:.1f}% of your "
                     "portfolio, against the {target:.1f}% you last set - "
                     "a gap of {gap:.1f} percentage points. This happens "
                     "because each fund grows at its own pace when the mix "
                     "is not reset.",
            "pro": "Active weights have drifted from target: {fund} is "
                   "{actual:.1f}% of portfolio value versus a "
                   "{target:.1f}% target ({gap:.1f} pp). Weights drift "
                   "because holdings compound at different rates between "
                   "rebalances.",
        },
    },
    "turbulent": {
        "title": {"plain": "A turbulent stretch",
                  "pro": "Turbulent window"},
        "body": {
            "plain": "You have entered a stretch the simulation marks as "
                     "turbulent: {label}, {start} to {end}. In this window "
                     "the Combined Equal-Weight fund moved by more than "
                     "twice its typical daily swing on several days.",
            "pro": "The simulation date has entered a turbulent window: "
                   "{label} ({start} - {end}), defined by daily moves in "
                   "the Combined Equal-Weight fund beyond +/-2 standard "
                   "deviations or by a named market event.",
        },
    },
    "end": {
        "title": {"plain": "The end of the data",
                  "pro": "End of sample"},
        "body": {
            "plain": "You have reached {date}, the last day in the "
                     "dataset. The simulation stops here because the "
                     "project data ends on 31 December 2023; nothing "
                     "later is part of this historical record.",
            "pro": "End of sample reached ({date}). The dataset ends "
                   "2023-12-31; no later observations exist in this "
                   "project.",
        },
    },
}


# ---------------------------------------------------------------------------
# Copy helpers
# ---------------------------------------------------------------------------

def lang() -> str:
    """Current language mode: 'plain' (default) or 'pro'."""
    return "pro" if st.session_state.get("lang") == "Professional" else "plain"


def T(key: str) -> str:
    """Look up a static paired string in the current language mode."""
    return COPY[key][lang()]


def card_text(card: str, part: str, **kwargs) -> str:
    """Look up a PRACTICE_COPY card string and fill in the user's numbers."""
    return PRACTICE_COPY[card][part][lang()].format(**kwargs)


def fund_line(fund: str) -> str:
    """The fund's static construction line plus the mandated closing line."""
    return COPY[f"line_{fund}"][lang()] + " " + GUARANTEE_LINE


# ---------------------------------------------------------------------------
# Data loading - committed artifacts only, never recomputed
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_data():
    returns = pd.read_csv(RESULTS_DATA / "fund_returns.csv",
                          parse_dates=["date"]).set_index("date")
    weights = pd.read_csv(RESULTS_DATA / "fund_weights.csv",
                          parse_dates=["date"])
    sentiment = pd.read_csv(RESULTS_DATA / "sector_sentiment_index.csv",
                            parse_dates=["date"]).set_index("date")
    metrics = pd.read_csv(RESULTS_TABLES / "performance_metrics.csv",
                          index_col="fund")
    sent_summary = pd.read_csv(RESULTS_TABLES / "sector_sentiment_summary.csv",
                               index_col=0)
    calendar = pd.read_csv(RESULTS_DATA / "event_calendar.csv",
                           parse_dates=["start", "end"])
    return returns, weights, sentiment, metrics, sent_summary, calendar


# ---------------------------------------------------------------------------
# Small computation helpers (weighted arithmetic on committed series only)
# ---------------------------------------------------------------------------

def perf_metrics(r: pd.Series, p: float) -> dict:
    """Annualised return/vol/Sharpe (rf = 0) and max drawdown.

    Uses the same formulas as the Station 3 pipeline, with p periods per
    year supplied by the caller.
    """
    r = r.dropna()
    n = len(r)
    wealth = (1.0 + r).cumprod()
    return {
        "ann_return": float(wealth.iloc[-1] ** (p / n) - 1.0),
        "ann_vol": float(r.std(ddof=1) * np.sqrt(p)),
        "sharpe": float(r.mean() / r.std(ddof=1) * np.sqrt(p)),
        "max_drawdown": float((wealth / wealth.cummax() - 1.0).min()),
        "n_days": int(n),
    }


def _method_key(fund: str) -> str:
    """Construction method of a fund, derived from its name - the name IS
    the recipe (same derive-from-name pattern as PERIODS_PER_YEAR)."""
    if "Equal-Weight" in fund:
        return "equal_weight"
    if "Min-Variance" in fund:
        return "min_variance"
    if "Max-Sharpe" in fund:
        return "max_sharpe"
    if "Risk-Parity" in fund:
        return "risk_parity"
    return "tilt"  # Equity+Sentiment Tilt


def _mechanism_stats(weights: pd.DataFrame, fund: str) -> dict:
    """Latest-rebalance weight facts for the worked construction example.

    Plain arithmetic on the committed fund_weights.csv only - no
    optimisation runs in the app (brief rule 3).
    """
    sub = weights[weights["fund"] == fund]
    row = (sub[sub["date"] == sub["date"].max()]
           .set_index("ticker")["weight"])
    nz = row[row > 1e-9]
    n = len(row)
    return {
        "date": sub["date"].max().strftime("%Y-%m-%d"),
        "n": n,
        "n_held": len(nz),
        "n_zero": n - len(nz),
        "top": row.idxmax(),
        "top_w": float(row.max()) * 100,
        "max_w": float(row.max()) * 100,
        "min_w": float(nz.min()) * 100,
        "eq_w": 100.0 / n,
    }


def weight_change_pp(weights: pd.DataFrame, fund: str) -> tuple[float, int]:
    """Mean total absolute weight change per rebalance (pp) + rebalance count."""
    sub = (weights[weights["fund"] == fund]
           .pivot(index="date", columns="ticker", values="weight")
           .sort_index())
    change = sub.fillna(0.0).diff().abs().sum(axis=1).iloc[1:]
    return float(change.mean() * 100.0), int(len(sub))


def current_holdings(weights: pd.DataFrame, fund: str) -> pd.Series:
    """Target weights at the fund's most recent rebalance."""
    sub = weights[weights["fund"] == fund]
    latest = sub[sub["date"] == sub["date"].max()]
    return latest.set_index("ticker")["weight"].sort_values(ascending=False)


# ---------------------------------------------------------------------------
# Chart helpers (shared chart standards)
# ---------------------------------------------------------------------------

def date_axis(ax, index, max_ticks: int = 6,
              extend_right: float = 0.0) -> None:
    """Format a date axis: at most ~6 tick labels like 'Jan 2021'.

    Ticks are pinned to the data range (so extending the view to the right
    for end-of-line labels never creates ticks past the last data point).
    """
    index = pd.DatetimeIndex(index)
    span_months = max(1, (index[-1].year - index[0].year) * 12
                      + index[-1].month - index[0].month)
    interval = max(1, (span_months + max_ticks - 1) // max_ticks)
    locator = mdates.MonthLocator(interval=interval)
    x0n, x1n = mdates.date2num(index[0]), mdates.date2num(index[-1])
    ax.xaxis.set_major_locator(mticker.FixedLocator(
        locator.tick_values(mdates.num2date(x0n), mdates.num2date(x1n))))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    if extend_right > 0.0:
        ax.set_xlim(x0n, x1n + extend_right * (x1n - x0n))
    ax.tick_params(axis="x", rotation=0, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)


def money_axis(ax) -> None:
    """Format a money axis as $ with thousands separators.

    Decimal places adapt to the plotted range so small-value charts (for
    example growth of $1) do not collapse several ticks onto one label.
    """
    lo, hi = ax.get_ylim()
    span = abs(hi - lo)
    decimals = 0 if span >= 20 else (1 if span >= 2 else 2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _pos: f"${x:,.{decimals}f}"))


def title_ax(ax, text: str, strip: bool = False) -> None:
    """Set a chart title, lifted clear of the event-marker strip if present."""
    ax.set_title(text, fontsize=10, pad=44 if strip else 10)


_NAMED_LABELS = {e["label"] for e in NAMED_EVENTS}


def add_event_markers(ax, calendar, x0, x1):
    """Dotted vertical lines at event windows + horizontal labels above.

    Labels sit in a reserved strip above the plot (rotation 0); unnamed
    windows show as 'Turbulent' to keep the strip readable. When two labels
    would collide they stagger onto a second row; if a third row would be
    needed, every marker falls back to a number and a caption string is
    returned for the caller to render.
    """
    sel = calendar[(calendar["end"] >= x0) & (calendar["start"] <= x1)]
    if sel.empty:
        return None
    x0n, x1n = mdates.date2num(x0), mdates.date2num(x1)
    items = []
    for _, row in sel.sort_values("start").iterrows():
        label = str(row["label"])
        # Only the four NAMED market events earn a marker. Generic
        # "Turbulent stretch" windows repeat one meaningless word and made
        # it impossible to tell which label belonged to which line; they
        # still appear as shaded bands in the Practice tab, where they
        # actually drive the simulation's behaviour.
        if label not in _NAMED_LABELS:
            continue
        marker = min(max(row["start"], x0), x1)  # clip marker into view
        items.append((mdates.date2num(marker), label))
    if not items:
        return None

    # The collision test is text-width aware: ~3.4pt per character at the
    # 7pt label size, converted from axes fraction into the x-axis
    # (date-number) units used below.
    span = x1n - x0n
    axes_width_pt = ax.figure.get_figwidth() * 0.87 * 72.0
    char_frac = 3.4 / axes_width_pt

    # Row layout. First choice: one clean row (the tightened width
    # estimate makes this possible in most cases). If labels genuinely
    # collide, use a deliberate 0-1-0-1 checkerboard rather than a
    # single stray label on a second row, which reads as accidental.
    # Densest case falls back to numbered markers plus a caption.
    trans = ax.get_xaxis_transform()  # x in data units, y in axes fraction
    for mn, _label in items:
        ax.axvline(mn, color=MUTED, lw=1.0, ls=(0, (2, 2)), zorder=1)

    def halfwidth(label: str) -> float:
        return 0.5 * len(label) * char_frac * span

    def collide(i: int, j: int) -> bool:
        (mi, li), (mj, lj) = items[i], items[j]
        return abs(mj - mi) < halfwidth(li) + halfwidth(lj) + 0.004 * span

    n = len(items)
    if not any(collide(i, i + 1) for i in range(n - 1)):
        rows = [0] * n
    elif n <= 6 and not any(collide(i, i + 2) for i in range(n - 2)):
        rows = [i % 2 for i in range(n)]
    else:
        rows = None
    if rows is not None:
        for (mn, label), row in zip(items, rows):
            # Edge-aware alignment keeps labels inside the plot: a label
            # centred on a marker near the left/right edge would spill
            # out of the axes.
            frac = (mn - x0n) / span
            ha = "left" if frac < 0.08 else ("right" if frac > 0.92 else "center")
            ax.text(mn, 1.05 + row * 0.09, label, transform=trans,
                    fontsize=7, ha=ha, va="bottom", color=MUTED)
        return None
    for i, (mn, _label) in enumerate(items, start=1):
        ax.text(mn, 1.05, str(i), transform=trans, fontsize=8,
                ha="center", va="bottom", color=MUTED, weight="bold")
    return "Markers: " + "; ".join(
        f"{i} = {label}" for i, (_mn, label) in enumerate(items, start=1))


def shade_windows(ax, calendar, x0, x1) -> None:
    """Shade turbulent windows grey behind the data."""
    sel = calendar[(calendar["end"] >= x0) & (calendar["start"] <= x1)]
    for _, row in sel.iterrows():
        ax.axvspan(max(row["start"], x0), min(row["end"], x1),
                   color=LIGHT_GREY, alpha=0.6, zorder=0)


def new_fig(width: float, height: float):
    """Figure with headroom reserved for the event-marker strip."""
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(top=0.72, left=0.10, right=0.97, bottom=0.12)
    return fig, ax


def fmt_money(v: float) -> str:
    return f"${v:,.0f}"


def fmt_date(d) -> str:
    return pd.Timestamp(d).strftime("%d %b %Y")


# ---------------------------------------------------------------------------
# Landing (first visit only)
# ---------------------------------------------------------------------------

def _go(tab: str) -> None:
    st.session_state["started"] = True
    st.session_state["nav"] = tab


def landing() -> None:
    st.markdown(
        '<div class="hero">'
        '<div class="hero-kicker">Evidence, not advice</div>'
        '<div class="hero-title">HyperInvest</div>'
        f'<div class="hero-sub">{T("landing_tagline")}</div>'
        '<div class="stat-strip">12 funds · 3 years of history '
        '(2021-2023) · ~147,000 headlines · 10 sectors</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.button(T("landing_btn_funds"), key="choice_funds",
                  on_click=_go, args=("Funds",), use_container_width=True)
        st.caption(T("landing_cap_funds"))
    with c2:
        st.button(T("landing_btn_practice"), key="choice_practice",
                  on_click=_go, args=("Practice",), use_container_width=True)
        st.caption(T("landing_cap_practice"))


# ---------------------------------------------------------------------------
# Tab 1 - Funds
# ---------------------------------------------------------------------------

def _fmt_metric(key: str, v: float) -> str:
    if key == "sharpe":
        return f"{v:.2f}"
    return f"{v * 100:.1f}%"


_GLOSS_KEYS = {"ann_return": "gloss_ann_return", "ann_vol": "gloss_ann_vol",
               "sharpe": "gloss_sharpe", "max_drawdown": "gloss_max_dd"}


def _gloss(key: str, row: pd.Series) -> str:
    v = row[key] if key == "sharpe" else row[key] * 100
    return COPY[_GLOSS_KEYS[key]]["plain"].format(v=v, usd=100.0 + v)


def _growth_chart(returns: pd.Series, calendar, fund: str):
    r = returns.dropna()
    wealth = (1.0 + r).cumprod()
    fig, ax = new_fig(6.2, 3.6)
    ax.plot(wealth.index, wealth.values, color=TEAL, lw=1.5)
    ax.axhline(1.0, color=CHARCOAL, lw=0.8, ls="--")
    title_ax(ax, T("growth_title").format(fund=fund), strip=True)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Value of \\$1 (USD)", fontsize=9)
    date_axis(ax, wealth.index)
    money_axis(ax)
    cap = add_event_markers(ax, calendar, wealth.index[0], wealth.index[-1])
    return fig, cap


def _drawdown_chart(returns: pd.Series, calendar, fund: str):
    r = returns.dropna()
    wealth = (1.0 + r).cumprod()
    dd = (wealth / wealth.cummax() - 1.0) * 100.0
    fig, ax = new_fig(6.2, 3.6)
    ax.fill_between(dd.index, dd.values, 0.0, color=MAROON, alpha=0.8)
    title_ax(ax, T("drawdown_title").format(fund=fund), strip=True)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Fall from previous peak (%)", fontsize=9)
    date_axis(ax, dd.index)
    cap = add_event_markers(ax, calendar, dd.index[0], dd.index[-1])
    return fig, cap


def _holdings_over_time(weights: pd.DataFrame, fund: str) -> None:
    """Measured three-tier rule based on mean |weight change| per rebalance."""
    change_pp, n_reb = weight_change_pp(weights, fund)
    if change_pp < 1.0:
        st.write(T("holdings_tier1").format(ch=change_pp, n_reb=n_reb))
        return
    if change_pp < 10.0:
        st.write(T("holdings_tier2").format(ch=change_pp, n_reb=n_reb))
        _current_holdings_bar(weights, fund)
        return
    sub = (weights[weights["fund"] == fund]
           .pivot(index="date", columns="ticker", values="weight")
           .sort_index() * 100.0)
    top5 = sub.mean().nlargest(5).index.tolist()
    other = sub.drop(columns=top5).sum(axis=1)
    # Weights only change at each monthly rebalance and are constant in
    # between. Plotting just the monthly points lets matplotlib connect
    # them with straight diagonal lines, inventing gradual "ramps" that
    # never happened. Reindexing to a daily grid and forward-filling
    # renders the honest shape instead: flat within each month, one
    # vertical jump at each rebalance.
    daily_idx = pd.date_range(sub.index.min(), sub.index.max(), freq="D")
    stepped = sub.reindex(daily_idx).ffill()
    # The grey "Other" band dominated the canvas on diversified funds (up
    # to ~90% of the area) and squashed the named holdings into unreadable
    # strips. The chart now shows the top 5 only, with the y-axis fitted
    # to them; the caption states that the rest is pooled away.
    fig, ax = new_fig(9.5, 4.2)
    fig.subplots_adjust(bottom=0.22)  # room for the legend under the chart
    ax.stackplot(stepped.index, [stepped[t] for t in top5],
                 labels=top5,
                 colors=STACK_COLORS,
                 edgecolor="white", linewidth=0.4)
    title_ax(ax, T("holdings_chart_title").format(top=sub.mean().max()))
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Weight (%)", fontsize=9)
    ymax = float(stepped[top5].sum(axis=1).max())
    ax.set_ylim(0, max(ymax * 1.15, 5.0))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncols=6,
              fontsize=8, frameon=False)
    date_axis(ax, stepped.index)
    st.pyplot(fig)
    plt.close(fig)
    if lang() == "plain":
        st.caption(T("cap_weights_area"))


def _current_holdings_bar(weights: pd.DataFrame, fund: str) -> None:
    cur = current_holdings(weights, fund).head(10).iloc[::-1]
    as_of = fmt_date(weights[weights["fund"] == fund]["date"].max())
    fig, ax = new_fig(9.5, 3.4)
    ax.barh(cur.index, cur.values * 100.0, color=TEAL, height=0.65)
    ax.set_title(T("current_bar_title").format(date=as_of), fontsize=10)
    ax.set_xlabel("Weight (%)", fontsize=9)
    ax.set_ylabel("Holding", fontsize=9)
    ax.set_xlim(left=0)
    fig.subplots_adjust(left=0.16)
    st.pyplot(fig)
    plt.close(fig)
    if lang() == "plain":
        st.caption(T("cap_holdings_bar"))


def _current_holdings(weights: pd.DataFrame, fund: str,
                      already_shown: bool) -> None:
    cur = current_holdings(weights, fund)
    spread_pp = float((cur.max() - cur.min()) * 100.0)
    if spread_pp >= 0.5:
        if not already_shown:
            _current_holdings_bar(weights, fund)
    else:
        as_of = fmt_date(weights[weights["fund"] == fund]["date"].max())
        st.write(T("current_equal").format(n=len(cur), w=100.0 / len(cur),
                                           date=as_of))


def tab_funds(returns, weights, metrics, calendar) -> None:
    st.header(T("funds_heading"))
    with st.popover(T("about_data_title")):
        st.caption(T("sample_period"))
        st.caption(T("backtest_basis"))

    disp = metrics.loc[FUND_ORDER, METRIC_KEYS].copy()
    disp["ann_return"] *= 100.0
    disp["ann_vol"] *= 100.0
    disp["max_drawdown"] *= 100.0
    disp = disp.reset_index().rename(columns={"fund": "Fund"})
    st.dataframe(
        disp,
        column_config={
            "ann_return": st.column_config.NumberColumn(
                metric_name("ann_return"), format="%.1f%%"),
            "ann_vol": st.column_config.NumberColumn(
                metric_name("ann_vol"), format="%.1f%%"),
            "sharpe": st.column_config.NumberColumn(
                metric_name("sharpe"), format="%.2f"),
            "max_drawdown": st.column_config.NumberColumn(
                metric_name("max_drawdown"), format="%.1f%%"),
        },
        hide_index=True,
        width="stretch",
    )
    st.caption(T("sorting_caption"))

    if lang() == "plain":
        with st.expander(T("funds_explain_title"), expanded=True):
            st.markdown(T("funds_explain_body"))

    cew = metrics.loc["Combined Equal-Weight"]
    rp = metrics.loc["Combined Risk-Parity"]
    cr = metrics.loc["Crypto Max-Sharpe"]
    with st.expander(T("howto_title"), expanded=False):
        st.markdown(T("howto_body").format(
            cew_ret=cew["ann_return"] * 100,
            cew_100=100 + cew["ann_return"] * 100,
            rp_vol=rp["ann_vol"] * 100,
            cr_vol=cr["ann_vol"] * 100, rp_sh=rp["sharpe"],
            rp_sh_cents=rp["sharpe"] * 100,
            cr_dd=cr["max_drawdown"] * 100,
            cr_dd_usd=100 + cr["max_drawdown"] * 100))

    fund = st.selectbox(T("choose_fund"), FUND_ORDER)
    row = metrics.loc[fund]
    cols = st.columns(4)
    for col, key in zip(cols, METRIC_KEYS):
        col.metric(metric_name(key), _fmt_metric(key, row[key]),
                   help=_gloss(key, row) if lang() == "plain" else None)
    if lang() == "plain":
        st.markdown(f"**{FUND_ONELINER[fund]}**")
    with st.expander(T("how_built_title"), expanded=False):
        st.markdown(f"**Universe:** {UNIVERSE[fund]}.  \n"
                    f"**Method:** {fund_line(fund)}")
        mk = _method_key(fund)
        if lang() == "pro":
            st.latex(METHOD_FORMULA[mk])
            st.caption(T("formula_symbols"))
            note = T(f"formula_note_{mk}")
            if note:
                st.caption(note)
        else:
            st.markdown(T(f"worked_{mk}").format(
                **_mechanism_stats(weights, fund)))
        st.caption(T("backtest_basis"))

    c1, c2 = st.columns(2)
    fig, cap = _growth_chart(returns[fund], calendar, fund)
    c1.pyplot(fig)
    plt.close(fig)
    if cap:
        c1.caption(cap)
    if lang() == "plain":
        c1.caption(T("cap_growth"))
    fig, cap = _drawdown_chart(returns[fund], calendar, fund)
    c2.pyplot(fig)
    plt.close(fig)
    if cap:
        c2.caption(cap)
    if lang() == "plain":
        c2.caption(T("cap_drawdown"))

    change_pp, _n = weight_change_pp(weights, fund)
    _holdings_over_time(weights, fund)
    _current_holdings(weights, fund, already_shown=1.0 <= change_pp < 10.0)


# ---------------------------------------------------------------------------
# Tab 2 - My Allocation
# ---------------------------------------------------------------------------

def _latest_weights(weights: pd.DataFrame, fund: str) -> pd.Series:
    """A fund's target weights at its most recent rebalance."""
    f = weights[weights["fund"] == fund]
    latest = f[f["date"] == f["date"].max()]
    return latest.set_index("ticker")["weight"]


def blend_sector_exposure(allocs: dict[str, float],
                          weights: pd.DataFrame) -> pd.Series:
    """Sector shares of a blend, from each fund's latest target weights.

    Equity tickers roll up to their sector via SECTOR_MAP; anything else
    (the crypto coins, which have no news coverage) goes to an explicit
    "Crypto" bucket so the no-news share of the mix is stated, not hidden.
    """
    shares: dict[str, float] = {}
    for fund, w in allocs.items():
        if w <= 0:
            continue
        for ticker, tw in _latest_weights(weights, fund).items():
            bucket = SECTOR_MAP.get(ticker, "Crypto")
            shares[bucket] = shares.get(bucket, 0.0) + w * float(tw)
    return pd.Series(shares).sort_values(ascending=False)


def sentiment_tone(sentiment: pd.DataFrame) -> pd.Series:
    """Latest reading as a full-sample z-score, per sector."""
    latest = sentiment.iloc[-1]
    return (latest - sentiment.mean()) / sentiment.std(ddof=0)


def _tone_label(z: float) -> str:
    if z <= -1.5:
        return T("tone_unusually_negative")
    if z >= 1.5:
        return T("tone_unusually_positive")
    return T("tone_usual")


def _news_exposure(allocs: dict[str, float], weights: pd.DataFrame,
                   sentiment: pd.DataFrame, big_title: bool = True) -> None:
    """The bridge panel: blend sector shares beside each sector's latest
    news tone. Descriptive only - the caption carries the neutrality line."""
    shares = blend_sector_exposure(allocs, weights)
    if shares.empty:
        return
    tone = sentiment_tone(sentiment)

    if big_title:
        st.subheader(T("news_exp_title"))
    # A mix with no equity exposure gets a sentence, not a grey wall:
    # a chart must earn its place by carrying information.
    if not any(s != "Crypto" for s in shares.index):
        st.caption(T("news_exp_all_crypto"))
        return
    names = [SECTOR_DISPLAY.get(s, s) if s != "Crypto"
             else T("news_exp_crypto_bucket") for s in shares.index]
    colors = [GREY if s == "Crypto" else TEAL for s in shares.index]
    y = np.arange(len(shares))[::-1]

    fig, ax = new_fig(9.5, max(2.8, 0.45 * len(shares) + 1.6))
    ax.barh(y, shares.values * 100, color=colors, height=0.62)
    ax.set_yticks(y, names, fontsize=9)
    ax.set_xlabel("Share of your mix (%)", fontsize=9)
    xmax = float(shares.max()) * 100
    for yi, s in zip(y, shares.index):
        if s == "Crypto":
            txt = T("news_exp_none")
        else:
            z = float(tone[s])
            txt = f"{_tone_label(z)} (z = {z:+.1f})"
        ax.text(xmax * 1.03, yi, txt, fontsize=8, color=MUTED, va="center")
    ax.set_xlim(0, xmax * 1.55)  # room for the tone labels
    title_ax(ax, T("news_exp_chart_title"))
    st.pyplot(fig)
    plt.close(fig)
    st.caption(T("news_exp_caption"))


# --- asset-family grouping for the allocation inputs -----------------------
# Derived from fund names (a future matrix change cannot misalign it).
# Each family renders in its own tinted, labelled container so users can
# SEE the 4x3 matrix structure instead of reading one long list.
def fund_family(fund: str) -> str:
    if fund.startswith("Combined"):
        return "combined"
    if fund.startswith("Crypto"):
        return "crypto"
    if fund == "Equity+Sentiment Tilt":
        return "tilt"
    return "equity"


FAMILY_TINT = {"combined": ("#E7F2F0", "#BFDDD8"),   # soft teal
               "equity": ("#ECEFF5", "#C9D4E4"),     # soft slate
               "crypto": ("#FAF3DF", "#E8D9A8"),     # soft gold
               "tilt": ("#F5EDF1", "#DCC3D1")}       # soft maroon


def _fund_inputs(prefix: str) -> None:
    """Allocation inputs in DOLLARS, grouped by asset family.

    The user enters amounts; each label shows the live share of the mix
    ("Combined Equal-Weight - 12.5% of your mix"), so the dollar-to-share
    link is taught by seeing, never required as mental arithmetic. Any
    positive total works - proportions are what matter, so there is no
    "must equal 100%" constraint anywhere. Session-state keys stay
    prefix + global index.
    """
    vals = [float(st.session_state.get(f"{prefix}{i}", 0.0))
            for i in range(N_FUNDS)]
    total = sum(vals)
    for family in ("combined", "equity", "crypto", "tilt"):
        idxs = [i for i, f in enumerate(FUND_ORDER)
                if fund_family(f) == family]
        if not idxs:
            continue
        with st.container(key=f"fam_{family}"):
            st.caption(T(f"fam_{family}"))
            cols = st.columns(2)
            for j, i in enumerate(idxs):
                share = (f" - {vals[i] / total * 100:.1f}% of your mix"
                         if total > 0 and vals[i] > 0 else "")
                cols[j % 2].number_input(
                    f"{FUND_ORDER[i]}{share}", min_value=0.0, step=50.0,
                    format="%.0f", key=f"{prefix}{i}",
                    help=fund_line(FUND_ORDER[i]))


def _split_evenly(prefix: str, amount_key: str) -> None:
    # Split the amount-first field evenly; the first fund takes the
    # rounding remainder. Editing the per-fund boxes afterwards moves the
    # total away from this field, and the total line follows the boxes.
    total = float(st.session_state.get(amount_key, 0.0))
    if total <= 0:
        total = 1000.0
    per = round(total / N_FUNDS)
    first = total - per * (N_FUNDS - 1)
    for i in range(N_FUNDS):
        st.session_state[f"{prefix}{i}"] = float(first if i == 0 else per)


def _reset_zero(prefix: str, amount_key: str) -> None:
    """A true clean slate: the fund boxes AND the amount field, so a new
    mix never starts from the previous one's leftovers."""
    for i in range(N_FUNDS):
        st.session_state[f"{prefix}{i}"] = 0.0
    st.session_state[amount_key] = 0.0


def _remove_saved(idx: int) -> None:
    st.session_state["saved_allocs"].pop(idx)


def _save_alloc(allocs: list[float], period: str, amount: float) -> None:
    entry = {
        "ts": pd.Timestamp.now().strftime("%d %b %Y %H:%M"),
        "period": period,
        "alloc": {FUND_ORDER[i]: allocs[i]
                  for i in range(N_FUNDS) if allocs[i] > 0},
        "amount": float(amount),
    }
    st.session_state.setdefault("saved_allocs", []).append(entry)
    # Saving completes the mix: clear the editor so the NEXT mix starts
    # from a clean sheet instead of accumulating on top of this one.
    for i in range(N_FUNDS):
        st.session_state[f"alloc_{i}"] = 0.0
    st.toast(T("saved_toast"))


def _save_start_mix() -> None:
    """The Practice bridge: carry the walk's starting mix into My
    Portfolio, using its own start amount."""
    sim = st.session_state.get("sim")
    if not sim:
        return
    returns, *_ = load_data()
    start_dec = sim["decisions"][0]
    entry = {
        "ts": pd.Timestamp.now().strftime("%d %b %Y %H:%M"),
        "period": f"{fmt_date(returns.index[0])} - "
                  f"{fmt_date(returns.index[-1])}",
        "alloc": {FUND_ORDER[i]: float(w)
                  for i, w in enumerate(start_dec["weights"]) if w > 0},
        "amount": float(start_dec["amount"]),
    }
    st.session_state.setdefault("saved_allocs", []).append(entry)
    st.toast(T("saved_toast"))


def _load_saved(idx: int) -> None:
    """Refill the allocation editor with a saved mix, scaled to the
    current amount field (shares sum to 1, so the gate stays satisfied)."""
    entry = st.session_state["saved_allocs"][idx]
    target = float(st.session_state.get("alloc_total_amount", 1000.0))
    for i, f in enumerate(FUND_ORDER):
        st.session_state[f"alloc_{i}"] = round(
            entry["alloc"].get(f, 0.0) * target, 0)


def _test_in_practice(idx: int) -> None:
    """The reverse bridge (Portfolio -> Practice): load a saved mix into
    the Practice setup with its own amount, and navigate there. Nothing
    starts until the user presses Start travelling - from there they can
    add or withdraw money at any date, which is the honest way to
    "invest more in" or "take money out of" a saved mix."""
    entry = st.session_state["saved_allocs"][idx]
    amount = float(entry.get("amount", 0.0))
    for i, f in enumerate(FUND_ORDER):
        st.session_state[f"setup_alloc_{i}"] = round(
            entry["alloc"].get(f, 0.0) * amount, 0)
    st.session_state["setup_total_amount"] = amount
    st.session_state["nav"] = "Practice"


def _test_total_in_practice() -> None:
    """Load the WHOLE portfolio (all saved mixes combined, dollar-weighted)
    into the Practice setup, so the aggregate becomes walkable like any
    single mix."""
    saved = st.session_state.get("saved_allocs", [])
    if not saved:
        return
    totals = {f: 0.0 for f in FUND_ORDER}
    amount = 0.0
    for e in saved:
        amt = float(e.get("amount", 0.0))
        amount += amt
        for f, share in e["alloc"].items():
            totals[f] += amt * share
    for i, f in enumerate(FUND_ORDER):
        st.session_state[f"setup_alloc_{i}"] = round(totals[f], 0)
    st.session_state["setup_total_amount"] = amount
    st.session_state["nav"] = "Practice"


def _blend_metrics(alloc: dict, returns: pd.DataFrame) -> dict:
    """Blended metrics for a saved mix, from precomputed fund returns."""
    w = np.array([alloc.get(f, 0.0) for f in FUND_ORDER], dtype=float)
    w = w / w.sum()
    blend = pd.Series(returns.fillna(0.0).to_numpy(dtype=float) @ w,
                      index=returns.index)
    p = float(np.dot(w, PERIODS_PER_YEAR))
    return perf_metrics(blend, p)


def tab_allocation(returns, weights, sentiment) -> None:
    st.header(T("alloc_heading"))
    st.caption(T("alloc_intro"))

    st.markdown(f"**{T('alloc_step1')}**")
    st.number_input(T("total_amount_label"), min_value=0.0, value=1000.0,
                    step=100.0, key="alloc_total_amount",
                    help=T("total_amount_help"))
    st.markdown(f"**{T('alloc_step2')}**")
    c1, c2, _ = st.columns([1, 1, 3])
    c1.button(T("split_evenly"), on_click=_split_evenly,
              args=("alloc_", "alloc_total_amount"))
    c2.button(T("reset_zero"), on_click=_reset_zero,
              args=("alloc_", "alloc_total_amount"))

    _fund_inputs("alloc_")

    allocs = [float(st.session_state.get(f"alloc_{i}", 0.0))
              for i in range(N_FUNDS)]
    total = sum(allocs)
    # The amount field is the contract: results appear once the full
    # declared amount is placed - never before, never after.
    target = float(st.session_state.get("alloc_total_amount", 0.0))
    diff = total - target
    st.write(T("placed_line").format(total=total, target=target))
    if target <= 0 and total <= 0:
        st.caption(T("placed_empty"))
        _saved_portfolio(returns, weights, sentiment)
        return
    if diff < -0.5:
        st.caption(T("placed_remaining").format(rem=-diff))
        _saved_portfolio(returns, weights, sentiment)
        return
    if diff > 0.5:
        st.caption(T("placed_over").format(over=diff))
        _saved_portfolio(returns, weights, sentiment)
        return

    # --- blended historical performance (proportions of the dollar mix) ---
    w = np.array(allocs) / total
    # Blended daily return = weighted sum of the committed fund returns
    # (funds contribute 0 before their inception via fillna). Annualisation
    # uses the weighted-average periods per year, sum_i w_i * p_i, with
    # p_i = 252 for equity-calendar funds and 365 for the crypto fund.
    blend = pd.Series(returns.fillna(0.0).to_numpy(dtype=float) @ w,
                      index=returns.index)
    p = float(np.dot(w, PERIODS_PER_YEAR))
    m = perf_metrics(blend, p)
    cols = st.columns(4)
    for col, key in zip(cols, METRIC_KEYS):
        col.metric(metric_name(key), _fmt_metric(key, m[key]))

    amount = total  # the principal IS the dollar total - no separate input
    value = amount * (1.0 + blend).cumprod()
    fig, ax = new_fig(9.5, 4.0)
    ax.plot(value.index, value.values, color=TEAL, lw=1.5)
    ax.axhline(amount, color=CHARCOAL, lw=0.9, ls="--",
               label=T("starting_ref").format(amount=amount)
               .replace("$", "\\$"))  # escape $ against mathtext parsing
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title(T("value_chart_title"), fontsize=10)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Value ($)", fontsize=9)
    date_axis(ax, value.index)
    money_axis(ax)
    st.pyplot(fig)
    plt.close(fig)
    st.caption(T("value_range_caption").format(
        start=fmt_date(value.index[0]), end=fmt_date(value.index[-1]),
        amount=amount, mn=value.min(), mx=value.max(), last=value.iloc[-1])
        + " " + T("assumption_caption"))

    period = f"{fmt_date(value.index[0])} - {fmt_date(value.index[-1])}"
    shares = (np.array(allocs) / total).tolist()
    st.button(T("save_button"), type="primary", on_click=_save_alloc,
              args=(shares, period, total))
    st.caption(T("save_caption"))

    # The bridge to the Sentiment tab: what news tone the mix currently
    # sits in. Fractional fund shares, from precomputed weights only.
    blend_allocs = {FUND_ORDER[i]: shares[i]
                    for i in range(N_FUNDS) if shares[i] > 0}
    _news_exposure(blend_allocs, weights, sentiment)
    _saved_portfolio(returns, weights, sentiment)

def _total_portfolio(saved: list, returns: pd.DataFrame,
                     weights: pd.DataFrame, sentiment: pd.DataFrame) -> None:
    """The user's whole portfolio: all saved mixes combined into one
    aggregate value path. Each mix's dollar growth is summed day by day;
    metrics come from the aggregate's daily returns. Same period and
    assumptions for every mix; historical only."""
    total_value = None
    total_amount = 0.0
    p_num = 0.0
    for e in saved:
        w = np.array([e["alloc"].get(f, 0.0) for f in FUND_ORDER],
                     dtype=float)
        w = w / w.sum()
        blend = returns.fillna(0.0).to_numpy(dtype=float) @ w
        growth = (1.0 + pd.Series(blend, index=returns.index)).cumprod() \
            * e.get("amount", 0.0)
        total_value = growth if total_value is None else total_value + growth
        amt = e.get("amount", 0.0)
        total_amount += amt
        p_num += amt * float(np.dot(w, PERIODS_PER_YEAR))
    daily = total_value.pct_change().fillna(0.0)
    m = perf_metrics(daily, p_num / total_amount)

    st.markdown(f"**{T('total_title')}**")
    st.caption(T("total_placed_line").format(amount=fmt_money(total_amount),
                                      n=len(saved)))
    cols = st.columns(4)
    for col, key in zip(cols, METRIC_KEYS):
        col.metric(metric_name(key), _fmt_metric(key, m[key]))
    fig, ax = new_fig(9.5, 3.6)
    ax.plot(total_value.index, total_value.values, color=TEAL, lw=1.5)
    ax.axhline(total_amount, color=CHARCOAL, lw=0.9, ls="--",
               label=T("total_ref").format(amount=fmt_money(total_amount))
               .replace("$", "\\$"))
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Value ($)", fontsize=9)
    date_axis(ax, total_value.index)
    money_axis(ax)
    st.pyplot(fig)
    plt.close(fig)
    st.caption(T("total_caption"))

    # The aggregate's news exposure: sector shares of the whole portfolio,
    # dollar-weighted across all saved mixes.
    agg: dict[str, float] = {}
    for e in saved:
        amt = e.get("amount", 0.0)
        for f, share in e["alloc"].items():
            agg[f] = agg.get(f, 0.0) + amt * share
    agg = {f: v / total_amount for f, v in agg.items() if v > 0}
    _news_exposure(agg, weights, sentiment)
    st.button(T("test_total"), key="test_total",
              on_click=_test_total_in_practice)


def _saved_portfolio(returns: pd.DataFrame, weights: pd.DataFrame,
                     sentiment: pd.DataFrame) -> None:
    """My Portfolio: saved mixes as mini fact-sheet cards, plus a
    side-by-side comparison when two or more exist. Rendered REGARDLESS of
    the editor's gate state - a saved mix must never vanish just because
    the editor is mid-edit."""
    saved = st.session_state.get("saved_allocs", [])
    if not saved:
        return
    st.subheader(T("saved_heading"))

    if len(saved) >= 2:
        _total_portfolio(saved, returns, weights, sentiment)

    if len(saved) >= 2:
        # Side-by-side comparison. Facts only; never ranked.
        comp = pd.DataFrame({
            "Mix": [T("mix_name").format(i=i + 1)
                    for i in range(len(saved))],
            "ret": [100 * _blend_metrics(e["alloc"], returns)["ann_return"]
                    for e in saved],
            "vol": [100 * _blend_metrics(e["alloc"], returns)["ann_vol"]
                    for e in saved],
            "sharpe": [_blend_metrics(e["alloc"], returns)["sharpe"]
                       for e in saved],
            "dd": [100 * _blend_metrics(e["alloc"], returns)["max_drawdown"]
                   for e in saved],
        })
        st.dataframe(
            comp, hide_index=True, width="stretch",
            column_config={
                "ret": st.column_config.NumberColumn(
                    metric_name("ann_return"), format="%.1f%%"),
                "vol": st.column_config.NumberColumn(
                    metric_name("ann_vol"), format="%.1f%%"),
                "sharpe": st.column_config.NumberColumn(
                    metric_name("sharpe"), format="%.2f"),
                "dd": st.column_config.NumberColumn(
                    metric_name("max_drawdown"), format="%.1f%%"),
            })
        st.caption(T("compare_caption"))

    for i, entry in enumerate(saved):
        top = sorted(entry["alloc"].items(), key=lambda kv: -kv[1])
        top_txt = ", ".join(f"{f} {a * 100:.0f}%" for f, a in top[:3])
        if len(top) > 3:
            top_txt += f" +{len(top) - 3} more"
        with st.container(key=f"mixcard_{i}"):
            st.markdown(
                f"**{T('mix_name').format(i=i + 1)}** · {entry['ts']} · "
                f"{fmt_money(entry.get('amount', 0.0))}")
            st.caption(top_txt)
            # Per-card tone line: this mix's top sectors and their latest
            # news tone (latest snapshot, never a forecast).
            tone = sentiment_tone(sentiment)
            exp = blend_sector_exposure(entry["alloc"], weights)
            eq = {s: v for s, v in exp.items() if s != "Crypto"}
            if eq:
                top2 = sorted(eq.items(), key=lambda kv: -kv[1])[:2]
                sect = "; ".join(
                    f"{SECTOR_DISPLAY.get(s, s)} "
                    f"{_tone_label(float(tone[s]))}" for s, _ in top2)
                st.caption(T("card_tone").format(
                    sectors=sect, date=fmt_date(sentiment.index[-1])))
            else:
                st.caption(T("card_tone_crypto"))
            m = _blend_metrics(entry["alloc"], returns)
            cols = st.columns(4)
            for col, key in zip(cols, METRIC_KEYS):
                col.metric(metric_name(key), _fmt_metric(key, m[key]))
            b1, b2, b3, _ = st.columns([1.1, 1.0, 1.6, 1.3])
            b1.button(T("load_mix"), key=f"load_{i}",
                      on_click=_load_saved, args=(i,))
            b2.button(T("remove"), key=f"remove_{i}",
                      on_click=_remove_saved, args=(i,))
            b3.button(T("test_in_practice"), key=f"test_{i}",
                      on_click=_test_in_practice, args=(i,),
                      help=T("test_in_practice_help"))
            # The full performance view lives INSIDE the card: click to
            # see this mix's own value-over-time chart with its amount.
            with st.expander(T("view_perf"), expanded=False):
                w = np.array([entry["alloc"].get(f, 0.0)
                              for f in FUND_ORDER], dtype=float)
                w = w / w.sum()
                blend = pd.Series(
                    returns.fillna(0.0).to_numpy(dtype=float) @ w,
                    index=returns.index)
                amt = float(entry.get("amount", 0.0))
                value = amt * (1.0 + blend).cumprod()
                fig, ax = new_fig(9.5, 3.4)
                ax.plot(value.index, value.values, color=TEAL, lw=1.5)
                ax.axhline(amt, color=CHARCOAL, lw=0.9, ls="--",
                           label=T("starting_ref").format(amount=amt)
                           .replace("$", "\\$"))
                ax.legend(fontsize=8, frameon=False, loc="upper left")
                ax.set_xlabel("Date", fontsize=9)
                ax.set_ylabel("Value ($)", fontsize=9)
                date_axis(ax, value.index)
                money_axis(ax)
                st.pyplot(fig)
                plt.close(fig)
                st.caption(T("value_range_caption").format(
                    start=fmt_date(value.index[0]),
                    end=fmt_date(value.index[-1]), amount=amt,
                    mn=value.min(), mx=value.max(), last=value.iloc[-1])
                    + " " + T("assumption_caption"))
                # The mix's news exposure belongs inside its performance
                # view too; all-crypto mixes get the sentence instead of
                # a chart, per the "a chart must earn its place" rule.
                st.markdown(f"**{T('news_exp_title')}**")
                _news_exposure(entry["alloc"], weights, sentiment,
                               big_title=False)


# ---------------------------------------------------------------------------
# Tab 3 - Sentiment
# ---------------------------------------------------------------------------

def tab_sentiment(sentiment, sent_summary) -> None:
    st.header(T("sent_heading"))
    st.markdown(f'<div class="quiet-note">{T("sent_disclaimer")}</div>',
                unsafe_allow_html=True)

    display_of = {s: SECTOR_DISPLAY.get(s, s) for s in SECTORS}
    raw_of = {v: k for k, v in display_of.items()}
    picked_display = st.multiselect(
        T("sent_sectors_label"),
        options=[display_of[s] for s in SECTORS],
        default=[display_of["Comm"], display_of["Tech"]],
    )
    show_grey = st.checkbox(T("sent_grey"), value=False)
    standardise = st.checkbox(T("sent_standardise"), value=False)
    if standardise:
        st.caption(T("sent_standardise_caption"))
    window = st.slider(T("smooth_label"), min_value=1, max_value=63,
                       value=21, step=1, help=T("smooth_caption"))

    picked = [raw_of[d] for d in picked_display]
    if not picked:
        st.caption(T("sent_empty"))
    else:
        smooth = sentiment.rolling(window, min_periods=1).mean()
        if standardise:
            # Week-9 standardisation: the raw index sits above neutral on
            # most days, so each sector is compared against its OWN
            # full-sample mean and std - 0 becomes "usual for this sector".
            smooth = (smooth - smooth.mean()) / smooth.std(ddof=0)
        fig, ax = new_fig(9.5, 4.4)
        if show_grey:
            for s in SECTORS:
                if s not in picked:
                    ax.plot(smooth.index, smooth[s], color=LIGHT_GREY,
                            lw=0.8, zorder=1)
        for s in picked:
            ax.plot(smooth.index, smooth[s], color=SECTOR_COLORS[s],
                    lw=1.5, zorder=2)
        ax.axhline(0.0, color=GREY, lw=0.8, ls="--")
        # Direct end-of-line labels (no legend box), nudged apart vertically
        # when two series end at nearly the same value.
        ends = sorted((float(smooth[s].iloc[-1]), s) for s in picked)
        ymin, ymax = ax.get_ylim()
        sep = 0.05 * (ymax - ymin)
        placed = []
        for v, s in ends:
            v = max(v, placed[-1][0] + sep) if placed else v
            placed.append((v, s))
        for v, s in placed:
            ax.text(smooth.index[-1], v, " " + display_of[s],
                    color=SECTOR_COLORS[s], fontsize=8.5, va="center",
                    ha="left", zorder=3)
        title_ax(ax, T("sent_title"))
        ax.set_xlabel("Date", fontsize=9)
        ax.set_ylabel(T("sent_ylabel_z") if standardise else T("sent_ylabel"),
                      fontsize=9)
        date_axis(ax, smooth.index, extend_right=0.14)
        st.pyplot(fig)
        plt.close(fig)
        if lang() == "plain":
            st.caption(T("cap_sentiment_chart"))

    # Background reading (positive bias, start dates) lives behind one
    # collapsed popover-style expander instead of two standing captions.
    with st.expander(T("about_index_title"), expanded=False):
        st.caption(T("posbias_caption").format(
            lo=sent_summary["mean"].min(), hi=sent_summary["mean"].max(),
            pmin=sent_summary["pct_below_zero"].min(),
            pmax=sent_summary["pct_below_zero"].max()))
        st.caption(T("startdates_caption"))


# ---------------------------------------------------------------------------
# Tab 4 - Practice (the investment time machine, Replay mode)
# ---------------------------------------------------------------------------

def _start_travel() -> None:
    alloc = np.array([float(st.session_state.get(f"setup_alloc_{i}", 0.0))
                      for i in range(N_FUNDS)])
    start = pd.Timestamp(st.session_state["setup_date"])
    amount = float(alloc.sum())  # the dollar total IS the starting amount
    blind = st.session_state.get("setup_mode") == T("mode_blind")
    st.session_state["sim"] = {
        "start_date": start,
        "mode": "blind" if blind else "replay",
        "frontier": start,  # blind mode: how far the future is revealed
        # the walk position lives in the sim dict: plain session state,
        # no widget lifecycle
        "view_date": start,
        "decisions": [{"date": start, "kind": "start", "amount": amount,
                       "weights": (alloc / amount).tolist()}],
        "fired": [],
    }


def _start_again() -> None:
    st.session_state.pop("sim", None)  # view_date lives inside sim


def _restart_walk() -> None:
    """Re-hide everything and re-walk the same setup: same start date,
    mix and mode, but the frontier returns to day one, later decisions
    are cleared, and fired cards are forgotten. Exists because dragging
    back cannot un-reveal the future - a restart is the only way to
    truly re-live a stretch."""
    sim = st.session_state.get("sim")
    if sim is None:
        return
    sim["decisions"] = sim["decisions"][:1]
    sim["fired"] = []
    sim["frontier"] = sim["start_date"]
    sim.pop("cards_checked_upto", None)
    sim["view_date"] = sim["start_date"]


def _blind_next(cur: pd.Timestamp, days: list, calendar,
                pace: str = "month") -> pd.Timestamp:
    """One forward step in blind mode.

    Daily inside a turbulent window (you live through the storm). In calm
    periods the pace is the user's choice: a month at a time or day by
    day. Monthly steps never jump OVER a window's start - arriving at a
    storm is part of the experience.
    """
    later = [d for d in days if d > cur]
    if not later:
        return cur
    if _window_at(calendar, cur) is not None:
        return later[0]
    if pace == "day":
        return later[0]
    target = cur + pd.DateOffset(months=1)
    upcoming = calendar[calendar["start"] > cur]
    if not upcoming.empty:
        w0 = upcoming["start"].min()
        if w0 <= target:
            into = [d for d in later if d >= w0]
            if into:
                return into[0]
    cand = [d for d in later if d >= target]
    return cand[0] if cand else later[-1]


def _blind_jump_target(cur: pd.Timestamp, target: pd.Timestamp, days: list,
                       calendar) -> pd.Timestamp:
    """A forward jump never passes a turbulent window's start - you may
    skip a calm year, but a storm still finds you on the way."""
    if target <= cur:
        return cur
    hits = calendar[(calendar["start"] > cur)
                    & (calendar["start"] <= target)]
    if not hits.empty:
        return hits["start"].min()
    return target


def _snap_on_or_after(d: pd.Timestamp, days: list) -> pd.Timestamp:
    cand = [x for x in days if x >= d]
    return cand[0] if cand else days[-1]


def _blind_jump() -> None:
    returns, _, _, _, _, calendar = load_data()
    sim = st.session_state.get("sim")
    if sim is None:
        return
    all_days = list(returns.loc[sim["start_date"]:].index)
    target = pd.Timestamp(st.session_state["jump_date"])
    frontier = sim.get("frontier", sim["start_date"])
    if target <= frontier:
        # Within the revealed range: just move the view, revealing nothing.
        back = [d for d in all_days if d <= target]
        sim["view_date"] = back[-1] if back else frontier
        return
    stop = _snap_on_or_after(
        _blind_jump_target(frontier, target, all_days, calendar), all_days)
    sim["frontier"] = stop
    sim["view_date"] = stop


def _step_slider(delta: int) -> None:
    returns, _, _, _, _, calendar = load_data()
    sim = st.session_state.get("sim")
    if sim is None:
        return
    all_days = list(returns.loc[sim["start_date"]:].index)
    cur = pd.Timestamp(sim.get("view_date", sim["start_date"]))

    if sim.get("mode") == "blind":
        frontier = sim.get("frontier", sim["start_date"])
        allowed = [d for d in all_days if d <= frontier]
        if delta > 0:
            if cur < frontier:  # still catching up with what is revealed
                nxt = [d for d in allowed if d > cur]
                sim["view_date"] = nxt[0] if nxt else frontier
            else:  # at the frontier: reveal one more step, at the
                   # user's chosen pace
                pace = ("day" if st.session_state.get("blind_pace")
                        == T("pace_day") else "month")
                new_frontier = _blind_next(frontier, all_days, calendar,
                                           pace)
                sim["frontier"] = new_frontier
                sim["view_date"] = new_frontier
        else:
            prev = [d for d in allowed if d < cur]
            if prev:
                sim["view_date"] = prev[-1]
        return

    i = all_days.index(cur) if cur in all_days else 0
    sim["view_date"] = all_days[min(max(i + delta, 0),
                                    len(all_days) - 1)]


def _apply_mix(sim_date, prefix: str) -> None:
    w = [float(st.session_state.get(f"{prefix}{i}", 0.0))
         for i in range(N_FUNDS)]
    total = sum(w)
    if total <= 0:
        # An all-zero mix has no proportions to apply. The Apply button is
        # disabled in this state, but guard here too: without it the
        # division below would log NaN weights and poison every later
        # value in the walk with NaN.
        return
    # Dollar amounts express proportions; the mix is applied to whatever
    # the portfolio is worth on the decision date.
    st.session_state["sim"]["decisions"].append(
        {"date": sim_date, "kind": "mix",
         "weights": (np.array(w) / total).tolist()})


def _apply_money(sim_date, amount_key: str, dir_key: str,
                 current_value: float) -> None:
    amount = float(st.session_state.get(amount_key, 0.0))
    if amount <= 0:
        return
    if st.session_state.get(dir_key) == T("money_add"):
        kind = "add"
    else:
        kind = "withdraw"
        amount = min(amount, current_value)  # capped at current value
    if amount <= 0:
        return
    st.session_state["sim"]["decisions"].append(
        {"date": sim_date, "kind": kind, "amount": amount})


def simulate(sim: dict, returns: pd.DataFrame, upto: pd.Timestamp) -> dict:
    """Replay the decision log from the start date to `upto`, day by day.

    Holdings are dollar amounts per fund. Each day: compound every holding
    by that fund's realised daily return (0 for a fund with no return that
    day), THEN apply decisions dated that day - so money earns a return
    only for days it was actually invested, and decisions take effect at
    the close of their date (earning from the next day, never the same
    one). The mix drifts between mix changes; contributions are spread
    across the mix in effect that day; withdrawals come out proportionally
    across all funds and are capped at the current value.
    """
    days = returns.loc[sim["start_date"]:upto].index
    panel = returns.fillna(0.0)
    by_date: dict = {}
    for dec in sim["decisions"]:
        by_date.setdefault(dec["date"], []).append(dec)

    holdings = np.zeros(N_FUNDS)
    paid = 0.0
    target = None
    values, paid_hist, daily_ret, eff_hist = [], [], [], []
    for i, d in enumerate(days):
        # Compound FIRST, with the holdings in effect: money earns a day's
        # return only if it was invested before that day. The start date
        # itself earns nothing - money starts working the day after it
        # goes in.
        if i > 0:
            r = panel.loc[d].to_numpy(dtype=float)
            before = holdings.copy()
            holdings = holdings * (1.0 + r)
        else:
            r = np.zeros(N_FUNDS)
            before = holdings.copy()
        # Decisions dated d take effect at the close of day d: they earn
        # returns from the NEXT day, never the same day.
        for dec in by_date.get(d, []):
            total = float(holdings.sum())
            if dec["kind"] == "start":
                holdings = dec["amount"] * np.asarray(dec["weights"])
                paid += dec["amount"]
                target = np.asarray(dec["weights"])
            elif dec["kind"] == "mix":
                holdings = total * np.asarray(dec["weights"])
                target = np.asarray(dec["weights"])
            elif dec["kind"] == "add":
                base = (holdings / total if total > 0
                        else (target if target is not None
                              else np.full(N_FUNDS, 1.0 / N_FUNDS)))
                holdings = holdings + dec["amount"] * base
                paid += dec["amount"]
            elif dec["kind"] == "withdraw":
                if total > 0:
                    amount = min(dec["amount"], total)
                    holdings = holdings * (1.0 - amount / total)
                    paid -= amount
        total_now = float(holdings.sum())
        values.append(total_now)
        paid_hist.append(paid)
        total_before = float(before.sum())
        daily_ret.append(float((before * r).sum() / total_before)
                         if total_before > 0 else 0.0)
        eff_hist.append(holdings / total_now if total_now > 0
                        else np.zeros(N_FUNDS))
    return {
        "days": days,
        "values": pd.Series(values, index=days),
        "paid": pd.Series(paid_hist, index=days),
        "daily_ret": pd.Series(daily_ret, index=days),
        "eff": pd.DataFrame(eff_hist, index=days, columns=FUND_ORDER),
        "holdings": holdings,
        "target": target,
    }


def _continuation(returns: pd.DataFrame, holdings: np.ndarray,
                  sim_date: pd.Timestamp) -> pd.Series:
    """What the same holdings did after `sim_date` with no further changes."""
    after = returns.fillna(0.0).loc[sim_date:].iloc[1:]
    if after.empty:
        return pd.Series(dtype=float)
    growth = (1.0 + after).cumprod().to_numpy(dtype=float)
    vals = (holdings * growth).sum(axis=1)
    return pd.Series(vals, index=after.index)


def _practice_chart(state: dict, returns: pd.DataFrame, calendar,
                    sim_date: pd.Timestamp, holdings: np.ndarray,
                    blind: bool = False):
    values = state["values"]
    fig, ax = new_fig(10.5, 4.6)
    # Blind mode: nothing past sim_date is drawn - no continuation dashes,
    # no future window shading, no unreached event markers. The x-axis
    # view is capped a little ahead of the frontier so the chart grows
    # with the traveller (a full-width axis would show one dot on an
    # empty canvas at the start of a walk).
    shade_end = sim_date if blind else returns.index[-1]
    shade_windows(ax, calendar, values.index[0], shade_end)
    ax.plot(values.index, values.values, color=TEAL, lw=1.6, zorder=3)
    if not blind:
        cont = _continuation(returns, holdings, sim_date)
        if not cont.empty:
            bridge = pd.concat([values.iloc[-1:], cont])
            ax.plot(bridge.index, bridge.values, color=GREY, lw=1.2,
                    ls="--", zorder=2, label=T("continuation_label"))
    ax.step(state["paid"].index, state["paid"].values, where="post",
            color=CHARCOAL, lw=1.0, zorder=2, label=T("paidin_label"))
    ax.scatter([sim_date], [values.iloc[-1]], color=MAROON, zorder=4, s=32)
    ax.annotate(T("you_are_here").format(date=fmt_date(sim_date)),
                xy=(sim_date, values.iloc[-1]), xytext=(8, 12),
                textcoords="offset points", fontsize=8.5, color=MAROON)
    title_ax(ax, T("practice_chart_title"), strip=True)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Value ($)", fontsize=9)
    ax.set_ylim(bottom=0)
    # Frameless legend pinned to the upper RIGHT: the "You are here" marker
    # and its label live at the left edge early in a run, and the old boxed
    # legend at upper-left collided with them and looked like default
    # matplotlib pasted onto the page.
    ax.legend(fontsize=8, loc="upper right", frameon=False)
    if blind:
        axis_end = min(sim_date + pd.DateOffset(days=60),
                       returns.index[-1])
        ax.set_xlim(values.index[0], axis_end)
        date_axis(ax, returns.loc[values.index[0]:axis_end].index)
    else:
        date_axis(ax, returns.loc[values.index[0]:].index)
    money_axis(ax)
    cap = add_event_markers(ax, calendar, values.index[0], shade_end)
    return fig, cap


def _window_at(calendar, d: pd.Timestamp):
    hit = calendar[(calendar["start"] <= d) & (d <= calendar["end"])]
    return hit.iloc[0] if not hit.empty else None


def _evaluate_cards(sim: dict, state: dict, returns: pd.DataFrame,
                    calendar, sim_date: pd.Timestamp) -> list[str]:
    """Fire-once learning cards. Returns ids of cards fired this run."""
    fired_ids = {c["id"] for c in sim["fired"]}
    values = state["values"]
    if values.empty:
        return []
    peak = values.cummax()
    cur = float(values.iloc[-1])
    cur_peak = float(peak.iloc[-1])
    peak_date = values.idxmax()
    dd = cur / cur_peak - 1.0 if cur_peak > 0 else 0.0

    def fire(cid: str, card: str, **kwargs) -> None:
        sim["fired"].append({"id": cid, "card": card, "kwargs": kwargs})

    new: list[str] = []
    # Warm-up: threshold cards need context to teach anything. In the
    # first month of a run the user has no baseline yet, so a "large
    # single-day move" or a drawdown alert on day two reads as noise, not
    # teaching. Window-entry and end-of-data cards stay ungated.
    warmed_up = len(values) >= 21
    if warmed_up and dd <= -0.10 and "dd_10" not in fired_ids:
        fire("dd_10", "dd_10", value=cur, peak=cur_peak,
             peak_date=fmt_date(peak_date), dd=dd * 100)
        new.append("dd_10")
    if warmed_up and dd <= -0.20 and "dd_20" not in fired_ids:
        fire("dd_20", "dd_20", value=cur, peak=cur_peak,
             peak_date=fmt_date(peak_date), dd=dd * 100)
        new.append("dd_20")

    cew = returns["Combined Equal-Weight"].dropna()
    sigma = float(cew.std(ddof=1))
    # The card checks the whole STRETCH travelled since the last check and
    # names the true biggest day in it - after a monthly jump or a date
    # jump, the landing day's move alone would name the wrong day or miss
    # the big one entirely.
    since = sim.get("cards_checked_upto", sim["start_date"])
    stretch = pd.Series(dtype=float)
    if sim_date > since:
        stretch = state["daily_ret"].loc[since:sim_date].iloc[1:]
    if warmed_up and len(stretch) > 0:
        biggest = stretch.abs().idxmax()
        move = float(stretch.loc[biggest])
        if abs(move) > 2.0 * sigma and "big_day" not in fired_ids:
            fire("big_day", "big_day", date=fmt_date(biggest),
                 move=move * 100, band=2.0 * sigma * 100,
                 n=int((cew.abs() > 2.0 * sigma).sum()), N=int(len(cew)))
            new.append("big_day")
    if sim_date > since:
        sim["cards_checked_upto"] = sim_date

    if state["target"] is not None and cur > 0:
        eff = state["eff"].iloc[-1].to_numpy(dtype=float)
        gaps = np.abs(eff - state["target"]) * 100.0
        i = int(np.argmax(gaps))
        if gaps[i] >= 5.0 and "drift" not in fired_ids:
            fire("drift", "drift", fund=FUND_ORDER[i],
                 actual=float(eff[i]) * 100,
                 target=float(state["target"][i]) * 100,
                 gap=float(gaps[i]))
            new.append("drift")

    win = _window_at(calendar, sim_date)
    if win is not None:
        cid = f"turbulent:{win['label']}:{win['start'].date()}"
        if cid not in fired_ids:
            fire(cid, "turbulent", label=str(win["label"]),
                 start=fmt_date(win["start"]), end=fmt_date(win["end"]))
            new.append(cid)

    if sim_date >= returns.index[-1] and "end" not in fired_ids:
        fire("end", "end", date=fmt_date(sim_date))
        new.append("end")
    return new


def _render_cards(sim: dict, newly: list[str]) -> None:
    newest = newly[-1] if newly else None
    for entry in sim["fired"]:
        title = PRACTICE_COPY[entry["card"]]["title"][lang()]
        with st.expander(title, expanded=(entry["id"] == newest)):
            st.write(card_text(entry["card"], "body", **entry["kwargs"]))


def _practice_setup() -> None:
    st.header(T("practice_heading"))
    st.caption(T("setup_intro"))
    # Numbered steps: a first-timer should never wonder what to do first.
    st.markdown(f"**{T('step1')}**")
    st.date_input(T("start_date_label"), value=PRACTICE_START_MIN.date(),
                  min_value=PRACTICE_START_MIN.date(),
                  max_value=PRACTICE_START_MAX.date(), key="setup_date")
    st.markdown(f"**{T('step2')}**")
    st.number_input(T("total_amount_label"), min_value=0.0, value=1000.0,
                    step=100.0, key="setup_total_amount",
                    help=T("total_amount_help"))
    st.markdown(f"**{T('step3')}**")
    st.button(T("split_evenly"), on_click=_split_evenly,
              args=("setup_alloc_", "setup_total_amount"))
    _fund_inputs("setup_alloc_")
    total = sum(float(st.session_state.get(f"setup_alloc_{i}", 0.0))
                for i in range(N_FUNDS))
    # Same contract as My Allocation: the walk starts once the full
    # declared amount is placed.
    target = float(st.session_state.get("setup_total_amount", 0.0))
    diff = total - target
    st.write(T("placed_line").format(total=total, target=target))
    st.markdown(f"**{T('step4')}**")
    st.radio(T("mode_label"), [T("mode_replay"), T("mode_blind")],
             key="setup_mode")
    if st.session_state.get("setup_mode") == T("mode_blind"):
        st.caption(T("mode_blind_cap"))
    else:
        st.caption(T("mode_replay_cap"))
    ready = abs(diff) <= 0.5 and target > 0
    st.button(T("start_button"), disabled=not ready, on_click=_start_travel)
    if not ready:
        if diff < -0.5:
            st.caption(T("placed_remaining").format(rem=-diff))
        else:
            st.caption(T("placed_over").format(over=diff))


def _decision_text(dec: dict) -> str:
    d = fmt_date(dec["date"])
    if dec["kind"] == "start":
        body = T("dec_start").format(amount=dec["amount"])
    elif dec["kind"] == "mix":
        body = T("dec_mix")
    elif dec["kind"] == "add":
        body = T("dec_add").format(amount=dec["amount"])
    else:
        body = T("dec_withdraw").format(amount=dec["amount"])
    return f"{d} - {body}"


def _day_summary(state: dict, sim: dict, sim_date: pd.Timestamp,
                 returns: pd.DataFrame) -> None:
    """The "today at a glance" digest: what the market move did to the
    user's money on this date, which fund drove it, and any cash flow.
    Directions are factual (rose/fell); nothing evaluates the day."""
    values = state["values"]
    st.markdown(f"**{T('day_title').format(date=fmt_date(sim_date))}**")
    if len(values) < 2:
        st.caption(T("day_first").format(
            amount=fmt_money(float(state["paid"].iloc[-1]))))
        return
    r_today = float(state["daily_ret"].iloc[-1])
    prev = float(values.iloc[-2])
    cur = float(values.iloc[-1])
    chg = prev * r_today  # the market move in dollars (flows excluded)
    direction = "rose" if chg >= 0 else "fell"
    st.caption(T("day_change").format(
        direction=direction, abs_chg=abs(chg), pct_chg=r_today * 100,
        value=cur))

    flow = cur - prev - chg  # decisions dated today take effect at close
    if abs(flow) >= 0.01:
        verb = "added" if flow > 0 else "took out"
        st.caption(T("day_flow").format(verb=verb, flow=abs(flow)))

    # Biggest driver: yesterday's effective weight x today's fund return.
    r = returns.loc[sim_date].to_numpy(dtype=float)
    eff_prev = state["eff"].iloc[-2].to_numpy(dtype=float)
    contrib = eff_prev * r * 100.0  # percentage points of portfolio value
    i = int(np.argmax(np.abs(contrib)))
    if abs(contrib[i]) >= 0.05:  # ignore trivial drivers
        st.caption(T("day_driver").format(
            fund=FUND_ORDER[i], fund_ret=float(r[i]) * 100,
            contrib=float(contrib[i])))
    else:
        st.caption(T("day_driver_none"))


def _news_mood(state: dict, weights: pd.DataFrame,
               sentiment: pd.DataFrame, sim_date: pd.Timestamp) -> None:
    """The current news mood for the sectors the user is invested in.

    PAST-ONLY by construction: the z-score uses the expanding mean/std of
    the index UP TO sim_date, and sector exposure uses each fund's latest
    rebalance ON OR BEFORE sim_date - nothing from the future leaks into
    the lesson.
    """
    hist = sentiment.loc[:sim_date]
    if len(hist) < 60:
        st.caption(T("news_mood_none"))
        return
    z = (hist.iloc[-1] - hist.mean()) / hist.std(ddof=0)

    eff = state["eff"].iloc[-1]  # effective per-fund shares at sim_date
    exposure: dict[str, float] = {}
    for fund, w in eff.items():
        if w <= 0:
            continue
        f_w = weights[(weights["fund"] == fund)
                      & (weights["date"] <= sim_date)]
        if f_w.empty:
            continue
        lw = f_w[f_w["date"] == f_w["date"].max()].set_index("ticker")["weight"]
        for ticker, tw in lw.items():
            sector = SECTOR_MAP.get(ticker)
            if sector:
                exposure[sector] = (exposure.get(sector, 0.0)
                                    + float(w) * float(tw))
    if not exposure:
        st.caption(T("news_mood_empty"))
        return

    st.markdown(f"**{T('news_mood_title')}**")
    top = sorted(exposure.items(), key=lambda kv: -kv[1])[:3]
    for sector, share in top:
        zs = float(z[sector])
        st.caption(f"{SECTOR_DISPLAY.get(sector, sector)} - "
                   f"{share * 100:.0f}% of your mix - "
                   f"{_tone_label(zs)} (z = {zs:+.1f})")
    st.caption(T("news_mood_caption"))


def _debrief(sim: dict, returns: pd.DataFrame) -> None:
    """The blind-walk payoff: the user's path versus never touching the
    starting mix. Facts only - the gap is stated, never judged."""
    end = returns.index[-1]
    mine = simulate(sim, returns, end)
    bh_sim = {"start_date": sim["start_date"],
              "decisions": sim["decisions"][:1]}
    bh = simulate(bh_sim, returns, end)
    my_end = float(mine["values"].iloc[-1])
    bh_end = float(bh["values"].iloc[-1])
    n_changes = len(sim["decisions"]) - 1

    st.subheader(T("debrief_title"))
    fig, ax = new_fig(9.5, 3.8)
    ax.plot(mine["values"].index, mine["values"].values, color=TEAL,
            lw=1.6, label=T("debrief_you"))
    ax.plot(bh["values"].index, bh["values"].values, color=GREY, lw=1.3,
            ls="--", label=T("debrief_bh"))
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    title_ax(ax, T("debrief_chart_title"))
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Value ($)", fontsize=9)
    ax.set_ylim(bottom=0)
    date_axis(ax, mine["values"].index)
    money_axis(ax)
    st.pyplot(fig)
    plt.close(fig)
    st.caption(T("debrief_body").format(
        n=n_changes, mine=fmt_money(my_end), bh=fmt_money(bh_end)))
    st.button(T("save_from_practice"), key="debrief_save",
              on_click=_save_start_mix)


def _dismiss_intro() -> None:
    st.session_state["walk_intro_seen"] = True


def _practice_running(returns, weights, sentiment, calendar) -> None:
    sim = st.session_state["sim"]
    blind = sim.get("mode") == "blind"
    all_days = list(returns.loc[sim["start_date"]:].index)
    if blind:
        frontier = sim.get("frontier", sim["start_date"])
        days = [d for d in all_days if d <= frontier]
    else:
        days = all_days
    # The walk position lives in sim["view_date"] - plain session state,
    # so tab switches cannot destroy it (unlike a widget key, which
    # Streamlit deletes when its tab is unmounted, and whose restore is
    # overwritten by the widget's first-ever default on remount).
    sim_date = pd.Timestamp(sim.get("view_date", sim["start_date"]))
    if sim_date not in days:
        sim_date = days[0]
        sim["view_date"] = sim_date
    state = simulate(sim, returns, sim_date)
    value_now = float(state["values"].iloc[-1])

    # First-walk orientation: a small dismissible card, once per session.
    if not st.session_state.get("walk_intro_seen"):
        with st.container(key="walk_intro"):
            st.markdown(f"**{T('walk_intro_title')}**")
            st.caption(T("walk_intro_body"))
            st.button(T("walk_intro_dismiss"), key="walk_intro_btn",
                      on_click=_dismiss_intro)

    # 1. Portfolio value chart (the centrepiece, full width).
    fig, cap = _practice_chart(state, returns, calendar, sim_date,
                               state["holdings"], blind=blind)
    st.pyplot(fig)
    plt.close(fig)
    if cap:
        st.caption(cap)

    # 2. Timeline slider directly beneath the chart - the primary control.
    win = _window_at(calendar, sim_date)
    c1, c2, c3 = st.columns([1, 16, 1])
    c1.button("◀", key="step_back", on_click=_step_slider, args=(-1,))
    if len(days) >= 2:
        # Stateless slider: the position is read from sim["view_date"]
        # every run and any drag is written straight back. No widget key,
        # so no lifecycle surprises.
        sel = c2.select_slider(
            T("slider_label"), options=days, value=sim_date,
            format_func=lambda d: pd.Timestamp(d).strftime("%d %b %Y"),
            label_visibility="visible", help=T("slider_caption"))
        if pd.Timestamp(sel) != sim_date:
            sim["view_date"] = pd.Timestamp(sel)
            st.rerun()
    else:
        # A one-option slider crashes the widget (min == max), and at the
        # very start of a blind walk the revealed range is a single date.
        c2.caption(T("slider_label") + " — " + fmt_date(sim_date))
    c3.button("▶", key="step_fwd", on_click=_step_slider, args=(1,))
    if win is not None:
        st.markdown(
            f'<div class="quiet-note">{T("turbulent_banner").format(label=win["label"], start=fmt_date(win["start"]), end=fmt_date(win["end"]))}</div>',
            unsafe_allow_html=True)

    if blind:
        # Pace is the user's choice; jumps are guarded by the storm rule.
        # Jumping is an explicit button click - an on_change handler on the
        # date field fired spuriously on tab remount (a stale restored
        # value looked like a change) and dragged the walk back to day 1.
        p1, p2, p3 = st.columns([2, 2, 2])
        p1.radio(T("pace_label"), [T("pace_month"), T("pace_day")],
                 key="blind_pace", horizontal=True)
        with p2:
            # The union calendar runs to 2023-12-31 (crypto trades the
            # year-end weekend); allow the true data end and clamp the
            # default into range.
            st.date_input(T("jump_label"),
                          value=min(
                              sim.get("frontier", sim["start_date"]).date(),
                              returns.index[-1].date()),
                          min_value=sim["start_date"].date(),
                          max_value=returns.index[-1].date(),
                          key="jump_date")
            st.button(T("jump_go"), key="jump_go", on_click=_blind_jump)
        with p3:
            st.markdown("<div style='height:28px'></div>",
                        unsafe_allow_html=True)
            st.button(T("restart_walk"), key="restart_walk",
                      on_click=_restart_walk, help=T("restart_note"))
        st.caption(T("jump_note"))

    # 2c. "Today at a glance" - the daily digest, in both modes.
    _day_summary(state, sim, sim_date, returns)

    # 2b. Blind mode only: the news mood at this date (past-only stats).
    if blind:
        _news_mood(state, weights, sentiment, sim_date)

    # 3. "What just happened" learning cards.
    newly = _evaluate_cards(sim, state, returns, calendar, sim_date)
    if sim["fired"]:
        st.subheader("What just happened" if lang() == "plain"
                     else "What just happened")
        _render_cards(sim, newly)

    # 4. Status row.
    cols = st.columns(4)
    peak = float(state["values"].cummax().iloc[-1])
    paid_now = float(state["paid"].iloc[-1])
    status = [
        (T("status_date"), fmt_date(sim_date), T("status_date_gloss")),
        (T("status_value"), fmt_money(value_now), T("status_value_gloss")),
        (T("status_paid"), fmt_money(paid_now), T("status_paid_gloss")),
        (T("status_peak"), fmt_money(peak), T("status_peak_gloss")),
    ]
    for col, (name, val, gloss) in zip(cols, status):
        col.metric(name, val,
                   help=gloss if lang() == "plain" and gloss else None)

    # 5. Make a change on this date.
    date_key = sim_date.strftime("%Y%m%d")
    with st.expander(T("change_heading"), expanded=False):
        t_mix, t_money = st.tabs([T("change_mix_tab"), T("change_money_tab")])
        with t_mix:
            # Dollar amounts, defaulting to the current effective dollars.
            # Any total works: the amounts express proportions, and the
            # mix is applied to whatever the portfolio is worth today.
            base = (state["eff"].iloc[-1].to_numpy(dtype=float) * value_now
                    if value_now > 0 and state["target"] is not None
                    else np.zeros(N_FUNDS))
            defaults = np.round(base, 0)
            prefix = f"mix_{date_key}_"
            cols2 = st.columns(2)
            for i, fund in enumerate(FUND_ORDER):
                cols2[i % 2].number_input(
                    fund, min_value=0.0, step=50.0,
                    format="%.0f", value=float(defaults[i]),
                    key=f"{prefix}{i}", help=fund_line(fund))
            total2 = sum(float(st.session_state.get(f"{prefix}{i}", 0.0))
                         for i in range(N_FUNDS))
            st.write(T("total_line").format(total=total2))
            st.caption(T("mix_note"))
            ok = total2 > 0
            st.button(T("mix_apply"), disabled=not ok, on_click=_apply_mix,
                      args=(sim_date, prefix))
            if not ok:
                st.caption(T("mix_hint"))
        with t_money:
            st.radio("Direction", [T("money_add"), T("money_take")],
                     horizontal=True, key=f"dir_{date_key}")
            st.number_input(T("money_amount"), min_value=0.0, value=100.0,
                            step=50.0, key=f"money_{date_key}")
            st.caption(T("withdraw_cap").format(val=value_now))
            st.button(T("money_apply"), on_click=_apply_money,
                      args=(sim_date, f"money_{date_key}", f"dir_{date_key}",
                            value_now))

    # 6. Decision history + reset + the bridge to My Portfolio.
    with st.expander(T("decisions_heading"), expanded=False):
        for i, dec in enumerate(sim["decisions"], start=1):
            st.write(f"{i}. {_decision_text(dec)}")
        d1, d2 = st.columns(2)
        d1.button(T("save_from_practice"), on_click=_save_start_mix)
        d2.button(T("start_again"), on_click=_start_again)

    # 7. Blind mode only: the debrief appears when the data runs out.
    if blind and sim_date >= all_days[-1]:
        st.divider()
        _debrief(sim, returns)


def tab_practice(returns, weights, sentiment, calendar) -> None:
    if st.session_state.get("sim") is None:
        _practice_setup()
    else:
        _practice_running(returns, weights, sentiment, calendar)


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Widget-state mirroring
# Streamlit deletes a widget's session-state entry whenever the widget is
# not rendered in a run - so switching tabs used to silently discard the
# Practice walk's position, the allocation amounts, and the setup choices.
# The fix: after each run, copy the values we care about into an ordinary
# (non-widget) session key, which survives; before rendering, restore any
# widget keys that were discarded while their tab was unmounted.
# ---------------------------------------------------------------------------
_MIRROR_FIXED = ["alloc_total_amount", "setup_total_amount",
                 "blind_pace", "setup_date", "setup_mode"]
_MIRROR_PREFIXES = ("alloc_", "setup_alloc_")


def _mirror_save() -> None:
    store = st.session_state.setdefault("_widget_mirror", {})
    for k in _MIRROR_FIXED:
        if k in st.session_state:
            store[k] = st.session_state[k]
    for k in list(st.session_state.keys()):
        if any(k.startswith(p) for p in _MIRROR_PREFIXES):
            store[k] = st.session_state[k]


def _mirror_restore() -> None:
    store = st.session_state.get("_widget_mirror", {})
    for k, v in store.items():
        if k not in st.session_state:
            st.session_state[k] = v


def main() -> None:
    st.set_page_config(page_title="HyperInvest", layout="wide")
    st.markdown(DESIGN_CSS, unsafe_allow_html=True)
    apply_chart_style()
    _mirror_restore()
    returns, weights, sentiment, metrics, sent_summary, calendar = load_data()

    with st.sidebar:
        st.markdown('<div class="sidebar-brand">HyperInvest</div>'
                    '<div class="sidebar-tag">Evidence, not advice.</div>',
                    unsafe_allow_html=True)
        st.radio("Language", ["Plain English", "Professional"], key="lang")
        # Journey map: fills the sidebar with wayfinding - the four
        # sections, with the current one marked. Display only.
        current = st.session_state.get("nav", "Funds")
        journey = "".join(
            f'<div class="journey-item{" current" if s == current else ""}">'
            f"{s}</div>"
            for s in TABS)
        st.markdown(f'<div style="margin-top:14px;margin-bottom:6px;'
                    f'font-size:0.78rem;font-weight:700;letter-spacing:0.06em;'
                    f'color:{MUTED};text-transform:uppercase;">Your journey'
                    f'</div>{journey}', unsafe_allow_html=True)
        with st.expander(T("about_data_title"), expanded=False):
            st.caption("**Data** — 50 US shares + 10 cryptocurrencies; "
                       "out-of-sample backtests 2021-02-01 to 2023-12-29 "
                       "(crypto fund from 2020-10-01, its own calendar). "
                       "News sentiment from ~147,000 headlines, 2020-2023. "
                       "No data exists past the sample.")
            st.caption("**Assumptions** — risk-free rate 0% · zero "
                       "transaction costs · monthly rebalancing · long-only.")
        with st.expander(T("mech_title"), expanded=False):
            st.markdown(T("mech_body"))
            st.caption(T("mech_guarantee"))
        st.caption("HyperInvest shows what happened. It never recommends "
                   "what to do.")

    if not st.session_state.get("started"):
        landing()
        return

    nav = st.radio("Section", TABS, horizontal=True, key="nav",
                   label_visibility="collapsed")
    if nav == "Funds":
        tab_funds(returns, weights, metrics, calendar)
    elif nav == "My Allocation":
        tab_allocation(returns, weights, sentiment)
    elif nav == "Sentiment":
        tab_sentiment(sentiment, sent_summary)
    else:
        tab_practice(returns, weights, sentiment, calendar)
    _mirror_save()


main()
