#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from common import atomic_write_json,read_json,sha256_file
from run_pipeline import run
from tikhub_adapter import detail_by_url,media_urls
from cost_ledger import CostLedger

def run_candidate(workspace:Path,candidate:dict,analysis_route:str="local")->Path:
    ledger=CostLedger(workspace);policy=ledger.policy();ledger.guard("detail",max_daily=int(policy.get("max_detail_per_day",100)),projected_cost=.001,daily_budget=float(policy.get("daily_budget_usd",1.5)))
    evidence,raw=detail_by_url(candidate["canonical_url"]);urls=media_urls(raw)
    ledger.record("detail",.001,candidate["creative_id"])
    if not urls:raise RuntimeError("详情成功但没有可下载视频地址")
    evidence["paid_evidence"]=candidate.get("paid_evidence") or {"level":"unknown","sources":[]}
    evidence["title"]=evidence.get("title") or candidate.get("title") or ""
    if not (evidence.get("author") or {}).get("display_name") and candidate.get("author_name"):
        evidence["author"]={**(evidence.get("author") or {}),"display_name":candidate.get("author_name")}
    evidence["evidence_class"]=candidate.get("evidence_class") or "public_content_only"
    evidence["organic_metrics"]=dict(evidence.get("metrics") or {})
    evidence["paid_metrics"]={};evidence["estimated_metrics"]=dict(candidate.get("estimated_metrics") or {})
    receipt={"schema_version":"source_receipt/v1","connector":"tikhub","creative_id":evidence["creative_id"],
        "canonical_url":evidence["canonical_url"],"published_at":evidence.get("published_at"),"metrics":evidence.get("metrics"),
        "paid_evidence":evidence["paid_evidence"],"evidence_class":evidence["evidence_class"],"estimated_metrics":evidence["estimated_metrics"],
        "upstream_provenance":candidate.get("provenance"),"privacy":"author identity and media URLs omitted"}
    staging=workspace/"logs/tikhub_receipts";staging.mkdir(parents=True,exist_ok=True);receipt_path=staging/f"{evidence['creative_id'].replace(':','_')}.json";atomic_write_json(receipt_path,receipt)
    evidence["source_snapshot_path"]=str(receipt_path);evidence["provenance"]={**evidence["provenance"],"receipt_sha256":sha256_file(receipt_path)}
    failures=[];out=None
    for media_url in urls[:4]:
        try:out=run(workspace,media_url,analysis_route,evidence);break
        except Exception as error:failures.append(type(error).__name__)
    if out is None:raise RuntimeError(f"所有候选媒体地址均下载失败: {failures}")
    manifest=read_json(out/"run_manifest.json",{});manifest["cost"]={"external_calls":1,"known_unit_cost_usd":0.001,"known_cost_usd":0.001,"notes":"TikHub detail call; media download and YouNavi billing not measured here"};atomic_write_json(out/"run_manifest.json",manifest)
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--batch",required=True);p.add_argument("--index",type=int,default=0);p.add_argument("--analysis",choices=["auto","local","gemini"],default="local");a=p.parse_args()
    batch=read_json(Path(a.batch),{});candidates=batch.get("candidates") or []
    if not 0<=a.index<len(candidates):raise SystemExit("候选索引超出范围")
    print(run_candidate(Path(a.workspace),candidates[a.index],a.analysis))
