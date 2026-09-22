#!/usr/bin/env python3
"""One backstage entry for daily discovery/import, selection, evidence processing and review queue creation."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from common import atomic_write_json, now, read_json, stable_id
from context import validate_context
from discover_candidates import discover
from render_dashboard import render
from run_ad_intel_candidate import run_candidate as run_ad_candidate
from run_tikhub_candidate import run_candidate as run_public_candidate
from validate_contract import validate as validate_contract
from memory_store import EVIDENCE_RANK, MemoryStore


COMMERCIAL_CUES=("团购","套餐","优惠","到店","门店","新品","上市","报名","咨询","课程","领取","下单","购买","加盟","品牌","测评","推荐","限时","价格","元")
GENERIC_TERMS={"ai","内容","内容营销","营销","视频","课程","培训","落地","推荐"}

def _bigrams(value:str)->set[str]:
    clean="".join(ch.lower() for ch in value if ch.isalnum())
    return {clean[i:i+2] for i in range(max(0,len(clean)-1))}

def _business_fit(candidate:dict[str,Any],context:dict[str,Any],watch:dict[str,Any])->float:
    """Estimate business relevance before heat without hard-coding an industry."""
    source=" ".join(str(candidate.get(key) or "") for key in ("title","description","author_name"))
    target=" ".join([str(context.get("target_customer") or ""),str(context.get("business_goal") or ""),str(context.get("current_priority") or ""),*map(str,context.get("products") or [])])
    a,b=_bigrams(source),_bigrams(target)
    semantic=len(a&b)/max(1,min(len(a),len(b))) if a and b else 0.0
    phrases=[]
    for value in list(context.get("products") or [])+list(watch.get("keywords") or []):
        text=str(value).strip().lower()
        if len(text)>=2 and text not in GENERIC_TERMS:phrases.append(text)
    exact=min(sum(1 for term in set(phrases) if term in source.lower())/2,1.0)
    return round(max(semantic,exact),4)

def _frontstage_reason(candidate:dict[str,Any],context:dict[str,Any],watch:dict[str,Any])->str:
    """Explain why a candidate entered today's shortlist without exposing scoring internals."""
    title=str(candidate.get("title") or "")
    terms=[]
    for value in list(context.get("products") or [])+list(watch.get("keywords") or []):
        terms.extend(token for token in str(value).replace("，"," ").split() if len(token)>=2)
    matched=[term for term in dict.fromkeys(terms) if term in title]
    cues=[cue for cue in COMMERCIAL_CUES if cue in title]
    flags=[key for key,value in (candidate.get("search_flags") or {}).items() if value]
    if matched and cues:return f"同时命中你的业务词“{matched[0]}”和成交表达“{cues[0]}”"
    if matched:return f"直接命中你的业务词“{matched[0]}”"
    if cues:return f"出现明确成交表达“{cues[0]}”，值得先看结构"
    if flags:return "带有平台可见的推广倾向，先进入候选观察"
    return "与当前观察范围相关，先保留到今日候选"

def _shortlist_snapshot(ranked:list[dict[str,Any]],context:dict[str,Any],watch:dict[str,Any],limit:int=8)->list[dict[str,Any]]:
    rows=[]
    for index,candidate in enumerate(ranked[:max(1,min(limit,8))],1):
        metrics=candidate.get("organic_metrics") or candidate.get("search_metrics") or {}
        rows.append({"rank":index,"creative_id":candidate.get("creative_id"),"title":candidate.get("title"),
            "platform":candidate.get("platform") or "douyin","author_name":candidate.get("author_name"),
            "canonical_url":candidate.get("canonical_url"),"reason":_frontstage_reason(candidate,context,watch),
            "visible_signal":{"likes":metrics.get("likes") or metrics.get("digg_count"),"comments":metrics.get("comments") or metrics.get("comment_count")},
            "status":"待深拆"})
    return rows

