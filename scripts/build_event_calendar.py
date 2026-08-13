"""Build results/data/event_calendar.csv: turbulent windows + named events.

    python scripts/build_event_calendar.py

Turbulent windows: days where the Combined Equal-Weight fund's absolute daily
move exceeded 2x its full-sample daily standard deviation, clustered into
windows (flagged days fewer than 10 trading days apart are merged). The four
named events from src/events.py are added as windows spanning +/-5 trading
days around the event date; windows that overlap or sit fewer than 10 trading
days apart are merged, with named labels kept. A single isolated flagged day
is not a window: unnamed windows spanning only one trading day are dropped.
The app reads this CSV for chart shading and annotations - it never
recomputes it.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.events import NAMED_EVENTS  # noqa: E402

GAP = 10    # merge flagged days (and windows) fewer than this many trading days apart
PAD = 5     # named events extend +/- this many trading days
REF_FUND = "Combined Equal-Weight"


def main() -> None:
    returns = pd.read_csv(ROOT / "results" / "data" / "fund_returns.csv",
                          parse_dates=["date"]).set_index("date")
    ref = returns[REF_FUND].dropna()
    days = ref.index                      # equity trading calendar
    std = ref.std(ddof=1)
    flagged = [d for d in days if abs(ref.loc[d]) > 2.0 * std]
    print(f"{REF_FUND}: daily std = {std:.4%}; "
          f"{len(flagged)} of {len(days)} days beyond +/-2 std")

    pos = {d: i for i, d in enumerate(days)}

    # Cluster flagged days into [start_pos, end_pos, labels] windows.
    windows: list[list] = []
    for d in flagged:
        p = pos[d]
        if windows and p - windows[-1][1] < GAP:
            windows[-1][1] = p
        else:
            windows.append([p, p, []])

    # Named events: +/- PAD trading days around the event's first trading day.
    for ev in NAMED_EVENTS:
        p = int(days.searchsorted(pd.Timestamp(ev["date"])))
        p = min(p, len(days) - 1)
        windows.append([max(0, p - PAD), min(len(days) - 1, p + PAD),
                        [ev["label"]]])

    # Merge overlapping or near windows; keep named labels in date order.
    windows.sort(key=lambda w: w[0])
    merged: list[list] = []
    for s, e, labels in windows:
        if merged and s - merged[-1][1] < GAP:
            merged[-1][1] = max(merged[-1][1], e)
            merged[-1][2] = list(dict.fromkeys(merged[-1][2] + labels))
        else:
            merged.append([s, e, list(labels)])

    rows = []
    for s, e, labels in merged:
        if not labels and e == s:
            continue  # a single isolated flagged day is not a window
        rows.append({
            "start": days[s].date().isoformat(),
            "end": days[e].date().isoformat(),
            "label": " + ".join(labels) if labels else "Turbulent stretch",
            "trading_days": e - s + 1,
        })
    out = pd.DataFrame(rows, columns=["start", "end", "label", "trading_days"])
    out.to_csv(ROOT / "results" / "data" / "event_calendar.csv", index=False)
    print(f"\nwrote results/data/event_calendar.csv ({len(out)} windows):")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
