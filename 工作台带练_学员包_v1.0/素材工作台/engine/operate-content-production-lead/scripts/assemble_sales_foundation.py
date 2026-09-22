#!/usr/bin/env python3
"""Assemble one task-level sales foundation from shared context and strategy."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _text(value, fallback="") -> str:
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    return str(value or fallback).strip()


def assemble(context: dict, strategy: dict) -> dict:
    if context.get("schema_version") != "shared_enterprise_context/v1":
        raise ValueError("需要企业白皮书")
    if strategy.get("schema_version") != "strategy_to_production/v1":
        raise ValueError("需要当前内容方向")
    if strategy.get("context_id") != context.get("context_id"):
        raise ValueError("当前内容方向和企业白皮书不是同一版本")

    foundation = context.get("strategy_foundation") or {}
    customer = foundation.get("customer") or {}
    battlefield = foundation.get("battlefield") or {}
    solution = foundation.get("solution") or {}
    decision = foundation.get("decision_path") or {}
    scene = battlefield.get("primary_scene") or strategy.get("customer_scene") or ""
    if isinstance(scene, dict):
        scene = scene.get("statement") or " · ".join(
            _text(scene.get(key)) for key in ("time", "action", "feeling") if _text(scene.get(key))
        )
    actors = decision.get("actors") or []
    actor_summary = "；".join(
        f'{_text(item.get("role"), "做决定的人")}在意：{_text(item.get("main_concern"), "暂未写明")}'
        for item in actors if isinstance(item, dict)
    )
    evidence = _text(solution.get("evidence"))
    if not evidence:
        evidence = "；".join(
            _text(item.get("statement")) for item in strategy.get("usable_evidence") or []
            if isinstance(item, dict) and _text(item.get("statement"))
        )

    result = {
        "schema_version": "sales_foundation/v1",
        "task_id": strategy.get("task_id"),
        "context_id": context.get("context_id"),
        "created_at": datetime.now().astimezone().isoformat(),
        "audience": _text(customer.get("primary_segment"), _text(strategy.get("target_audience"))),
        "customer_moment": _text(scene, _text(strategy.get("customer_scene"))),
        "visible_problem": _text(customer.get("visible_symptoms")),
        "root_problem": _text(customer.get("root_problem")),
        "desired_outcome": _text(customer.get("desired_outcome_scene")),
        "comparison": _text(solution.get("comparison_against")),
        "primary_advantage": _text(solution.get("primary_advantage")),
        "positioning": _text(solution.get("positioning_sentence")),
        "usable_proof": evidence,
        "decision_people": actor_summary,
        "main_barrier": _text(decision.get("primary_barrier")),
        "barrier_answer": _text(decision.get("mitigation")),
        "belief_to_change": _text(strategy.get("belief_change")),
        "next_action": _text(strategy.get("desired_action"), _text(decision.get("next_action"))),
        "destination": strategy.get("touch_destination") or {},
        "single_variable": strategy.get("single_variable") or {},
        "expression_boundaries": strategy.get("expression_boundaries") or [],
        "source_refs": list(dict.fromkeys([context.get("context_id"), *(strategy.get("source_refs") or [])])),
    }
    important = ("audience", "customer_moment", "root_problem", "primary_advantage", "next_action")
    result["known_gaps"] = [key for key in important if not result.get(key)]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--strategy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assemble(
        json.loads(args.context.read_text(encoding="utf-8")),
        json.loads(args.strategy.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
