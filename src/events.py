"""Named market events shared by the build script and the app.

Each event has a short label (at most 16 characters, used on charts) and a
longer detail line. The date is the event's first trading day;
scripts/build_event_calendar.py extends each event +/-5 trading days when it
builds results/data/event_calendar.csv, and streamlit_app.py reads that file
for chart shading and annotation. This module holds only static data so the
deployed app can import it safely.
"""

NAMED_EVENTS = [
    {
        "date": "2021-05-19",
        "label": "Crypto sell-off",
        "detail": "Crypto sell-off of May 2021: sharp one-day falls across "
                  "cryptocurrencies.",
    },
    {
        "date": "2022-06-13",
        "label": "Bear market",
        "detail": "June 2022: US shares closed more than 20% below their "
                  "January peak, confirming a bear market.",
    },
    {
        "date": "2022-11-08",
        "label": "FTX collapse",
        "detail": "November 2022: the collapse of the FTX exchange hit "
                  "cryptocurrency prices.",
    },
    {
        "date": "2023-03-10",
        "label": "Banking stress",
        "detail": "March 2023: US regional-bank stress around the failure "
                  "of Silicon Valley Bank.",
    },
]
