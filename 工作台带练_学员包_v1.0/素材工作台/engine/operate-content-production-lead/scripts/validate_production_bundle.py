#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(bundle: dict) -> list[str]:
    errors = []
    locked = bundle.get("locked_strategy") or {}
    required_locked = ("target_audience", "customer_scene", "desired_action", "single_variable")
    for key in required_locked:
        if not locked.get(key): errors.append(f"locked_strategy.{key}:missing")
    candidates = bundle.get("script_candidates") or []
    ids = [row.get("candidate_id") for row in candidates]
    if len(ids) != len(set(ids)): errors.append("script_candidates:duplicate_id")
    for index, row in enumerate(candidates):
        for key in ("format", "body", "strategy_trace"):
            if not row.get(key): errors.append(f"script_candidates[{index}].{key}:missing")
        trace = row.get("strategy_trace") or {}
        for key in ("target_audience", "customer_scene", "belief_change", "desired_action", "single_variable"):
            if trace.get(key) != locked.get(key): errors.append(f"script_candidates[{index}].strategy_trace.{key}:drift")
    selected = bundle.get("selected_script")
    if selected and selected not in ids: errors.append("selected_script:not_in_candidates")
    for s_index, suite in enumerate(bundle.get("image_suites") or []):
        if suite.get("source_script_id") != selected: errors.append(f"image_suites[{s_index}].source_script_id:not_selected")
        if not suite.get("items"): errors.append(f"image_suites[{s_index}].items:missing")
        jobs = [item.get("job") for item in suite.get("items") or []]
        if len(jobs) != len(set(jobs)): errors.append(f"image_suites[{s_index}].items:duplicate_job")
        for i_index, item in enumerate(suite.get("items") or []):
            for key in ("job", "output_path"):
                if not item.get(key): errors.append(f"image_suites[{s_index}].items[{i_index}].{key}:missing")
        if s_index and suite.get("supersedes") != (bundle.get("image_suites") or [])[s_index - 1].get("version_id"):
            errors.append(f"image_suites[{s_index}].supersedes:not_previous_version")
        if s_index and suite.get("version_id") == (bundle.get("image_suites") or [])[s_index - 1].get("version_id"):
            errors.append(f"image_suites[{s_index}].version_id:not_new")
    artifact = bundle.get("adopted_artifact")
    if artifact:
        for key in ("artifact_id", "version_id", "type", "locator"):
            if not artifact.get(key): errors.append(f"adopted_artifact.{key}:missing")
        if artifact.get("type") not in {"script", "article", "image_suite", "shot_pack", "video"}:
            errors.append("adopted_artifact.type:unsupported")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("file", type=Path); args = parser.parse_args()
    errors = validate(json.loads(args.file.read_text(encoding="utf-8")))
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())
