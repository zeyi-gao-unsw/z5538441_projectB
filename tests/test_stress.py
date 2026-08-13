"""Stress tests for streamlit_app.py (HyperInvest, Part B).

Two layers, run from the project folder:

    python -m pytest tests/test_stress.py -q

- ENGINE: direct calls into simulate(), _blind_next(), _blind_jump_target()
  and _evaluate_cards() (importing streamlit_app runs it in bare mode -
  harmless, same as tests/test_app.py).
- UI FLOWS: streamlit.testing.v1.AppTest drives the real widgets on every
  tab (landing, Funds, My Allocation, Sentiment, Practice).

Every scenario drives the app to a boundary and asserts sane behaviour:
no exceptions, no NaN/negative money, guards hold, and state stays
consistent. Nothing here writes to results/ - the app reads the committed
CSVs only.
"""
from __future__ import annotations

import copy
import datetime
import logging
import pathlib
import sys
import warnings

import numpy as np
import pandas as pd
import pytest

# The bare-mode import below prints Streamlit warnings; keep test output clean.
logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = ROOT / "streamlit_app.py"

import streamlit_app as appmod  # noqa: E402  (bare mode is harmless)

RETURNS, WEIGHTS, SENTIMENT, METRICS, SENT_SUMMARY, CALENDAR = appmod.load_data()
START = appmod.PRACTICE_START_MIN          # 2021-02-01: earliest walk start
END = RETURNS.index[-1]                    # 2023-12-31: true data end
DAYS = list(RETURNS.loc[START:].index)     # walk calendar from the min start
N = appmod.N_FUNDS
W_FIRST = [1.0] + [0.0] * (N - 1)          # 100% Combined Equal-Weight


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def make_app() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    return at


def btn(at: AppTest, label: str, key: str | None = None):
    """Fresh lookup every call - element refs go stale after each .run()."""
    matches = [b for b in at.button
               if b.label == label and (key is None or b.key == key)]
    assert matches, (
        f"button {label!r} (key={key}) not found; "
        f"have {[(b.label, b.key) for b in at.button]}")
    return matches[0]


def nav_to(at: AppTest, tab: str) -> None:
    [r for r in at.radio if r.key == "nav"][0].set_value(tab).run()


def goto_allocation(at: AppTest) -> None:
    btn(at, "Explore the funds").click().run()
    nav_to(at, "My Allocation")


def start_walk(at: AppTest, blind: bool = False,
               start: datetime.date | None = None) -> None:
    """Land on Practice, configure, and press Start travelling."""
    btn(at, "Start in the practice area").click().run()
    if start is not None:
        [d for d in at.date_input
         if d.key == "setup_date"][0].set_value(start).run()
    btn(at, "Split evenly").click().run()
    if blind:
        [x for x in at.radio if x.key == "setup_mode"][0].set_value(
            "Blind walk - the future is hidden").run()
    btn(at, "Start travelling").click().run()
    assert not at.exception


def start_decision(amount: float = 1000.0, date: pd.Timestamp = START,
                   weights: list | None = None) -> dict:
    return {"date": date, "kind": "start", "amount": amount,
            "weights": weights if weights is not None else list(W_FIRST)}


def alloc_total(at: AppTest, prefix: str = "alloc_") -> float:
    return sum(at.session_state[f"{prefix}{i}"] for i in range(N)
               if f"{prefix}{i}" in at.session_state)


def value_metric(at: AppTest) -> str:
    vals = [m.value for m in at.metric if m.label == "Portfolio value"]
    assert vals, "Portfolio value metric not rendered"
    return vals[0]


# ---------------------------------------------------------------------------
# ENGINE - withdrawals, zero states, boundaries, determinism
# ---------------------------------------------------------------------------

def test_engine_withdraw_more_than_value_caps():
    """A withdrawal larger than the portfolio is capped at the current
    value: holdings floor at $0, never negative, and paid-in drops by the
    actual value, not by the requested amount."""
    d1 = DAYS[40]
    pre = appmod.simulate({"start_date": START,
                           "decisions": [start_decision()]}, RETURNS, d1)
    v = float(pre["values"].iloc[-1])
    assert v > 0
    sim = {"start_date": START, "decisions": [start_decision(),
           {"date": d1, "kind": "withdraw", "amount": v * 10.0}]}
    st = appmod.simulate(sim, RETURNS, END)
    assert float(st["values"].loc[d1]) == pytest.approx(0.0, abs=1e-9)
    assert float(st["values"].min()) >= 0.0
    assert not (np.asarray(st["holdings"]) < -1e-9).any()
    # paid-in fell by exactly the portfolio value (the cap), no more
    assert float(st["paid"].loc[d1]) == pytest.approx(1000.0 - v, abs=1e-6)


