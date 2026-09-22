#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _production_line(strategy: dict) -> dict:
    destination = strategy.get("touch_destination") or {}
    joined = " ".join(str(destination.get(key) or "") for key in ("channel", "position"))
    if any(word in joined.lower() for word in ("抖音", "视频号", "快手", "douyin", "video")):
        line_id, label, output = "short-video", "短视频生产线", "可拍短视频脚本"
    elif any(word in joined.lower() for word in ("海报", "图片", "轮播", "poster", "image")):
        line_id, label, output = "visual-suite", "营销图片生产线", "同一主张的图片套装"
    else:
        line_id, label, output = "sales-content", "销售内容生产线", "可以直接使用的销售内容"
    return {
        "line_id": line_id,
        "label": label,
        "method_id": "sales-foundation-plus-ntf-v4" if line_id == "sales-content" else "strategy-locked-native-v1",
        "method_version": "1.0",
        "recommended_output": output,
        "reason": "系统已根据这次内容出现的位置自动选择",
    }


def initialize(strategy: dict) -> dict:
    if strategy.get("schema_version") != "strategy_to_production/v1":
        raise ValueError("只接受 strategy_to_production/v1")
    return {
        "schema_version": "production_run/v1",
        "run_id": f"prod-{strategy['task_id']}-v{strategy['version']}",
        "task_id": strategy["task_id"],
        "cycle_id": strategy["cycle_id"],
        "context_id": strategy["context_id"],
        "strategy_version": strategy["version"],
        "created_at": datetime.now().astimezone().isoformat(),
        "locked_strategy": {key: strategy.get(key, []) for key in (
            "target_audience", "customer_scene", "belief_change", "desired_action",
            "single_variable", "held_conditions", "usable_evidence", "touch_destination",
            "expression_boundaries", "completion_gate", "material_refs",
        )},
        "production_line": _production_line(strategy),
        "production_recipe": {
            "sales_foundation": "reuse-whitepaper-and-current-strategy",
            "content_method": "ntf-v4" if _production_line(strategy)["line_id"] == "sales-content" else "native",
            "method_notes": [],
        },
        "script_candidates": [],
        "selected_script": None,
        "image_suites": [],
        "current_artifact": None,
        "status": "SCRIPTING",
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = initialize(json.loads(args.strategy.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["run_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
