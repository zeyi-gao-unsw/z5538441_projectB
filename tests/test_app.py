"""App tests for streamlit_app.py using streamlit.testing.v1.AppTest.

Run from the project folder:

    python -m pytest -q
"""
from __future__ import annotations

import pathlib
import sys

import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = ROOT / "streamlit_app.py"

DISCLAIMER = ("The sentiment index describes news tone; it is not a buy or "
              "sell signal.")


def make_app() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    return at


def button(at: AppTest, label: str):
    matches = [b for b in at.button if b.label == label]
    assert matches, f"button {label!r} not found; have {[b.label for b in at.button]}"
    return matches[0]


def test_app_runs_first_load():
    at = make_app()
    assert not at.exception


def test_landing_renders_and_buttons_navigate():
    at = make_app()
    labels = [b.label for b in at.button]
    assert "Explore the funds" in labels
    assert "Start in the practice area" in labels

    button(at, "Explore the funds").click().run()
    assert not at.exception
    assert at.session_state["nav"] == "Funds"

    at2 = make_app()
    button(at2, "Start in the practice area").click().run()
    assert not at2.exception
    assert at2.session_state["nav"] == "Practice"


def test_sentiment_disclaimer():
    at = make_app()
    button(at, "Explore the funds").click().run()
    nav = [r for r in at.radio if r.key == "nav"][0]
    nav.set_value("Sentiment").run()
    assert not at.exception
    # The disclaimer renders as a styled quiet-note markdown, not st.info.
    text = "\n".join(m.value for m in at.markdown)
    assert DISCLAIMER in text, "disclaimer not found on the Sentiment tab"


def test_practice_start_disabled_until_100():
    at = make_app()
    button(at, "Start in the practice area").click().run()
    assert not at.exception
    assert button(at, "Start travelling").disabled

    allocs = [ni for ni in at.number_input
              if ni.key and ni.key.startswith("setup_alloc_")]
    assert len(allocs) >= 8  # the fund shelf can grow; never hardcode it
    # Partially placed amount: the walk must NOT start (the amount field
    # is the contract - results/walks wait for the full placement).
    allocs[0].set_value(500.0)
    at.run()
    assert button(at, "Start travelling").disabled
    # "Split evenly" fills every box to the declared amount, so the gate
    # opens - the test drives the same control a user would.
    button(at, "Split evenly").click().run()
    assert not at.exception
    assert not button(at, "Start travelling").disabled


def test_no_forbidden_imports():
    text = APP.read_text(encoding="utf-8")
    assert "nltk" not in text
    assert "scipy" not in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


def test_sector_map_matches_real_data():
    """Tripwire for the hardcoded sector map: reload the hosted data and
    assert every one of the 50 equity tickers is mapped to its real sector.
    Hardcoding is allowed (the sample is frozen) - silence is not."""
    from src import data_access
    import streamlit_app as app_module  # noqa: importing the app runs st
                                        # commands in bare mode; harmless
    eq = data_access.load_equity_prices()
    real = (eq[["ticker", "sector"]].drop_duplicates()
            .set_index("ticker")["sector"].to_dict())
    assert app_module.SECTOR_MAP == real


def test_blend_sector_exposure_math():
    """100% Combined Equal-Weight: 50 equities at 1/60 each roll up to
    5/60 per sector, and the 10 coins land in the Crypto bucket."""
    import pandas as pd
    import streamlit_app as app_module
    weights = pd.read_csv(ROOT / "results" / "data" / "fund_weights.csv",
                          parse_dates=["date"])
    shares = app_module.blend_sector_exposure(
        {"Combined Equal-Weight": 1.0}, weights)
    assert abs(shares["Crypto"] - 10 / 60) < 1e-9
    for s in app_module.SECTORS:
        assert abs(shares[s] - 5 / 60) < 1e-9
    assert abs(shares.sum() - 1.0) < 1e-9