def test_engine_withdraw_entire_value_zero_portfolio():
    """Withdrawing EVERYTHING: the portfolio sits at exactly $0 with zero
    holdings, zero effective weights and zero daily returns - and the
    learning cards still evaluate without crashing (the drift card is
    correctly skipped on an empty portfolio)."""
    d1 = DAYS[40]
    pre = appmod.simulate({"start_date": START,
                           "decisions": [start_decision()]}, RETURNS, d1)
    v = float(pre["values"].iloc[-1])
    sim = {"start_date": START, "fired": [],
           "decisions": [start_decision(),
                         {"date": d1, "kind": "withdraw", "amount": v}]}
    st = appmod.simulate(sim, RETURNS, END)
    assert float(st["values"].loc[d1]) == pytest.approx(0.0, abs=1e-9)
    assert float(st["values"].min()) >= 0.0
    assert not st["values"].isna().any()
    assert np.allclose(st["holdings"], 0.0)
    assert float(st["eff"].loc[d1].sum()) == 0.0
    assert float(st["daily_ret"].loc[d1]) == 0.0
    # cards on a $0 portfolio: factual drawdown cards may fire, the drift
    # card must NOT (nothing is held, so nothing can have drifted)
    new = appmod._evaluate_cards(sim, appmod.simulate(sim, RETURNS, d1),
                                 RETURNS, CALENDAR, d1)
    fired_ids = {f["id"] for f in sim["fired"]}
    assert "drift" not in fired_ids
    assert fired_ids <= {"dd_10", "dd_20", "big_day", "end"}
    assert set(new) <= fired_ids


def test_engine_add_after_total_withdrawal():
    """Money added to an empty portfolio starts compounding again from the
    last target mix: value jumps to the added amount, weights re-normalise,
    and net paid-in tracks every flow exactly."""
    d1, d2 = DAYS[40], DAYS[60]
    pre = appmod.simulate({"start_date": START,
                           "decisions": [start_decision()]}, RETURNS, d1)
    v = float(pre["values"].iloc[-1])
    sim = {"start_date": START, "decisions": [start_decision(),
           {"date": d1, "kind": "withdraw", "amount": v},
           {"date": d2, "kind": "add", "amount": 500.0}]}
    st = appmod.simulate(sim, RETURNS, END)
    assert float(st["values"].loc[d1]) == pytest.approx(0.0, abs=1e-9)
    assert float(st["values"].loc[d2]) == pytest.approx(500.0, abs=1e-9)
    assert float(st["values"].iloc[-1]) > 0.0
    assert not st["values"].isna().any()
    # effective weights are the start mix again from the day after the add
    assert float(st["eff"].loc[DAYS[61]].sum()) == pytest.approx(1.0)
    assert float(st["paid"].iloc[-1]) == pytest.approx(1000.0 - v + 500.0)


def test_engine_start_on_last_day_of_data():
    """A walk that starts on the final data day has exactly one observation,
    earns nothing, fires only the end-of-data card, and the continuation
    series is empty - nothing divides by zero."""
    sim = {"start_date": END, "fired": [],
           "decisions": [start_decision(date=END)]}
    st = appmod.simulate(sim, RETURNS, END)
    assert len(st["values"]) == 1
    assert float(st["values"].iloc[-1]) == pytest.approx(1000.0)
    assert float(st["daily_ret"].iloc[-1]) == 0.0
    new = appmod._evaluate_cards(sim, st, RETURNS, CALENDAR, END)
    assert new == ["end"]
    cont = appmod._continuation(RETURNS, st["holdings"], END)
    assert cont.empty