def _score(candidate: dict[str, Any], context: dict[str, Any] | None=None, watch: dict[str, Any] | None=None) -> float:
    flags=candidate.get("search_flags") or {}
    metrics=candidate.get("organic_metrics") or candidate.get("search_metrics") or {}
    estimated=candidate.get("estimated_metrics") or {}
    score=sum(1 for value in flags.values() if value)*20
    for key,weight in (("likes",.0001),("digg_count",.0001),("fans",.00001)):
        try: score += min(float(metrics.get(key) or 0)*weight,10)
        except (TypeError,ValueError): pass
    score += min(len(estimated)*2,8)
    if candidate.get("media_url"): score += 5
    if candidate.get("canonical_url"): score += 2
    title=str(candidate.get("title") or "")
    cue_hits=sum(1 for cue in COMMERCIAL_CUES if cue in title);score+=min(cue_hits*6,24)
    heat=estimated.get("heat_index") or estimated.get("supplier_score")
    try: score+=min(max(math.log10(float(heat)+1)-3,0)*2,6)
    except (TypeError,ValueError):pass
    context=context or {};industry=context.get("industry");category=candidate.get("category")
    preferred={"education":{"education":12},"local_life":{"food":10,"life":4},"ecommerce":{"life":6,"food":3}}.get(industry,{})
    score+=preferred.get(category,0)
    watch=watch or {};terms=[]
    for value in list(context.get("products") or [])+list(watch.get("keywords") or []):
        terms.extend(token for token in str(value).replace("，"," ").split() if len(token)>=2)
    score+=min(sum(1 for term in set(terms) if term in title)*5,20)
    fit=_business_fit(candidate,context,watch)
    # Business relevance dominates popularity. Heat only orders candidates
    # that are similarly useful to the current enterprise.
    return round(fit*100+score,4)

def _has_pending_review(workspace:Path)->bool:
    for path in (workspace/"runs").glob("*/experiment.json"):
        if not read_json(path,{}).get("needs_strategy_review"):continue
        manifest=read_json(path.parent/"run_manifest.json",{})
        if manifest.get("status")=="succeeded" and manifest.get("current_stage") not in {"DONE","FAILED_PERMANENT"}:return True
    return False


