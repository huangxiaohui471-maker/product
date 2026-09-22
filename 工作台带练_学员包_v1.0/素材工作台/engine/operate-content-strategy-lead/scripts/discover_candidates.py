#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json, now, read_json, stable_id
from tikhub_adapter import search_douyin
from cost_ledger import CostLedger
from watch_discovery import update_from_candidates

def discover(workspace:Path,days:int=7,limit:int=20)->Path:
    watch=read_json(workspace/"config/watch_universe.json",{})
    keywords=[str(k).strip() for k in watch.get("keywords",[]) if str(k).strip()]
    # Auto-promoted counterpart names become low-cost search seeds on the next run.
    keywords.extend(str(name).strip() for name in watch.get("seed_accounts",[])[:5] if isinstance(name,str) and str(name).strip())
    keywords=list(dict.fromkeys(keywords))
    if not keywords: raise ValueError("watch_universe.keywords 为空；先由 Skill 与用户确定观察关键词")
    if len(keywords)>20:raise ValueError("运行闸门：单轮最多 20 个关键词，超出请拆批")
    ledger=CostLedger(workspace)
    policy=ledger.policy()
    rows=[];errors=[]
    for keyword in keywords:
        try:
            ledger.guard("search",max_daily=int(policy.get("max_search_per_day",50)),projected_cost=.001,daily_budget=float(policy.get("daily_budget_usd",1.5)))
            for row in search_douyin(keyword,days,limit):
                flags=row.get("search_flags") or {};row["query_keyword"]=keyword
                row["matched_keywords"]=[keyword]
                row["paid_evidence"]={"level":"weak_signal" if any(flags.values()) else "unknown",
                    "sources":[key for key,value in flags.items() if value]}
                row["evidence_class"]="public_content_only"
                row["organic_metrics"]=dict(row.get("search_metrics") or {})
                rows.append(row)
            ledger.record("search",.001,keyword)
        except Exception as error: errors.append({"keyword":keyword,"type":type(error).__name__,"message":str(error)[:300]})
    unique={}
    for row in rows:
        prior=unique.get(row["creative_id"])
        if prior:
            prior["matched_keywords"]=list(dict.fromkeys((prior.get("matched_keywords") or [])+(row.get("matched_keywords") or [])))
        else: unique[row["creative_id"]]=row
    stamp=now().replace(":","-")
    out=workspace/"runs"/f"discovery-{stamp}"/"candidates.json"
    payload={"schema_version":"candidate_batch/v1","batch_id":stable_id(stamp,*keywords)[:24],"created_at":now(),
        "connector":"tikhub/douyin-index","keywords":keywords,"candidates":list(unique.values()),"errors":errors,
        "cost":{"requests":len(keywords),"known_unit_cost_usd":0.001,"known_cost_usd":round(len(keywords)*0.001,6)},
        "status":"succeeded" if unique and not errors else "partial" if unique else "failed"}
    atomic_write_json(out,payload)
    if unique:update_from_candidates(workspace,list(unique.values()))
    if not unique: raise RuntimeError(f"没有取得候选素材；连接器错误已保存到 {out}")
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--days",type=int,default=7);p.add_argument("--limit",type=int,default=20);a=p.parse_args();print(discover(Path(a.workspace),a.days,a.limit))