def test_engine_first_day_to_last_day_full_run():
    """Start at the first walkable day and run to the end: one value per
    calendar day, no NaN, never negative."""
    st = appmod.simulate({"start_date": START,
                          "decisions": [start_decision()]}, RETURNS, END)
    assert len(st["values"]) == len(DAYS)
    assert not st["values"].isna().any()
    assert float(st["values"].min()) >= 0.0
    assert not st["eff"].isna().any().any()


def test_engine_determinism_replay_back_and_forth():
    """Same decision log -> identical numbers, however often the traveller
    revisits a date. Simulate to a mid date, travel back over it, replay to
    the same date: the series must be bit-identical."""
    decisions = [start_decision(),
                 {"date": DAYS[100], "kind": "mix",
                  "weights": [0.5, 0.5] + [0.0] * (N - 2)},
                 {"date": DAYS[200], "kind": "add", "amount": 250.0},
                 {"date": DAYS[300], "kind": "withdraw", "amount": 100.0}]
    sim_a = {"start_date": START, "decisions": decisions}
    sim_b = copy.deepcopy(sim_a)
    mid, early = DAYS[500], DAYS[50]
    first = appmod.simulate(sim_a, RETURNS, mid)
    appmod.simulate(sim_a, RETURNS, early)          # travel back over it
    again = appmod.simulate(sim_a, RETURNS, mid)    # re-replay
    pd.testing.assert_series_equal(first["values"], again["values"])
    pd.testing.assert_frame_equal(first["eff"], again["eff"])
    pd.testing.assert_series_equal(first["paid"], again["paid"])
    pd.testing.assert_series_equal(first["daily_ret"], again["daily_ret"])
    # and two independent copies of the log agree to the very end
    b1 = appmod.simulate(sim_b, RETURNS, END)
    b2 = appmod.simulate(copy.deepcopy(sim_a), RETURNS, END)
    pd.testing.assert_series_equal(b1["values"], b2["values"])


# ---------------------------------------------------------------------------
# ENGINE - blind-step and jump rules
# ---------------------------------------------------------------------------

def test_engine_blind_next_boundaries():
    """_blind_next at every boundary: stays put at the data end, steps
    daily inside a turbulent window (including its last day), and monthly
    steps land exactly on month-end dates and never jump over a storm."""
    # at the data end: stays put
    assert appmod._blind_next(END, DAYS, CALENDAR) == END
    # inside a window: exactly one day ahead
    assert appmod._blind_next(pd.Timestamp("2021-05-06"), DAYS, CALENDAR) \
        == pd.Timestamp("2021-05-07")
    # last day of a window: still daily (the storm is not over until it ends)
    assert appmod._blind_next(pd.Timestamp("2021-05-26"), DAYS, CALENDAR) \
        == pd.Timestamp("2021-05-27")
    # month-end boundaries in calm periods: exactly one month ahead
    assert appmod._blind_next(pd.Timestamp("2021-03-31"), DAYS, CALENDAR) \
        == pd.Timestamp("2021-04-30")
    assert appmod._blind_next(pd.Timestamp("2021-10-31"), DAYS, CALENDAR) \
        == pd.Timestamp("2021-11-30")
    assert appmod._blind_next(pd.Timestamp("2021-12-31"), DAYS, CALENDAR) \
        == pd.Timestamp("2022-01-31")
    # Jan 31 -> Feb 28 (short month): DateOffset lands on a real data day
    assert appmod._blind_next(pd.Timestamp("2023-01-31"), DAYS, CALENDAR) \
        == pd.Timestamp("2023-02-28")
    # a monthly step never jumps OVER a window start: it lands on the storm
    assert appmod._blind_next(pd.Timestamp("2021-04-30"), DAYS, CALENDAR) \
        == pd.Timestamp("2021-05-05")
    # day pace in a calm period: exactly one day
    assert appmod._blind_next(pd.Timestamp("2021-03-01"), DAYS, CALENDAR,
                              pace="day") == pd.Timestamp("2021-03-02")


