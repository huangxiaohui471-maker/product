#!/usr/bin/env python3
"""Dependency-free validator for phase-1 versioned handoff contracts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import read_json

REQUIRED: dict[str, dict[str, type]] = {
    "creative_evidence/v1": {"creative_id":str,"platform":str,"media":dict,"evidence_class":str,"paid_evidence":dict,"organic_metrics":dict,"paid_metrics":dict,"estimated_metrics":dict},
    "creative_analysis/v1": {"creative_id":str,"route":str,"observations":dict,"interpretations":dict,"confidence":dict,"evidence_refs":list,"degradations":list},
    "strategy_cluster/v1": {"cluster_id":str,"label":str,"member_creative_ids":list,"cluster_version":str},
    "experiment_task/v1": {"experiment_id":str,"enterprise_context_id":str,"evidence_creative_ids":list,"hypothesis":str,"single_variable":dict,"constants":list,"claim_boundaries":list},
    "decision_event/v1": {"event_id":str,"experiment_id":str,"decision":str,"decided_by":str,"decided_at":str},
    "feedback_event/v1": {"feedback_id":str,"experiment_id":str,"event_type":str,"occurred_at":str,"source":str,"metrics":dict},
    "performance_result/v1": {"result_id":str,"experiment_id":str,"observed_at":str,"source":str,"metrics":dict,"measurement_window":dict},
    "run_manifest/v1": {"run_id":str,"status":str,"started_at":str,"errors":list},
    "ad_intelligence_batch/v1": {"provider":str,"source_receipt":dict,"evidence_policy":str,"candidates":list,"status":str},
    "ad_intelligence_candidate/v1": {"provider":str,"provider_record_id":str,"creative_id":str,"platform":str,"paid_evidence":dict,"organic_metrics":dict,"paid_metrics":dict,"estimated_metrics":dict},
    "daily_run/v1": {"daily_run_id":str,"started_at":str,"source_batch":str,"selected":list,"runs":list,"errors":list,"status":str},
    "enterprise_context/v1":{"context_id":str,"name":str,"industry":str,"business_goal":str,"current_priority":str,"target_customer":str,"products":list,"claim_boundaries":list,"production_capabilities":list},
    "watch_universe/v1":{"seed_accounts":list,"keywords":list,"excluded_accounts":list},
    "industry_pack/v1":{"industry":str,"purchase_chain":str,"proof_rule":str},
    "platform_pack/v1":{"platforms":list,"available_signals":list,"paid_truth_rule":str},
    "task_run_pack/v1":{"timezone":str,"max_candidates":int,"output":str,"failure_policy":str},
    "cost_policy/v1":{"mode":str,"daily_budget_usd":(int,float),"max_search_per_day":int,"max_detail_per_day":int,"max_downloads_per_run":int},
    "model_review/v2":{"reviewer_type":str},
    "mechanism_cluster/v1":{"cluster_id":str,"label":str,"member_creative_ids":list,"cluster_version":str,"reviewed":bool},
}

DEF_NAMES={version:version.replace("/","_") for version in REQUIRED}

def validate_schema_node(value:Any,schema:dict[str,Any],root:dict[str,Any],where:str="$")->list[str]:
    if "$ref" in schema:
        name=schema["$ref"].split("/")[-1];schema=(root.get("$defs") or {}).get(name,{})
    errors=[];kind=schema.get("type")
    type_map={"object":dict,"array":list,"string":str,"boolean":bool,"integer":int,"number":(int,float)}
    if kind in type_map and (not isinstance(value,type_map[kind]) or kind in {"integer","number"} and isinstance(value,bool)):
        return [f"{where}:type:{kind}"]
    if "const" in schema and value!=schema["const"]:errors.append(f"{where}:const")
    if "enum" in schema and value not in schema["enum"]:errors.append(f"{where}:enum")
    if isinstance(value,str):
        if len(value)<int(schema.get("minLength",0)):errors.append(f"{where}:minLength")
        if schema.get("pattern") and not re.search(schema["pattern"],value):errors.append(f"{where}:pattern")
    if isinstance(value,list):
        if len(value)<int(schema.get("minItems",0)):errors.append(f"{where}:minItems")
        if "maxItems" in schema and len(value)>int(schema["maxItems"]):errors.append(f"{where}:maxItems")
        if schema.get("items"):
            for index,item in enumerate(value):errors+=validate_schema_node(item,schema["items"],root,f"{where}[{index}]")
    if isinstance(value,dict):
        for key in schema.get("required",[]):
            if key not in value:errors.append(f"{where}:missing:{key}")
        for key,node in schema.get("properties",{}).items():
            if key in value:errors+=validate_schema_node(value[key],node,root,f"{where}.{key}")
    return errors

def validate_draft202012(payload:dict[str,Any],schema_path:Path|None=None)->list[str]:
    schema_path=schema_path or Path(__file__).resolve().parent.parent/"schemas/phase1-contracts.schema.json"
    bundle=read_json(schema_path,{})
    name=DEF_NAMES.get(str(payload.get("schema_version")))
    node=(bundle.get("$defs") or {}).get(name or "")
    return [f"unsupported schema_version: {payload.get('schema_version')!r}"] if not node else validate_schema_node(payload,node,bundle)


def validate(payload: dict[str, Any]) -> list[str]:
    version=payload.get("schema_version")
    if version not in REQUIRED: return [f"unsupported schema_version: {version!r}"]
    errors=[]
    for key, expected in REQUIRED[version].items():
        if key not in payload: errors.append(f"missing:{key}")
        elif not isinstance(payload[key],expected): errors.append(f"type:{key}:expected {expected.__name__}")
    if version=="decision_event/v1" and payload.get("decision") not in {"adopt","hold","reject"}: errors.append("enum:decision")
    if version=="run_manifest/v1" and payload.get("status") not in {"running","succeeded","failed"}: errors.append("enum:status")
    if version=="creative_evidence/v1":
        overlap=set(payload.get("paid_metrics",{})) & set(payload.get("estimated_metrics",{}))
        if overlap: errors.append("metric_partition_overlap:"+",".join(sorted(overlap)))
        if payload.get("evidence_class") not in {"verified_paid_platform_library","verified_paid_owned_account","authorized_top_ad","third_party_ad_library","commercial_like_proxy","public_content_only","user_supplied_unverified"}:errors.append("enum:evidence_class")
        if (payload.get("paid_evidence") or {}).get("level") not in {"verified_paid","strong_signal","weak_signal","unknown"}:errors.append("enum:paid_evidence.level")
        media=payload.get("media") or {}
        if not media.get("local_path") or not media.get("sha256"):errors.append("nested:media.local_path/sha256")
    if version=="creative_analysis/v1":
        if payload.get("route") not in {"native_video","scene_fusion","fixed_frame_fallback"}:errors.append("enum:route")
        if not payload.get("creative_id") or not payload.get("evidence_refs"):errors.append("empty:creative_id/evidence_refs")
    if version=="experiment_task/v1":
        for key in ("experiment_id","enterprise_context_id","hypothesis"):
            if not str(payload.get(key) or "").strip():errors.append(f"empty:{key}")
        variable=payload.get("single_variable") or {}
        if not all(str(variable.get(key) or "").strip() for key in ("name","from","to")):errors.append("nested:single_variable")
        if not payload.get("evidence_creative_ids"):errors.append("empty:evidence_creative_ids")
        if payload.get("adoptable") and payload.get("hold_reasons"):errors.append("invariant:adoptable_with_hold_reasons")
    if version=="daily_run/v1" and payload.get("status")=="failed" and payload.get("current_stage")=="DASHBOARD_READY":errors.append("invariant:failed_dashboard_ready")
    return errors


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("path");args=parser.parse_args()
    path=Path(args.path);payload=read_json(path,{});errors=validate(payload)+validate_draft202012(payload)
    print(json.dumps({"path":str(path),"valid":not errors,"errors":errors},ensure_ascii=False,indent=2))
    raise SystemExit(1 if errors else 0)