def run_daily(workspace: Path, batch_path: Path | None, discover_public: bool, top: int, analysis: str) -> Path:
    context=read_json(workspace/"config/enterprise_context.json",{});watch=read_json(workspace/"config/watch_universe.json",{})
    errors=validate_context(context)
    if errors: raise ValueError("企业上下文未通过装配门："+"；".join(errors))
    if discover_public:
        batch_path=discover(workspace)
    if not batch_path: raise ValueError("必须选择 --discover-public 或提供 --batch")
    batch=read_json(batch_path,{})
    candidates=batch.get("candidates") or []
    if not candidates: raise ValueError("候选批次为空")
    context_limit=int(context.get("authorization_scope",{}).get("max_downloads_per_run",5));cost_limit=int(read_json(workspace/"config/cost_policy.json",{}).get("max_downloads_per_run",20))
    limit=min(max(1,top),context_limit,cost_limit)
    ranked=sorted(candidates,key=lambda row:(-_business_fit(row,context,watch),-_score(row,context,watch),str(row.get("creative_id"))))
    receipt={"schema_version":"daily_run/v1","daily_run_id":stable_id(now(),str(batch_path))[:24],"started_at":now(),
             "source_batch":str(batch_path),"selected":[],"skipped":[],"runs":[],"errors":[],"status":"running",
             "current_stage":"DISCOVERING","stage_history":[{"at":now(),"stage":"DISCOVERING"}],
             "candidate_funnel":{"discovered":len(candidates),"shortlisted":min(len(ranked),8),"already_seen":0,"deep_reviewed":0,"failed":0},
             "shortlist":_shortlist_snapshot(ranked,context,watch)}
    out=workspace/"runs"/("daily-"+receipt["daily_run_id"])/"daily_run.json"
    atomic_write_json(out,receipt)
    memory=MemoryStore(workspace);seen=memory.seen_index();suppressed=memory.suppressed_creative_ids()
    receipt["current_stage"]="COLLECTING";receipt["stage_history"].append({"at":now(),"stage":"COLLECTING"})
    # Refill failed slots, but never let a sick supplier turn one daily run into an
    # unbounded crawl.  Three attempts per requested success is enough to expose
    # a partial outage and still leaves the receipt in a truthful terminal state.
    max_attempts=min(len(ranked),max(limit*3,limit+2));attempts=0
    for candidate in ranked:
        if len(receipt["runs"])>=limit or attempts>=max_attempts: break
        creative_id=candidate.get("creative_id")
        prior=seen.get(creative_id)
        candidate_rank=EVIDENCE_RANK.get(candidate.get("evidence_class"),0)
        prior_rank=EVIDENCE_RANK.get((prior or {}).get("evidence_class"),-1)
        is_upgrade=bool(prior and candidate_rank>prior_rank)
        if (creative_id in suppressed and not is_upgrade) or (prior and not is_upgrade):
            receipt["skipped"].append({"creative_id":creative_id,"reason":"记忆已处理/冷却，采集前跳过","prior_evidence_class":(prior or {}).get("evidence_class")})
            for row in receipt["shortlist"]:
                if row.get("creative_id")==creative_id:row["status"]="历史已看，已排重"
            continue
        receipt["selected"].append({"creative_id":candidate.get("creative_id"),"selection_score":_score(candidate,context,watch)})
        attempts+=1
        try:
            if candidate.get("schema_version")=="ad_intelligence_candidate/v1":
                enriched={**candidate,"_source_batch_path":str(batch_path.resolve()),"_source_receipt":batch.get("source_receipt")}
                run_path=run_ad_candidate(workspace,enriched,analysis)
            else:
                run_path=run_public_candidate(workspace,candidate,analysis)
            experiment=read_json(run_path/"experiment.json",{})
            receipt["runs"].append({"creative_id":candidate.get("creative_id"),"run_path":str(run_path),
                "experiment_id":experiment.get("experiment_id"),"needs_agent_review":bool(experiment.get("needs_strategy_review"))})
            for row in receipt["shortlist"]:
                if row.get("creative_id")==creative_id:row["status"]="已进入深拆"
        except Exception as error:
            receipt["errors"].append({"creative_id":candidate.get("creative_id"),"type":type(error).__name__,"message":str(error)[:300]})
            for row in receipt["shortlist"]:
                if row.get("creative_id")==creative_id:row["status"]="本次读取失败"
        atomic_write_json(out,receipt)
    render_failed=False
    try:render(workspace,workspace/"dashboard.html")
    except Exception as error:
        render_failed=True
        receipt["errors"].append({"type":"DashboardRenderError","message":str(error)[:300]})
    receipt["status"]="succeeded" if (receipt["runs"] or receipt["skipped"]) and not receipt["errors"] else "partial" if receipt["runs"] or receipt["skipped"] else "failed"
    receipt["finished_at"]=now()
    receipt["candidate_funnel"].update({"already_seen":len(receipt["skipped"]),"deep_reviewed":len(receipt["runs"]),"failed":len(receipt["errors"])})
    receipt["current_stage"]="FAILED_PERMANENT" if render_failed else (("WAIT_REVIEW" if any(row.get("needs_agent_review") for row in receipt["runs"]) or _has_pending_review(workspace) else "DASHBOARD_READY") if receipt["runs"] or receipt["skipped"] else "FAILED_PERMANENT")
    receipt["stage_history"].append({"at":receipt["finished_at"],"stage":receipt["current_stage"]})
    contract_errors=validate_contract(receipt)
    if contract_errors:
        receipt["status"]="failed";receipt["errors"].append({"type":"ContractError","message":"；".join(contract_errors)})
    atomic_write_json(out,receipt)
    return out


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",required=True)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--discover-public",action="store_true")
    source.add_argument("--batch")
    parser.add_argument("--top",type=int,default=3)
    parser.add_argument("--analysis",choices=["auto","local","gemini"],default="local")
    args=parser.parse_args()
    print(run_daily(Path(args.workspace),Path(args.batch) if args.batch else None,args.discover_public,args.top,args.analysis))