def test_engine_blind_jump_target_edges():
    """_blind_jump_target: a target at/before the frontier goes nowhere;
    a target past the data end (with no storm in between) returns the raw
    target, and the snap used by the app clamps it to the last data day."""
    cur = pd.Timestamp("2021-04-06")
    # target before frontier: stays put
    assert appmod._blind_jump_target(cur, pd.Timestamp("2021-03-01"),
                                     DAYS, CALENDAR) == cur
    # target exactly at the frontier: stays put
    assert appmod._blind_jump_target(cur, cur, DAYS, CALENDAR) == cur
    # target past the data end, starting AFTER the last turbulent window
    # (Banking stress, 2023-03-03 to 2023-03-17): no guard fires, the raw
    # target comes back ...
    late = pd.Timestamp("2023-04-03")
    raw = appmod._blind_jump_target(late, pd.Timestamp("2024-06-01"),
                                    DAYS, CALENDAR)
    assert raw == pd.Timestamp("2024-06-01")
    # ... and the app's snap clamps it to the true last day
    assert appmod._snap_on_or_after(raw, DAYS) == END
    # a storm in between still stops the jump, even past the data end
    assert appmod._blind_jump_target(cur, pd.Timestamp("2024-06-01"),
                                     DAYS, CALENDAR) \
        == pd.Timestamp("2021-05-05")
    # and from just before the LAST storm, a jump past the data end stops
    # at that storm's start (2023-03-03, Banking stress)
    assert appmod._blind_jump_target(pd.Timestamp("2023-01-03"),
                                     pd.Timestamp("2024-06-01"),
                                     DAYS, CALENDAR) \
        == pd.Timestamp("2023-03-03")


# ---------------------------------------------------------------------------
# UI - landing
# ---------------------------------------------------------------------------

def test_ui_landing_both_entries_and_language_toggle():
    """Both landing buttons navigate to their tab, and the language toggle
    works from the landing page in both directions without an exception."""
    at = make_app()
    btn(at, "Explore the funds").click().run()
    assert not at.exception
    assert at.session_state["nav"] == "Funds"

    at = make_app()
    btn(at, "Start in the practice area").click().run()
    assert not at.exception
    assert at.session_state["nav"] == "Practice"

    at = make_app()
    [r for r in at.radio if r.key == "lang"][0].set_value(
        "Professional").run()
    assert not at.exception
    md = "\n".join(m.value for m in at.markdown)
    assert "out-of-sample backtests" in md  # the pro tagline swapped in
    [r for r in at.radio if r.key == "lang"][0].set_value(
        "Plain English").run()
    assert not at.exception
    md = "\n".join(m.value for m in at.markdown)
    assert "Eight systematic funds" in md


# ---------------------------------------------------------------------------
# UI - My Allocation: the amount-field gate and saved-mix cards
# ---------------------------------------------------------------------------

def test_ui_alloc_neutral_zero_zero():
    """Amount 0 + all boxes 0: the neutral state - guidance caption, no
    metrics, no chart, no save button, no crash."""
    at = make_app()
    goto_allocation(at)
    [ni for ni in at.number_input
     if ni.key == "alloc_total_amount"][0].set_value(0.0).run()
    assert not at.exception
    caps = "\n".join(c.value for c in at.caption)
    assert "Enter an amount to invest" in caps
    assert len(at.metric) == 0
    assert not [b for b in at.button
                if b.label == "Save this allocation to My Portfolio"]


def test_ui_alloc_boxes_over_amount():
    """Boxes totalling more than the declared amount: the over state hides
    the results and says so - no partial render, no crash."""
    at = make_app()
    goto_allocation(at)
    [ni for ni in at.number_input if ni.key == "alloc_0"][0] \
        .set_value(2000.0).run()  # vs the $1,000 default amount
    assert not at.exception
    caps = "\n".join(c.value for c in at.caption)
    assert "Over by" in caps
    assert len(at.metric) == 0
    assert not [b for b in at.button
                if b.label == "Save this allocation to My Portfolio"]


def test_ui_alloc_amount_zero_with_boxes_filled():
    """Amount 0 with boxes filled: still the over state, and the guidance
    names the two ways out (reduce a fund or raise the amount)."""
    at = make_app()
    goto_allocation(at)
    [ni for ni in at.number_input
     if ni.key == "alloc_total_amount"][0].set_value(0.0).run()
    [ni for ni in at.number_input if ni.key == "alloc_0"][0] \
        .set_value(500.0).run()
    assert not at.exception
    caps = "\n".join(c.value for c in at.caption)
    assert "Over by" in caps
    assert "reduce a fund or raise the amount" in caps
    assert len(at.metric) == 0


