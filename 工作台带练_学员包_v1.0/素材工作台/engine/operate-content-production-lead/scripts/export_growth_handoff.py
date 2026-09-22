#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from validate_production_bundle import validate


def export(bundle: dict) -> dict:
    errors = validate(bundle)
    if errors:
        raise ValueError("生产包未通过检查：" + ";".join(errors))
    selected_id = bundle.get("selected_script")
    selected = next((x for x in bundle.get("script_candidates") or [] if x.get("candidate_id") == selected_id), None)
    explicit = bundle.get("current_artifact") or bundle.get("adopted_artifact")
    suites = bundle.get("image_suites") or []
    if explicit:
        artifact = explicit
        channel_variants = artifact.get("channel_variants") or [{"channel": "待发布渠道", "position": "当前作品", "locator": artifact["locator"]}]
        content_master = {"type": artifact["type"], "locator": artifact["locator"]}
        human_edits = artifact.get("human_edits") or []
        source_refs = artifact.get("source_refs") or []
    elif selected and suites:
        suite = suites[-1]
        artifact = {
            "artifact_id": suite["suite_id"], "version_id": suite["version_id"],
            "observation_plan": suite.get("observation_plan") or {},
            "known_confounders": suite.get("known_confounders") or [],
        }
        channel_variants = [{"job": x["job"], "position": x["channel_position"], "locator": x["output_path"]} for x in suite["items"]]
        content_master = {"type": selected["format"], "locator": selected.get("output_path") or f"candidate:{selected_id}"}
        human_edits = suite.get("user_feedback") or []
        source_refs = sum([x.get("source_refs") or [] for x in suite["items"]], [])
    else:
        raise ValueError("还没有用户采用的具体版本")
    locked = bundle["locked_strategy"]
    return {
        "schema_version": "production_to_growth/v1",
        "handoff_id": f"handoff-{bundle['run_id']}-{artifact['version_id']}",
        "task_id": bundle["task_id"], "cycle_id": bundle["cycle_id"], "context_id": bundle["context_id"],
        "artifact_id": artifact["artifact_id"], "version_id": artifact["version_id"],
        "created_at": datetime.now().astimezone().isoformat(),
        "content_master": content_master,
        "channel_variants": channel_variants,
        "target_audience": locked["target_audience"], "customer_scene": locked["customer_scene"],
        "single_variable": locked["single_variable"],
        "desired_action": locked["desired_action"],
        "observation_plan": artifact.get("observation_plan") or {"signals": ["平台公开表现"], "window": "发布后按渠道默认时间查看", "record_location": "内容复盘"},
        "known_confounders": artifact.get("known_confounders") or [],
        "human_edits": human_edits,
        "production_line": bundle.get("production_line") or {},
        "production_recipe": bundle.get("production_recipe") or {},
        "source_refs": list(dict.fromkeys([bundle["run_id"], selected_id, artifact["version_id"], *source_refs])),
    }


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("bundle", type=Path); p.add_argument("output", type=Path); a = p.parse_args()
    result = export(json.loads(a.bundle.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(result["handoff_id"]); return 0


if __name__ == "__main__": raise SystemExit(main())