def test_blind_next_steps():
    """Blind-mode forward rule: monthly in calm periods, never jumping a
    window start, daily inside a window, and never past the data end."""
    import pandas as pd
    import streamlit_app as app_module
    returns = pd.read_csv(ROOT / "results" / "data" / "fund_returns.csv",
                          parse_dates=["date"]).set_index("date")
    calendar = pd.read_csv(ROOT / "results" / "data" / "event_calendar.csv",
                           parse_dates=["start", "end"])
    days = list(returns.index)

    # calm period: roughly a month ahead
    cur = pd.Timestamp("2021-03-01")
    nxt = app_module._blind_next(cur, days, calendar)
    assert pd.Timestamp("2021-03-15") <= nxt <= pd.Timestamp("2021-04-15")

    # just before the crypto sell-off window (2021-05-05 start): land on
    # the window, do not jump over it
    cur = pd.Timestamp("2021-04-06")
    nxt = app_module._blind_next(cur, days, calendar)
    assert nxt >= pd.Timestamp("2021-05-05")
    assert nxt <= pd.Timestamp("2021-05-26")

    # inside the window: exactly one trading day ahead
    cur = pd.Timestamp("2021-05-06")
    nxt = app_module._blind_next(cur, days, calendar)
    assert nxt == pd.Timestamp("2021-05-07")

    # at the data end: stays put
    assert app_module._blind_next(days[-1], days, calendar) == days[-1]


def test_debrief_counterfactual_is_buy_and_hold():
    """The debrief's comparison path must equal the simulation with only
    the start decision - i.e. buy-and-hold of the starting mix."""
    import pandas as pd
    import streamlit_app as app_module
    returns = pd.read_csv(ROOT / "results" / "data" / "fund_returns.csv",
                          parse_dates=["date"]).set_index("date")
    start = returns.index[0]
    sim = {"start_date": start,
           "decisions": [{"date": start, "kind": "start", "amount": 1000.0,
                          "weights": [1.0] + [0.0] * 12}]}
    end = returns.index[-1]
    with_decision = dict(sim)
    with_decision["decisions"] = sim["decisions"] + [
        {"date": returns.index[100], "kind": "mix",
         "weights": [0.5, 0.5] + [0.0] * 11}]
    full = app_module.simulate(with_decision, returns, end)
    bh = app_module.simulate(sim, returns, end)
    # buy-and-hold of fund 0 ends at 1000 x its growth endpoint
    g = (1.0 + returns.iloc[:, 0].fillna(0.0)).cumprod()
    assert abs(float(bh["values"].iloc[-1]) - 1000.0 * float(g.iloc[-1])) < 1e-6
    # and the decision path genuinely differs from it
    assert abs(float(full["values"].iloc[-1]) - float(bh["values"].iloc[-1])) > 1e-6


def test_blind_pace_and_jump():
    """Pace switch: day mode steps one trading day even in calm periods.
    Jump rule: a forward jump stops at the next turbulent window's start."""
    import pandas as pd
    import streamlit_app as app_module
    returns = pd.read_csv(ROOT / "results" / "data" / "fund_returns.csv",
                          parse_dates=["date"]).set_index("date")
    calendar = pd.read_csv(ROOT / "results" / "data" / "event_calendar.csv",
                           parse_dates=["start", "end"])
    days = list(returns.index)

    # day pace in a calm period: exactly one trading day ahead
    cur = pd.Timestamp("2021-03-01")
    nxt = app_module._blind_next(cur, days, calendar, pace="day")
    assert nxt == pd.Timestamp("2021-03-02")

    # jump from April into September 2021: stops at the crypto sell-off
    # window start (2021-05-05), never past it
    stop = app_module._blind_jump_target(pd.Timestamp("2021-04-06"),
                                         pd.Timestamp("2021-09-01"),
                                         days, calendar)
    assert stop == pd.Timestamp("2021-05-05")
    # a jump within a calm stretch lands on the target itself
    stop2 = app_module._blind_jump_target(pd.Timestamp("2021-03-01"),
                                          pd.Timestamp("2021-03-31"),
                                          days, calendar)
    assert stop2 == pd.Timestamp("2021-03-31")


def test_big_day_card_names_true_biggest_day():
    """After a monthly jump, the card must name the biggest day IN the
    travelled stretch, not the landing day."""
    import pandas as pd
    import streamlit_app as app_module
    returns = pd.read_csv(ROOT / "results" / "data" / "fund_returns.csv",
                          parse_dates=["date"]).set_index("date")
    calendar = pd.read_csv(ROOT / "results" / "data" / "event_calendar.csv",
                           parse_dates=["start", "end"])
    start = pd.Timestamp("2021-04-01")
    sim = {"start_date": start, "fired": [],
           "decisions": [{"date": start, "kind": "start", "amount": 1000.0,
                          "weights": [1.0] + [0.0] * 12}]}
    land = pd.Timestamp("2021-05-26")  # a jump covering the crypto sell-off
    state = app_module.simulate(sim, returns, land)
    app_module._evaluate_cards(sim, state, returns, calendar, land)
    fired = {f["id"]: f for f in sim["fired"]}
    assert "big_day" in fired
    # the named date must be the stretch's true argmax |move|
    stretch = state["daily_ret"].loc[start:land].iloc[1:]
    true_biggest = stretch.abs().idxmax()
    assert fired["big_day"]["kwargs"]["date"] == true_biggest.strftime(
        "%d %b %Y")