def test_ui_alloc_gate_boundary_exact_and_tolerance():
    """The gate opens when the boxes sum to the amount EXACTLY, and at the
    +/-$0.5 rounding tolerance - but not one cent past it."""
    at = make_app()
    goto_allocation(at)
    box = lambda: [ni for ni in at.number_input if ni.key == "alloc_0"][0]
    save = lambda: [b for b in at.button
                    if b.label == "Save this allocation to My Portfolio"]

    box().set_value(1000.0).run()          # exact
    assert len(at.metric) >= 4 and save()
    box().set_value(1000.5).run()          # +0.5: still inside tolerance
    assert len(at.metric) >= 4 and save()
    box().set_value(1000.6).run()          # +0.6: over
    caps = "\n".join(c.value for c in at.caption)
    assert "Over by" in caps and len(at.metric) == 0 and not save()
    box().set_value(999.5).run()           # -0.5: still inside tolerance
    assert len(at.metric) >= 4 and save()
    box().set_value(999.4).run()           # -0.6: under
    caps = "\n".join(c.value for c in at.caption)
    assert "Not yet placed" in caps and len(at.metric) == 0 and not save()
    assert not at.exception


def test_ui_alloc_save_two_remove_first_reindexes():
    """Save two DIFFERENT mixes, remove the FIRST card: the survivor
    reindexes cleanly to position 0 (working buttons, no 'Mix 2' label,
    aggregate block gone), nothing crashes."""
    at = make_app()
    goto_allocation(at)
    btn(at, "Split evenly").click().run()
    btn(at, "Save this allocation to My Portfolio").click().run()
    [ni for ni in at.number_input if ni.key == "alloc_8"][0] \
        .set_value(1000.0).run()           # second mix: 100% Crypto EW
    btn(at, "Save this allocation to My Portfolio").click().run()
    assert len(at.session_state["saved_allocs"]) == 2

    btn(at, "Remove", key="remove_0").click().run()
    assert not at.exception
    saved = at.session_state["saved_allocs"]
    assert len(saved) == 1
    assert list(saved[0]["alloc"].keys()) == ["Crypto Equal-Weight"]
    md = "\n".join(m.value for m in at.markdown)
    assert "Mix 2" not in md
    assert "whole portfolio" not in md     # aggregate needs 2+ mixes
    # the reindexed card's buttons exist and still work
    btn(at, "Load into editor", key="load_0").click().run()
    assert not at.exception
    assert alloc_total(at) == pytest.approx(1000.0, abs=1.0)


def test_ui_alloc_save_same_mix_twice():
    """Saving the identical mix twice stores two independent cards and the
    aggregate counts both - duplicates are allowed by design (each save is
    a deliberate user act)."""
    at = make_app()
    goto_allocation(at)
    btn(at, "Split evenly").click().run()
    btn(at, "Save this allocation to My Portfolio").click().run()
    btn(at, "Split evenly").click().run()
    btn(at, "Save this allocation to My Portfolio").click().run()
    assert not at.exception
    saved = at.session_state["saved_allocs"]
    assert len(saved) == 2
    assert saved[0]["alloc"] == saved[1]["alloc"]
    md = "\n".join(m.value for m in at.markdown)
    assert "whole portfolio" in md
    assert sum(e["amount"] for e in saved) == 2000.0


def test_ui_alloc_load_then_remove_no_dangling_state():
    """Load a saved mix into the editor, then remove the saved card: the
    editor keeps the loaded dollars (they are the user's working state),
    the saved list is empty, and the results view still renders."""
    at = make_app()
    goto_allocation(at)
    btn(at, "Split evenly").click().run()
    btn(at, "Save this allocation to My Portfolio").click().run()
    btn(at, "Load into editor", key="load_0").click().run()
    assert alloc_total(at) == pytest.approx(1000.0, abs=1.0)
    btn(at, "Remove", key="remove_0").click().run()
    assert not at.exception
    assert len(at.session_state["saved_allocs"]) == 0
    assert alloc_total(at) == pytest.approx(1000.0, abs=1.0)
    assert len(at.metric) >= 4  # gate still satisfied by the loaded boxes


