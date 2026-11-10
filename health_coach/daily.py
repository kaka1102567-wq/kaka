"""Daily entry point: pull Intervals.icu data, assess readiness, report.

Usage:
    python -m health_coach.daily              # print report
    python -m health_coach.daily --telegram   # also send to Telegram
    python -m health_coach.daily --json       # print metrics as JSON
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

from .coach import assess, build_report
from .intervals_client import IntervalsClient


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (default: today in athlete timezone)")
    p.add_argument("--telegram", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    tz = ZoneInfo(os.environ.get("COACH_TZ", "Asia/Phnom_Penh"))
    as_of = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(tz).date()

    client = IntervalsClient()
    athlete = client.athlete()
    wellness = client.wellness((as_of - dt.timedelta(days=28)).isoformat(), as_of.isoformat())
    activities = client.activities((as_of - dt.timedelta(days=42)).isoformat(), as_of.isoformat())

    rd = assess(wellness, activities, as_of, athlete)
    if a.json:
        print(json.dumps({"level": rd.level, "reasons": rd.reasons, "metrics": rd.metrics},
                         ensure_ascii=False, indent=2))
    report = build_report(rd)
    print(report)

    if a.telegram:
        from .telegram import send_message
        send_message(report)
        print("\n[sent to Telegram]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
