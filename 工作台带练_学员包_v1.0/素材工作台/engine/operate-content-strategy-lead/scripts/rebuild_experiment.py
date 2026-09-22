#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json,read_json,now
from strategy_engine import propose
from render_dashboard import render
from clustering import cluster_tasks,cluster_analyses
from memory_store import MemoryStore
from validate_contract import validate as validate_contract

def rebuild(workspace:Path,run_dir:Path)->dict:
    evidence=read_json(run_dir/"creative/evidence.json",{});analysis=read_json(run_dir/"analysis/analysis.json",{});context=read_json(workspace/"config/enterprise_context.json",{});old=read_json(run_dir/"experiment.json",{})
    task=propose(evidence,analysis,context);review=analysis.get("model_review") or {};review_decision=review.get("decision","pending");reasons=[]
    if review_decision not in {"adopt","hold","reject","pending"}:raise ValueError("model_review.decision 非法")
    # Once a validated multimodal review exists, its explicit fit score supersedes
    # the cheap lexical pre-filter. The lexical score remains useful before review.
    review_fit=review.get("context_fit") or {};human_fit=review_fit.get("score_0_to_1") if isinstance(review_fit,dict) else None
    if human_fit is not None:
        score=task.get("scorecard") or {};score["context_fit"]=round(float(human_fit),3)
        score["reference_score"]=round(.35*float(score.get("evidence_strength") or 0)+.25*float(score.get("analysis_completeness") or 0)+.4*float(human_fit),3)
        task["scorecard"]=score;task["context_fit_reason"]="已由多模态证据复核校准，人工上下文匹配度为 %.2f。"%float(human_fit)
        task["why_now"]=f"复核后候选参考分 {score['reference_score']}；最终是否投放仍由企业证据、路径和实验结果决定。"
    memory=MemoryStore(workspace)
    if memory.is_mechanism_suppressed(task.get("borrow_mechanism","")):reasons.append("这个说服机制已采用或仍在冷却期，今天不重复解释")
    whitebox=analysis.get("whitebox_analysis") or {};reconstruction=whitebox.get("reconstruction") or {}
    recommendation=review.get("recommendation") or {}
    review_variable=recommendation.get("single_variable") if isinstance(recommendation,dict) else None
    if isinstance(review_variable,dict) and all(str(review_variable.get(key) or "").strip() for key in ("name","from","to")):
        task["single_variable"]={key:str(review_variable[key]).strip() for key in ("name","from","to")}
        task["hypothesis"]=str(recommendation.get("hypothesis") or f"只把“{task['single_variable']['from']}”换成“{task['single_variable']['to']}”，其余要约、证据和投放条件保持不变。")
    task["production_handoff"]={"schema_version":"creative_production_brief/v1","goal":reconstruction.get("goal"),"shots":reconstruction.get("shots") or [],"owner_questions":reconstruction.get("owner_questions") or whitebox.get("open_questions") or [],"claim_checks":whitebox.get("claims_to_check") or [],"status":"ready_for_future_module" if reconstruction else "incomplete"}
    task["required_assets"]=[row.get("visual") for row in reconstruction.get("shots") or [] if row.get("visual")]
    if not old.get("is_new_creative",True):reasons.append("重复素材：已在历史记忆中处理")
    reviewed_at=now()
    interp=analysis.get("interpretations") or {}
    content_ready=bool(interp.get("opening_hook") and interp.get("customer_tension") and interp.get("proof_devices") and review_decision!="pending")
    recommendation_state={"adopt":"recommended","hold":"observe","reject":"excluded","pending":"processing"}[review_decision]
    task.update({"is_new_creative":old.get("is_new_creative",True),"is_evidence_enrichment":old.get("is_evidence_enrichment",False),"visible_in_dashboard":old.get("visible_in_dashboard",True),"source_media_sha256":(evidence.get("media") or {}).get("sha256"),"evidence_links":old.get("evidence_links",{}),"review_gate":review,"reviewed_at":reviewed_at,"needs_strategy_review":not content_ready,"content_ready":content_ready,"recommendation_state":recommendation_state,"adoptable":recommendation_state=="recommended","hold_reasons":[]})
    contract_errors=validate_contract(task)
    if contract_errors: raise ValueError("契约门未通过："+"；".join(contract_errors))
    atomic_write_json(run_dir/"experiment.json",task)
    tasks=[];analyses=[]
    for path in (workspace/"runs").glob("*/experiment.json"):
        try:tasks.append(read_json(path,{}))
        except Exception:pass
    for path in (workspace/"runs").glob("*/analysis/analysis.json"):
        try:analyses.append(read_json(path,{}))
        except Exception:pass
    strategy_clusters=cluster_tasks(tasks);mechanism_clusters=cluster_analyses(analyses)
    atomic_write_json(run_dir/"clusters.json",strategy_clusters)
    atomic_write_json(run_dir/"mechanism_clusters.json",mechanism_clusters)
    # Trend attribution uses only the current run's reviewed mechanism; the
    # workspace-wide clusters remain a dashboard index, not a current-run fact.
    current_mechanisms=cluster_analyses([analysis])
    if review.get("schema_version")=="model_review/v2":memory.record_patterns(current_mechanisms or cluster_tasks([task]),run_dir.name)
    manifest=read_json(run_dir/"run_manifest.json",{})
    if manifest:
        manifest.setdefault("artifacts",{})["mechanism_clusters"]="mechanism_clusters.json"
        manifest["strategy_ready"]=True;manifest["strategy_ready_at"]=reviewed_at;atomic_write_json(run_dir/"run_manifest.json",manifest)
    render(workspace,workspace/"dashboard.html");return task
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--run",required=True);a=p.parse_args();print(rebuild(Path(a.workspace),Path(a.run))["decision"])