def test_ui_alloc_news_exposure_panel_renders():
    """With the gate satisfied, the news-exposure bridge panel renders its
    chart caption (the factual neutrality line rides along)."""
    at = make_app()
    goto_allocation(at)
    btn(at, "Split evenly").click().run()
    assert not at.exception
    caps = "\n".join(c.value for c in at.caption)
    assert "does not predict returns" in caps


# ---------------------------------------------------------------------------
# UI - Practice (the time machine)
# ---------------------------------------------------------------------------

def test_ui_practice_restart_without_stepping_and_twice():
    """Restart walk pressed before any step - and pressed twice in a row -
    returns the walk to day one with one decision and no fired cards."""
    at = make_app()
    start_walk(at, blind=True)
    btn(at, "Restart walk").click().run()
    sim = at.session_state["sim"]
    assert sim["frontier"] == sim["start_date"]
    assert sim["view_date"] == sim["start_date"]
    assert len(sim["decisions"]) == 1
    assert sim["fired"] == []
    btn(at, "Restart walk").click().run()   # idempotent
    assert not at.exception
    sim = at.session_state["sim"]
    assert sim["frontier"] == sim["start_date"]
    assert len(sim["decisions"]) == 1


def test_ui_practice_blind_walk_to_end_then_forward_stays_put():
    """At the end of the data the forward button is a no-op: the frontier
    never moves past the last day, the debrief renders, nothing breaks."""
    at = make_app()
    start_walk(at, blind=True)
    sim = at.session_state["sim"]
    sim["frontier"] = END                    # as if walked all the way
    sim["view_date"] = END
    at.run()
    assert not at.exception
    txt = "\n".join(c.value for c in at.caption)
    assert "never touched" in txt            # the debrief body
    n_dec = len(at.session_state["sim"]["decisions"])
    btn(at, "▶").click().run()               # press forward at the end
    assert not at.exception
    sim = at.session_state["sim"]
    assert sim["frontier"] == END
    assert sim["view_date"] == END
    assert len(sim["decisions"]) == n_dec


def test_ui_practice_replay_slider_to_last_day():
    """Dragging the Replay timeline to the final day lands exactly there."""
    at = make_app()
    start_walk(at)                           # replay mode
    at.select_slider[0].set_value(END).run()
    at.run()                                 # absorb the st.rerun follow-up
    assert not at.exception
    assert at.session_state["sim"]["view_date"] == END


def test_ui_practice_language_switch_mid_walk():
    """Flipping Plain -> Professional -> Plain in the middle of a walk
    keeps the walk state and never raises."""
    at = make_app()
    start_walk(at)
    for _ in range(3):
        btn(at, "▶").click().run()
    pos = at.session_state["sim"]["view_date"]
    [r for r in at.radio if r.key == "lang"][0].set_value(
        "Professional").run()
    assert not at.exception
    assert at.session_state["sim"]["view_date"] == pos
    [r for r in at.radio if r.key == "lang"][0].set_value(
        "Plain English").run()
    assert not at.exception
    assert at.session_state["sim"]["view_date"] == pos


def test_ui_practice_start_on_last_selectable_day():
    """Start date = the last selectable day (2023-12-29): one monthly step
    lands on the true data end, further steps stay put, the debrief
    appears."""
    at = make_app()
    start_walk(at, blind=True, start=datetime.date(2023, 12, 29))
    sim = at.session_state["sim"]
    assert sim["start_date"] == pd.Timestamp("2023-12-29")
    btn(at, "▶").click().run()
    assert not at.exception
    assert at.session_state["sim"]["frontier"] == END
    btn(at, "▶").click().run()               # past the end: stays put
    assert not at.exception
    assert at.session_state["sim"]["frontier"] == END
    txt = "\n".join(c.value for c in at.caption)
    assert "never touched" in txt


def test_ui_practice_zero_mix_is_rejected():
    """Regression: a mix change with all-zero amounts must be REJECTED -
    the Apply button is disabled, and even if a click slips through, the
    callback appends nothing (an unguarded division used to poison the
    whole walk with NaN weights)."""
    at = make_app()
    start_walk(at)
    sim = at.session_state["sim"]
    dk = sim["view_date"].strftime("%Y%m%d")
    for i in range(N):
        matches = [x for x in at.number_input if x.key == f"mix_{dk}_{i}"]
        if matches:
            matches[0].set_value(0.0)
    at.run()
    apply_btn = [b for b in at.button if b.label == "Apply the new mix"][0]
    assert apply_btn.disabled
    apply_btn.click().run()                  # harness CAN click disabled
    assert not at.exception
    sim = at.session_state["sim"]
    assert len(sim["decisions"]) == 1        # nothing was appended
    assert sim["decisions"][0]["kind"] == "start"
    # and the rendered value is still a number, never NaN
    assert value_metric(at).startswith("$")


