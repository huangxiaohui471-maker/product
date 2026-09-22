#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from common import append_jsonl, atomic_write_json, now, read_json, stable_id
from media_ingest import ingest
from analyze_media import analyze
from memory_store import MemoryStore
from strategy_engine import propose
from render_dashboard import render
from gemini_video import analyze as analyze_native
from context import validate_context
from clustering import cluster_tasks
from validate_contract import validate as validate_contract

def _stage(out: Path, stage: str, detail: dict | None = None) -> None:
    """Persist an auditable state transition; process exit alone is never completion."""
    event={"schema_version":"run_event/v1","at":now(),"stage":stage,"detail":detail or {}}
    append_jsonl(out/"events/state_transitions.jsonl",event)
    manifest=read_json(out/"run_manifest.json",{})
    manifest["current_stage"]=stage
    manifest.setdefault("stage_history",[]).append({"at":event["at"],"stage":stage})
    atomic_write_json(out/"run_manifest.json",manifest)

def _failure_stage(error: Exception) -> str:
    message=str(error).lower()
    if any(token in message for token in ("401","403","凭据","token","api key")):
        return "BLOCKED_CREDENTIAL"
    if any(token in message for token in ("402","余额","预算","cost","budget")):
        return "BLOCKED_COST"
    if isinstance(error,(ValueError,FileNotFoundError,PermissionError)):
        return "BLOCKED_INPUT"
    if any(token in message for token in ("429","timeout","timed out","5xx","tempor")):
        return "FAILED_RETRYABLE"
    return "FAILED_PERMANENT"

