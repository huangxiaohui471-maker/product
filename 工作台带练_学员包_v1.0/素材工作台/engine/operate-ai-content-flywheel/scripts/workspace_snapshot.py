#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from continuity import inspect as inspect_continuity


def read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def build(workspace: Path) -> dict:
    workspace = workspace.expanduser().resolve()
    context = read(workspace / "context/shared_enterprise_context.json")
    strategy = read(workspace / "strategy_to_production.json")
    production = read(workspace / "production_run.json")
    production_done = read(workspace / "production_to_growth.json")
    growth = read(workspace / "growth_learning_return.json")
    continuity=inspect_continuity(workspace)
    active_context = bool(context)
    if not context:
        current = "learn_company"
    elif not active_context:
        current = "building_whitepaper"
    elif not strategy:
        current = "find_direction"
    elif not production:
        current = "make_content"
    elif not production_done:
        current = "review_content" if production.get("status") in {"AWAITING_SELECTION", "AWAITING_REVIEW"} else "make_content"
    elif not growth:
        current = "wait_or_review_results"
    else:
        current = "next_cycle"
    return {
        "workspace": str(workspace),
        "company": context.get("company"),
        "current": current,
        "context_ready": active_context,
        "strategy_ready": bool(strategy),
        "production_ready": bool(production_done),
        "result_ready": bool(growth),
        "continuity": continuity,
    }
