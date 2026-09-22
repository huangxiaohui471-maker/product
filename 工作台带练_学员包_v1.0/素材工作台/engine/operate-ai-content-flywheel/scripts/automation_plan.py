#!/usr/bin/env python3
"""Small recurring plan for the two V1 jobs: daily discovery and weekly review."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def default_plan(timezone: str = "Asia/Shanghai", daily_time: str = "09:00", weekly_day: int = 0, weekly_time: str = "09:30") -> dict:
    return {
        "schema_version": "content_flywheel_automation/v1",
        "timezone": timezone,
        "paused": False,
        "jobs": [
            {"job_id": "daily-discovery", "label": "每天找新素材", "cadence": "daily", "time": daily_time, "goal": "find_direction", "enabled": True, "last_window": None},
            {"job_id": "weekly-review", "label": "每周复盘上周内容", "cadence": "weekly", "weekday": weekly_day, "time": weekly_time, "goal": "review_results", "enabled": True, "last_window": None},
        ],
    }


def due_jobs(plan: dict, now: datetime) -> list[dict]:
    if plan.get("paused"):
        return []
    tz = ZoneInfo(plan.get("timezone") or "Asia/Shanghai")
    local = now.astimezone(tz)
    due = []
    for job in plan.get("jobs") or []:
        if not job.get("enabled"):
            continue
        hour, minute = (int(x) for x in str(job.get("time") or "09:00").split(":", 1))
        scheduled = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if job.get("cadence") == "weekly":
            scheduled -= timedelta(days=(scheduled.weekday() - int(job.get("weekday", 0))) % 7)
            window = scheduled.date().isoformat() + ":weekly"
        else:
            window = scheduled.date().isoformat() + ":daily"
        if local >= scheduled and job.get("last_window") != window:
            due.append({**job, "window": window, "scheduled_at": scheduled.isoformat()})
    return due


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--daily-time", default="09:00")
    parser.add_argument("--weekly-time", default="09:30")
    parser.add_argument("--weekly-day", type=int, default=0)
    args = parser.parse_args()
    plan = default_plan(args.timezone, args.daily_time, args.weekly_day, args.weekly_time)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("每天找素材、每周复盘已经安排好；需要修改或暂停时直接告诉我。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