def _run(workspace: Path, source: str, analysis_route: str, run_id: str, evidence_seed: dict | None = None) -> Path:
    out=workspace/"runs"/run_id
    _stage(out,"WAIT_CONFIG")
    context=read_json(workspace/"config/enterprise_context.json",{})
    context_errors=validate_context(context)
    if context_errors: raise ValueError("企业上下文未通过装配门："+"；".join(context_errors))
    _stage(out,"READY")
    _stage(out,"COLLECTING")
    evidence=ingest(source,out/"creative")
    if evidence_seed:
        for key in ("creative_id","platform","canonical_url","author","published_at","metrics","organic_metrics","paid_metrics","estimated_metrics","paid_evidence","evidence_class","provenance","source_snapshot_path"):
            if key in evidence_seed:evidence[key]=evidence_seed[key]
        atomic_write_json(out/"creative/evidence.json",evidence)
    _stage(out,"UNDERSTANDING")
    evidence_errors=validate_contract(evidence)
    if evidence_errors: raise ValueError("契约门未通过 creative_evidence/v1："+"；".join(evidence_errors))
    memory=MemoryStore(workspace);matched_seen=memory.match_seen(evidence)
    is_new=matched_seen is None
    adapter=(evidence.get("provenance") or {}).get("adapter")
    rank={"user_supplied_unverified":0,"public_content_only":1,"commercial_like_proxy":2,"third_party_ad_library":3,"authorized_top_ad":4,"verified_paid_platform_library":5,"verified_paid_owned_account":6}
    is_enrichment=bool(matched_seen and (rank.get(evidence.get("evidence_class"),0)>rank.get(matched_seen.get("evidence_class"),-1) or (adapter not in (None,"manual") and matched_seen.get("adapter") in (None,"manual"))))
    local_analysis=analyze(out/"creative/evidence.json",out/"analysis")
    analysis=local_analysis
    has_key=bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if analysis_route == "gemini" or (analysis_route == "auto" and has_key):
        try:
            analysis=analyze_native(Path(evidence["media"]["local_path"]),evidence["creative_id"])
            analysis["evidence_refs_local"] = local_analysis["evidence_refs"]
            atomic_write_json(out/"analysis/analysis.json",analysis)
        except Exception as error:
            if analysis_route == "gemini": raise
            analysis["degradations"].append(f"native_video_failed:{type(error).__name__}")
            atomic_write_json(out/"analysis/analysis.json",analysis)
    if analysis.get("degradations"):
        _stage(out,"DEGRADED_UNDERSTANDING",{"reasons":analysis.get("degradations")})
    analysis_errors=validate_contract(analysis)
    if analysis_errors: raise ValueError("契约门未通过 creative_analysis/v1："+"；".join(analysis_errors))
    _stage(out,"CLUSTERING")
    _stage(out,"JUDGING")
    task=propose(evidence,analysis,context)
    interpretation_confidence=(analysis.get("confidence") or {}).get("interpretations", 1)
    hold_reasons=[]
    if interpretation_confidence == 0:
        hold_reasons.append("视觉策略理解尚未完成；请接入多模态模型或人工复核")
    if not is_new and not is_enrichment:
        hold_reasons.append("重复素材：已在历史记忆中处理，本轮不重复推荐")
    if memory.is_cooled(task["experiment_id"]): hold_reasons.append("记忆冷却期内")
    # Native model output is analysis evidence, not a final strategy judgment.
    # Only a source-bound model_review/v2 may later unlock adoption via rebuild.
    review=analysis.get("model_review") or {}
    if review.get("schema_version")!="model_review/v2" or review.get("decision")!="adopt":
        hold_reasons.append("详细拆解尚未完成：需经过可追溯的 V2 白盒复核")
    task["needs_strategy_review"]=review.get("schema_version")!="model_review/v2"
    task["adoptable"]=not hold_reasons
    task["hold_reasons"]=hold_reasons
    if hold_reasons:
        task["decision"]="hold"; task["decision_reason"]="；".join(hold_reasons)
    task["is_new_creative"]=is_new;task["is_evidence_enrichment"]=is_enrichment; task["visible_in_dashboard"]=is_new or is_enrichment
    task["source_media_sha256"]=(evidence.get("media") or {}).get("sha256")
    task["evidence_links"]={"analysis":str((out/"analysis/analysis.json").relative_to(workspace)),"source_video":str((out/"creative/source.mp4").relative_to(workspace)),"evidence":str((out/"creative/evidence.json").relative_to(workspace))}
    _stage(out,"PROPOSING")
    task_errors=validate_contract(task)
    if task_errors: raise ValueError("契约门未通过 experiment_task/v1："+"；".join(task_errors))
    atomic_write_json(out/"experiment.json",task)
    prior=[]
    for path in (workspace/"runs").glob("*/experiment.json"):
        try: prior.append(read_json(path,{}))
        except Exception: pass
    clusters=cluster_tasks(prior)
    cluster_errors=[f"{cluster.get('cluster_id')}:{error}" for cluster in clusters for error in validate_contract(cluster)]
    if cluster_errors: raise ValueError("契约门未通过 strategy_cluster/v1："+"；".join(cluster_errors))
    atomic_write_json(out/"clusters.json",clusters)
    render(workspace,workspace/"dashboard.html")
    _stage(out,"DASHBOARD_READY")
    _stage(out,"WAIT_DECISION")
    manifest=read_json(out/"run_manifest.json",{});manifest.update({"status":"succeeded","finished_at":now(),"artifacts":{"evidence":"creative/evidence.json","analysis":"analysis/analysis.json","clusters":"clusters.json","experiment":"experiment.json","dashboard":str(workspace/"dashboard.html")},"errors":[]})
    manifest_errors=validate_contract(manifest)
    if manifest_errors: raise ValueError("契约门未通过 run_manifest/v1："+"；".join(manifest_errors))
    atomic_write_json(out/"run_manifest.json",manifest)
    # Commit memory only after every durable artifact and dashboard completed.
    memory.commit_completed_run(evidence,run_id,{"run_id":run_id,"at":now(),"creative_id":evidence["creative_id"],"new":is_new,"experiment_id":task["experiment_id"]})
    return out

def run(workspace: Path, source: str, analysis_route: str = "auto", evidence_seed: dict | None = None) -> Path:
    run_id=datetime.now().astimezone().isoformat(timespec="microseconds").replace(":","-");out=workspace/"runs"/run_id;out.mkdir(parents=True,exist_ok=True)
    manifest={"schema_version":"run_manifest/v1","run_id":run_id,"status":"running","current_stage":"WAIT_CONFIG","stage_history":[],"started_at":now(),"finished_at":None,
        "context_path":"config/enterprise_context.json","analysis_route":analysis_route,"cost":{"external_calls":0,"known_cost_usd":0},"errors":[]}
    atomic_write_json(out/"run_manifest.json",manifest)
    try:return _run(workspace,source,analysis_route,run_id,evidence_seed)
    except Exception as error:
        failed_stage=_failure_stage(error)
        _stage(out,failed_stage,{"error_type":type(error).__name__})
        manifest=read_json(out/"run_manifest.json",manifest)
        manifest.update({"status":"failed","current_stage":failed_stage,"finished_at":now(),"errors":[{"type":type(error).__name__,"message":str(error)[:500]}]})
        atomic_write_json(out/"run_manifest.json",manifest);raise

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--source",required=True);p.add_argument("--analysis",choices=["auto","local","gemini"],default="auto");a=p.parse_args();print(run(Path(a.workspace),a.source,a.analysis))
