from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from common import atomic_write_json, now, read_json


def update_from_candidates(workspace: Path, candidates: list[dict[str, Any]], max_auto_accounts: int = 5) -> dict[str, Any]:
    """Recommend counterpart accounts from repeated candidate evidence, without asking the learner to judge."""
    watch_path=workspace/"config/watch_universe.json";watch=read_json(watch_path,{})
    excluded={str(value).strip() for value in watch.get("excluded_accounts",[]) if str(value).strip()}
    groups: dict[str, dict[str, Any]] = defaultdict(lambda:{"creative_ids":set(),"keywords":set(),"strong_flags":set(),"likes":0})
    for row in candidates:
        name=str(row.get("author_name") or ((row.get("author") or {}).get("display_name")) or "").strip()
        if not name or name in excluded: continue
        item=groups[name];item["creative_ids"].add(str(row.get("creative_id") or ""))
        item["keywords"].update(str(value) for value in (row.get("matched_keywords") or [row.get("query_keyword")]) if value)
        item["strong_flags"].update(key for key,value in (row.get("search_flags") or {}).items() if value)
        try:item["likes"]+=int(float((row.get("search_metrics") or {}).get("likes") or 0))
        except (TypeError,ValueError):pass
    suggestions=[]
    for name,item in groups.items():
        evidence_count=len(item["creative_ids"]);flag_count=len(item["strong_flags"])
        score=evidence_count*4+len(item["keywords"])*2+flag_count*3+min(item["likes"]//1000,5)
        suggestions.append({"account_name":name,"platform":"douyin","confidence":"high" if evidence_count>=2 or flag_count>=2 else "provisional",
            "score":score,"evidence_count":evidence_count,"matched_keywords":sorted(item["keywords"]),"strong_flags":sorted(item["strong_flags"]),
            "reason":"多个候选或强表现信号反复出现" if evidence_count>=2 or flag_count>=2 else "单条候选，继续观察后再升级",
            "last_observed_at":now()})
    suggestions.sort(key=lambda row:(-row["score"],row["account_name"]))
    existing=[str(value).strip() for value in watch.get("seed_accounts",[]) if isinstance(value,str) and str(value).strip()]
    promoted=[]
    for row in suggestions:
        if row["confidence"]!="high" or row["account_name"] in existing: continue
        if len(promoted)>=max_auto_accounts: break
        existing.append(row["account_name"]);promoted.append(row["account_name"])
    watch["seed_accounts"]=existing
    watch["suggested_accounts"]=suggestions[:20]
    watch["auto_promoted_accounts"]=promoted
    watch["account_discovery_policy"]="auto-promote only after repeated creatives or at least two strong search flags; learner can exclude"
    watch["updated_at"]=now()
    atomic_write_json(watch_path,watch)
    return watch