def test_restart_walk_rehides():
    """Restart walk: same setup, frontier back to day one, decisions and
    cards cleared - the future is hidden again."""
    at = make_app()
    button(at, "Start in the practice area").click().run()
    button(at, "Split evenly").click().run()
    [b for b in at.button if "Blind walk" in (b.label or "")]  # radio, not button
    r = [x for x in at.radio if "Replay - see the whole timeline" in str(x.options)][0]
    r.set_value("Blind walk - the future is hidden").run()
    button(at, "Start travelling").click().run()
    assert not at.exception
    sim = at.session_state["sim"]
    assert sim["mode"] == "blind"
    # step forward twice (monthly), then restart
    button(at, "▶").click().run()
    button(at, "▶").click().run()
    sim = at.session_state["sim"]
    assert sim["frontier"] > sim["start_date"]
    button(at, "Restart walk").click().run()
    sim = at.session_state["sim"]
    assert sim["frontier"] == sim["start_date"]
    assert len(sim["decisions"]) == 1
    assert sim["fired"] == []
    assert sim["view_date"] == sim["start_date"]


def test_walk_position_survives_tab_switch():
    """Streamlit deletes state for unmounted widgets; the mirror must
    restore the walk's position after switching away and back."""
    at = make_app()
    button(at, "Start in the practice area").click().run()
    button(at, "Split evenly").click().run()
    button(at, "Start travelling").click().run()  # replay mode
    button(at, "▶").click().run()
    pos = at.session_state["sim"]["view_date"]
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    nav.set_value("My Allocation").run()
    assert not at.exception
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    nav.set_value("Practice").run()
    assert not at.exception
    assert at.session_state["sim"]["view_date"] == pos
    assert at.session_state["sim"] is not None


def test_portfolio_save_and_load_back():
    """Save a completed mix to My Portfolio, then load it back into the
    editor: the boxes must refill and sum to the amount field."""
    at = make_app()
    button(at, "Explore the funds").click().run()
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    nav.set_value("My Allocation").run()
    button(at, "Split evenly").click().run()  # fills to the $1,000 default
    button(at, "Save this allocation to My Portfolio").click().run()
    assert "saved_allocs" in at.session_state
    saved = at.session_state["saved_allocs"]
    assert len(saved) == 1
    assert abs(sum(saved[0]["alloc"].values()) - 1.0) < 1e-9
    assert saved[0]["amount"] == 1000.0
    # saving auto-clears the editor, so the next mix starts clean
    after_save = sum(at.session_state[f"alloc_{i}"] for i in range(20)
                     if f"alloc_{i}" in at.session_state)
    assert after_save == 0.0
    # loading the saved mix brings it back deliberately
    button(at, "Load into editor").click().run()
    total = sum(at.session_state[f"alloc_{i}"] for i in range(20)
                if f"alloc_{i}" in at.session_state)
    assert abs(total - 1000.0) < 1.0


def test_practice_bridge_saves_start_mix():
    """The Practice bridge saves the walk's starting mix with its own
    start amount into My Portfolio."""
    at = make_app()
    button(at, "Start in the practice area").click().run()
    button(at, "Split evenly").click().run()
    button(at, "Start travelling").click().run()
    button(at, "Save this starting mix to My Portfolio").click().run()
    assert "saved_allocs" in at.session_state
    saved = at.session_state["saved_allocs"]
    assert len(saved) == 1
    assert saved[0]["amount"] == 1000.0
    assert abs(sum(saved[0]["alloc"].values()) - 1.0) < 1e-9


def test_total_portfolio_renders_with_two_mixes():
    """With 2+ saved mixes, the aggregate 'whole portfolio' block appears
    and its maths is sane: total placed equals the sum of amounts."""
    at = make_app()
    button(at, "Explore the funds").click().run()
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    nav.set_value("My Allocation").run()
    button(at, "Split evenly").click().run()
    button(at, "Save this allocation to My Portfolio").click().run()
    # saving auto-clears the editor now, so refill before the second save
    button(at, "Split evenly").click().run()
    button(at, "Save this allocation to My Portfolio").click().run()
    at.run()
    assert not at.exception
    text = "\n".join(m.value for m in at.markdown)
    assert "whole portfolio" in text
    saved = at.session_state["saved_allocs"]
    assert sum(e["amount"] for e in saved) == 2000.0