def test_ui_practice_withdraw_cap_and_add_after_via_widgets():
    """Through the real widgets: asking to take out $5,000 of a $1,000
    portfolio records a $1,000 withdrawal (the cap), the value hits $0,
    and adding $500 afterwards restarts the balance at exactly $500."""
    at = make_app()
    start_walk(at)                           # $1,000 split evenly, replay
    dk = at.session_state["sim"]["view_date"].strftime("%Y%m%d")
    [x for x in at.radio if x.key == f"dir_{dk}"][0] \
        .set_value("Take out money").run()
    [x for x in at.number_input if x.key == f"money_{dk}"][0] \
        .set_value(5000.0).run()
    [b for b in at.button if b.label == "Apply"][0].click().run()
    assert not at.exception
    dec = at.session_state["sim"]["decisions"]
    assert dec[-1] == {"date": pd.Timestamp(START), "kind": "withdraw",
                       "amount": 1000.0}     # capped at the current value
    assert value_metric(at) == "$0"

    [x for x in at.radio if x.key == f"dir_{dk}"][0] \
        .set_value("Add money").run()
    [x for x in at.number_input if x.key == f"money_{dk}"][0] \
        .set_value(500.0).run()
    [b for b in at.button if b.label == "Apply"][0].click().run()
    assert not at.exception
    dec = at.session_state["sim"]["decisions"]
    assert dec[-1]["kind"] == "add" and dec[-1]["amount"] == 500.0
    assert value_metric(at) == "$500"


def test_ui_practice_mix_change_via_widgets():
    """A valid mix change through the widgets appends normalised weights
    (700/300 -> 0.7/0.3) that sum to 1."""
    at = make_app()
    start_walk(at)
    dk = at.session_state["sim"]["view_date"].strftime("%Y%m%d")
    # the boxes default to the current effective dollars - zero them all
    # first so the 700/300 split is the whole mix
    for i in range(N):
        matches = [x for x in at.number_input if x.key == f"mix_{dk}_{i}"]
        if matches:
            matches[0].set_value(0.0)
    [x for x in at.number_input if x.key == f"mix_{dk}_0"][0] \
        .set_value(700.0)
    [x for x in at.number_input if x.key == f"mix_{dk}_8"][0] \
        .set_value(300.0)
    at.run()
    apply_btn = [b for b in at.button if b.label == "Apply the new mix"][0]
    assert not apply_btn.disabled
    apply_btn.click().run()
    assert not at.exception
    dec = at.session_state["sim"]["decisions"][-1]
    assert dec["kind"] == "mix"
    assert dec["weights"][0] == pytest.approx(0.7)
    assert dec["weights"][8] == pytest.approx(0.3)
    assert sum(dec["weights"]) == pytest.approx(1.0)


def test_ui_practice_value_is_deterministic_when_revisiting_dates():
    """Travel forward, note the value, travel back over those dates, then
    forward again: the rendered value at the same date is identical."""
    at = make_app()
    start_walk(at)
    for _ in range(5):
        btn(at, "▶").click().run()
    first = value_metric(at)
    pos = at.session_state["sim"]["view_date"]
    for _ in range(2):
        btn(at, "◀").click().run()
    for _ in range(2):
        btn(at, "▶").click().run()
    assert not at.exception
    assert at.session_state["sim"]["view_date"] == pos
    assert value_metric(at) == first


