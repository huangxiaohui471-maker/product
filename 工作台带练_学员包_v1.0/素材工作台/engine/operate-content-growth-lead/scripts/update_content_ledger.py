#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path

METRIC_GROUPS=("public_metrics","internal_metrics","business_results")

def update(existing:dict, batch:dict)->dict:
    ledger=existing or {"schema_version":"content_ledger/v1","ledger_id":batch.get("ledger_id") or "enterprise-content-ledger","items":[],"updated_at":None}
    by_key={(x["channel"],x["content_id"]):x for x in ledger.get("items") or []}
    for raw in batch.get("items") or []:
        if not raw.get("channel") or not raw.get("content_id") or not raw.get("source_refs"): raise ValueError("每条作品需要渠道、作品编号和来源")
        key=(raw["channel"],raw["content_id"]); old=by_key.get(key,{})
        snapshots=list(old.get("snapshots") or [])
        snap={"observed_at":raw.get("observed_at") or datetime.now().astimezone().isoformat(),"data_through":raw.get("data_through"),"public_metrics":raw.get("public_metrics") or {},"internal_metrics":raw.get("internal_metrics") or {},"business_results":raw.get("business_results") or {},"missing_fields":raw.get("missing_fields") or [],"source_refs":raw["source_refs"]}
        if not snapshots or snapshots[-1] != snap:snapshots.append(snap)
        by_key[key]={"channel":raw["channel"],"content_id":raw["content_id"],"title":raw.get("title") or old.get("title") or "未命名内容","published_at":raw.get("published_at") or old.get("published_at"),"content_locator":raw.get("content_locator") or old.get("content_locator"),"production_ref":raw.get("production_ref") or old.get("production_ref"),"production_line":raw.get("production_line") or old.get("production_line"),"production_recipe":raw.get("production_recipe") or old.get("production_recipe"),"artifact_id":raw.get("artifact_id") or old.get("artifact_id"),"version_id":raw.get("version_id") or old.get("version_id"),"topic":raw.get("topic") or old.get("topic"),"format":raw.get("format") or old.get("format"),"snapshots":snapshots}
    ledger["items"]=sorted(by_key.values(),key=lambda x:x.get("published_at") or "",reverse=True);ledger["updated_at"]=datetime.now().astimezone().isoformat();return ledger

def main():
    p=argparse.ArgumentParser();p.add_argument("batch",type=Path);p.add_argument("output",type=Path);p.add_argument("--existing",type=Path);a=p.parse_args()
    old=json.loads(a.existing.read_text(encoding="utf-8")) if a.existing else {};result=update(old,json.loads(a.batch.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(len(result["items"]));return 0
if __name__=="__main__":raise SystemExit(main())