def test_test_in_practice_bridge():
    """The reverse bridge: a saved mix loads into the Practice setup with
    its own amount, and navigation lands on the Practice tab."""
    at = make_app()
    button(at, "Explore the funds").click().run()
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    nav.set_value("My Allocation").run()
    button(at, "Split evenly").click().run()
    button(at, "Save this allocation to My Portfolio").click().run()
    button(at, "Test in the time machine").click().run()
    assert not at.exception
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    assert nav.value == "Practice"
    setup_total = sum(at.session_state[f"setup_alloc_{i}"] for i in range(20)
                      if f"setup_alloc_{i}" in at.session_state)
    assert abs(setup_total - 1000.0) < 1.0
    assert abs(at.session_state["setup_total_amount"] - 1000.0) < 1e-9


def test_all_crypto_mix_gets_sentence_not_grey_wall():
    """A 100%-crypto mix has no equity exposure, so the news panel must
    show the factual sentence instead of a useless all-grey chart."""
    at = make_app()
    button(at, "Explore the funds").click().run()
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    nav.set_value("My Allocation").run()
    key = [ni for ni in at.number_input
           if ni.key and ni.key.startswith("alloc_")
           and "Crypto Max-Sharpe" in ni.label][0]
    key.set_value(1000.0)
    at.run()
    caps = "\n".join(c.value for c in at.caption)
    assert "no news tone to show" in caps


def test_whole_portfolio_bridge():
    """The aggregate bridge loads ALL saved mixes (dollar-weighted) into
    the Practice setup with the combined amount."""
    at = make_app()
    button(at, "Explore the funds").click().run()
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    nav.set_value("My Allocation").run()
    button(at, "Split evenly").click().run()
    button(at, "Save this allocation to My Portfolio").click().run()
    button(at, "Split evenly").click().run()
    button(at, "Save this allocation to My Portfolio").click().run()
    at.run()
    button(at, "Test my whole portfolio in the time machine").click().run()
    assert not at.exception
    nav = [r for r in at.radio if "My Allocation" in list(r.options)][0]
    assert nav.value == "Practice"
    assert abs(at.session_state["setup_total_amount"] - 2000.0) < 1e-9
    setup_total = sum(at.session_state[f"setup_alloc_{i}"] for i in range(20)
                      if f"setup_alloc_{i}" in at.session_state)
    assert abs(setup_total - 2000.0) < 2.0


def test_blind_walk_to_data_end_no_crash():
    """Reaching the end of the data in blind mode must not crash the jump
    widget (the union calendar runs past 2023-12-29)."""
    at = make_app()
    button(at, "Start in the practice area").click().run()
    button(at, "Split evenly").click().run()
    r = [x for x in at.radio
         if "Blind walk - the future is hidden" in list(x.options)][0]
    r.set_value("Blind walk - the future is hidden").run()
    button(at, "Start travelling").click().run()
    # simulate having walked to the very end of the union calendar
    sim = at.session_state["sim"]
    import pandas as pd
    sim["frontier"] = pd.Timestamp("2023-12-31")
    sim["view_date"] = pd.Timestamp("2023-12-31")
    at.run()
    assert not at.exception


def test_sidebar_mechanism_expander():
    """The sidebar must carry the 'How every fund is built' explainer - the
    transparency window showing funds are rule-built, not randomly named."""
    at = make_app()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert "How every fund is built" in labels


def test_fact_sheet_worked_example_plain_mode():
    """Plain mode shows the worked construction example with REAL numbers
    from the committed weights (default fund: Combined Equal-Weight,
    100% / 60 = 1.67% per asset)."""
    at = make_app()
    button(at, "Explore the funds").click().run()
    assert not at.exception
    texts = [m.value for m in at.markdown]
    assert any("1.67" in t and "in every asset" in t for t in texts)
    assert not at.latex  # formulas belong to professional mode only


def test_fact_sheet_formula_pro_mode():
    """Professional mode renders the method's construction formula as
    LaTeX on the fund fact sheet."""
    at = make_app()
    button(at, "Explore the funds").click().run()
    lang = [r for r in at.radio if r.key == "lang"][0]
    lang.set_value("Professional").run()
    assert not at.exception
    assert len(at.latex) >= 1