def test_ui_practice_guarded_jump_and_back_jump():
    """Blind jump-to-date stops at the next storm's start; a jump back
    inside the revealed range moves only the view, not the frontier."""
    at = make_app()
    start_walk(at, blind=True)
    [d for d in at.date_input if d.key == "jump_date"][0] \
        .set_value(datetime.date(2021, 9, 1)).run()
    btn(at, "Jump", key="jump_go").click().run()
    assert not at.exception
    sim = at.session_state["sim"]
    assert sim["frontier"] == pd.Timestamp("2021-05-05")  # storm stop
    assert sim["view_date"] == pd.Timestamp("2021-05-05")

    [d for d in at.date_input if d.key == "jump_date"][0] \
        .set_value(datetime.date(2021, 2, 10)).run()
    btn(at, "Jump", key="jump_go").click().run()
    assert not at.exception
    sim = at.session_state["sim"]
    assert sim["view_date"] == pd.Timestamp("2021-02-10")  # view moved
    assert sim["frontier"] == pd.Timestamp("2021-05-05")   # nothing hidden


# ---------------------------------------------------------------------------
# UI - Sentiment
# ---------------------------------------------------------------------------

def test_ui_sentiment_empty_selection():
    """No sectors picked: the guidance caption appears and no chart is
    drawn - no crash."""
    at = make_app()
    btn(at, "Explore the funds").click().run()
    nav_to(at, "Sentiment")
    at.multiselect[0].set_value([]).run()
    assert not at.exception
    caps = "\n".join(c.value for c in at.caption)
    assert "at least one sector" in caps


def test_ui_sentiment_all_ten_sectors():
    """Every sector selected at once: all ten lines draw without an
    exception."""
    at = make_app()
    btn(at, "Explore the funds").click().run()
    nav_to(at, "Sentiment")
    all_display = [appmod.SECTOR_DISPLAY.get(s, s) for s in appmod.SECTORS]
    assert len(all_display) == 10
    at.multiselect[0].set_value(all_display).run()
    assert not at.exception


def test_ui_sentiment_standardise_and_smoothing_extremes():
    """Standardise ON with the shortest smoothing (1 day), then the longest
    (63 days): both extremes render without an exception."""
    at = make_app()
    btn(at, "Explore the funds").click().run()
    nav_to(at, "Sentiment")
    std = [c for c in at.checkbox
           if "standardise" in (c.label or "").lower()
           or "own usual level" in (c.label or "").lower()]
    assert std, f"standardise checkbox not found: {[c.label for c in at.checkbox]}"
    std[0].set_value(True).run()
    assert not at.exception
    slider = at.slider[0]
    assert slider.min == 1 and slider.max == 63
    slider.set_value(1).run()
    assert not at.exception
    at.slider[0].set_value(63).run()
    assert not at.exception


# ---------------------------------------------------------------------------
# UI - Funds: every fact sheet, and the tiered holdings rule
# ---------------------------------------------------------------------------

def test_ui_funds_every_fact_sheet_renders():
    """Open every one of the 13 fund fact sheets: no exceptions, and the
    tiered holdings logic emits the right artifact per fund - a sentence
    for Equal-Weight funds (weights never change), a sentence + current
    holdings bar for Risk-Parity funds, and the over-time area chart for
    the rest."""
    at = make_app()
    btn(at, "Explore the funds").click().run()
    assert len(at.selectbox[0].options) == 13
    for fund in appmod.FUND_ORDER:
        at.selectbox[0].set_value(fund).run()
        assert not at.exception, f"fact sheet for {fund} raised"
        md = "\n".join(m.value for m in at.markdown)
        tier = fund.split()[-1]  # Equal-Weight / Min-Variance / ...
        if "Equal-Weight" in fund:
            assert "weights never change" in md, fund
        elif "Risk-Parity" in fund:
            assert "too little movement for an over-time chart" in md, fund
        else:
            assert "weights never change" not in md, fund
            assert "too little movement" not in md, fund


def test_engine_holdings_tier_thresholds_match_design():
    """The tier predicate itself: mean |weight change| per rebalance is
    < 1pp for the three Equal-Weight funds (sentence), 1-10pp for the
    three Risk-Parity funds (sentence + bar), and >= 10pp for the seven
    others (area chart) - on the committed weights data."""
    for fund in appmod.FUND_ORDER:
        change_pp, n_reb = appmod.weight_change_pp(WEIGHTS, fund)
        assert n_reb > 1
        if "Equal-Weight" in fund:
            assert change_pp < 1.0, (fund, change_pp)
        elif "Risk-Parity" in fund:
            assert 1.0 <= change_pp < 10.0, (fund, change_pp)
        else:
            assert change_pp >= 10.0, (fund, change_pp)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
