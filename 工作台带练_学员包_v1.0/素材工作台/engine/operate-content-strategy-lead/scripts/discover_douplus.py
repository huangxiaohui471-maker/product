#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import atomic_write_json, now, stable_id
from cost_ledger import CostLedger
from tikhub_adapter import request

CATEGORIES={"life":619,"education":626,"food":628}


def normalize_rows(rows: list[dict[str, Any]], category: str, dimension: int) -> list[dict[str, Any]]:
    def estimate(value: Any) -> Any:
        # Supplier ranking payloads sometimes return string zero beside much
        # larger public-detail engagement. Treat that as unavailable, not truth.
        return None if value in (None, "", 0, "0", 0.0) else value
    result=[]
    for item in rows:
        item_id=str(item.get("itemId") or "").strip()
        if not item_id: continue
        stats=item.get("statistics") or {};author=item.get("author") or {}
        result.append({
            "schema_version":"douplus_candidate/v1",
            "creative_id":f"douyin:{item_id}","platform":"douyin","canonical_url":f"https://www.douyin.com/video/{item_id}",
            "title":str(item.get("title") or "").strip(),"author_name":str(author.get("nickname") or "").strip(),
            "published_at":item.get("createTime"),"category":category,"ranking_dimension":dimension,
            "organic_metrics":{},"paid_metrics":{},
            "estimated_metrics":{"views":estimate(stats.get("ViewCnt")),"likes":estimate(stats.get("LikeCnt")),"shares":estimate(stats.get("ShareCnt")),
                "comments":estimate(stats.get("CommentCnt")),"finish_rate":estimate(stats.get("FinishPlayRate")),"like_rate":estimate(stats.get("LikeRate")),
                "heat_index":estimate(stats.get("IndexCnt")),"new_fans":estimate(stats.get("NewFansCnt"))},
            "evidence_class":"commercial_like_proxy",
            "paid_evidence":{"level":"strong_signal","sources":["douplus_video_ranking_via_tikhub"]},
            "evidence_note":"入选 DOU+ 视频排行榜是平台推广场景强信号，不证明该视频真实消耗、转化或 ROI",
            "source_library_url":"douyin://douplus/video-ranking",
            "provenance":{"adapter":"tikhub_douplus_ranking","adapter_version":"openapi-v5.3.2"},
        })
    return result


def discover(workspace: Path, categories: list[str], time_range: int=2, dimension: int=5) -> Path:
    unknown=[name for name in categories if name not in CATEGORIES]
    if unknown: raise ValueError("未知 DOU+ 垂类："+", ".join(unknown))
    ledger=CostLedger(workspace);policy=ledger.policy();candidates=[];receipts=[];errors=[]
    for category in categories:
        try:
            ledger.guard("search",max_daily=int(policy.get("max_search_per_day",50)),projected_cost=.001,daily_budget=float(policy.get("daily_budget_usd",1.5)))
            payload=request("/api/v1/douyin/douplus/fetch_video_ranking",method="POST",body={"time_range":time_range,"tag_id":CATEGORIES[category],"dim_type":dimension,"adv_id":""})
            rows=(((payload.get("data") or {}).get("data")) or [])
            normalized=normalize_rows(rows,category,dimension);candidates.extend(normalized)
            receipts.append({"category":category,"tag_id":CATEGORIES[category],"dimension":dimension,"request_id":payload.get("request_id"),"row_count":len(rows)})
            ledger.record("search",.001,f"douplus:{category}:{dimension}")
        except Exception as error:
            errors.append({"category":category,"type":type(error).__name__,"message":str(error)[:300]})
    unique={row["creative_id"]:row for row in candidates};stamp=now().replace(":","-")
    out=workspace/"runs"/f"douplus-{stamp}"/"candidates.json"
    payload={"schema_version":"candidate_batch/v1","batch_id":stable_id(stamp,*categories,"douplus")[:24],"created_at":now(),
        "connector":"tikhub/douplus-video-ranking","source_receipts":receipts,"evidence_policy":"B-level strong promotion signal; never paid spend/conversion truth",
        "candidates":list(unique.values()),"errors":errors,"cost":{"requests":len(receipts),"known_unit_cost_usd":.001,"known_cost_usd":round(len(receipts)*.001,6)},
        "status":"succeeded" if unique and not errors else "partial" if unique else "failed"}
    atomic_write_json(out,payload)
    if not unique: raise RuntimeError(f"DOU+ 排行榜没有取得候选；详情见 {out}")
    return out


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--workspace",required=True);parser.add_argument("--category",action="append",choices=sorted(CATEGORIES),required=True)
    parser.add_argument("--time-range",type=int,choices=[1,2,3],default=2);parser.add_argument("--dimension",type=int,choices=[1,2,3,4,5],default=5);args=parser.parse_args()
    print(discover(Path(args.workspace),args.category,args.time_range,args.dimension))
