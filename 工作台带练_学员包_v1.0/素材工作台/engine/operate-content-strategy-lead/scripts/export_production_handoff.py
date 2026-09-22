#!/usr/bin/env python3
"""Export an adopted strategy experiment as the cross-role production brief."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def export_handoff(experiment: dict, shared_context: dict, direction: dict) -> dict:
    if shared_context.get("schema_version") != "shared_enterprise_context/v1":
        raise ValueError("需要已确认的企业人货场白皮书")
    variable = experiment.get("single_variable") or {}
    if not variable.get("name") or variable.get("from") == variable.get("to"):
        raise ValueError("这次还没有形成真正的单变量实验")
    production = experiment.get("production_handoff") or {}
    boundaries = list(dict.fromkeys((experiment.get("claim_boundaries") or []) + (experiment.get("do_not_copy") or [])))
    if not boundaries:
        boundaries = ["不要照抄同行品牌、价格和承诺，换成企业自己的真实内容"]
    evidence_ids = experiment.get("evidence_creative_ids") or []
    evidence = []
    for item in production.get("claim_checks") or []:
        evidence.append({
            "statement": item.get("what_we_can_confirm") or item.get("source_says") or "待门店确认",
            "source_ref": evidence_ids[0] if evidence_ids else "owner-confirmation-pending",
            "needed_before_use": item.get("needed_before_use"),
        })
    if not evidence:
        evidence = [{"statement": str(x), "source_ref": evidence_ids[0] if evidence_ids else "owner-confirmation-pending"} for x in (experiment.get("required_assets") or ["待确认可用证据"])]
    result = {
        "schema_version": "strategy_to_production/v1",
        "task_id": direction.get("task_id") or experiment.get("experiment_id"),
        "cycle_id": direction.get("cycle_id") or f"cycle-{datetime.now().date().isoformat()}",
        "context_id": shared_context["context_id"],
        "version": int(direction.get("version") or 1),
        "created_at": datetime.now().astimezone().isoformat(),
        "opportunity": {"statement": experiment.get("borrow_mechanism") or experiment.get("hypothesis") or "待确认机会", "why_now": experiment.get("why_now") or "本轮已由负责人确认值得测试"},
        "target_audience": direction.get("target_audience") or experiment.get("target_customer") or "待确认目标对象",
        "customer_scene": direction.get("customer_scene") or experiment.get("customer_situation") or "待确认客户场景",
        "belief_change": direction.get("belief_change") or "待确认希望改变的想法",
        "desired_action": direction.get("desired_action") or "待确认希望客户前进的一步",
        "usable_evidence": evidence,
        "single_variable": variable,
        "held_conditions": experiment.get("constants") or [],
        "touch_destination": direction.get("touch_destination") or {"channel": "unknown", "position": "unknown", "owner": "unknown"},
        "expression_boundaries": boundaries,
        "completion_gate": direction.get("completion_gate") or ["形成可用内容版本", "保持当前方向", "记录使用位置"],
        "material_refs": list(dict.fromkeys(evidence_ids)),
        "source_refs": [shared_context["context_id"], *evidence_ids],
        "status": "ready_for_production",
    }
    required = ("task_id", "cycle_id", "context_id", "target_audience", "customer_scene", "belief_change", "desired_action")
    missing = [key for key in required if not result.get(key)]
    if missing: raise ValueError("交接包缺少：" + "、".join(missing))
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--experiment", type=Path, required=True); p.add_argument("--context", type=Path, required=True)
    p.add_argument("--direction", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = export_handoff(json.loads(a.experiment.read_text(encoding="utf-8")), json.loads(a.context.read_text(encoding="utf-8")), json.loads(a.direction.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(a.output); return 0


if __name__ == "__main__": raise SystemExit(main())
