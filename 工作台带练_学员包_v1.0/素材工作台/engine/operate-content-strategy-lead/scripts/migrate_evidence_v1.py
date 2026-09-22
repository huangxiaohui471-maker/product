#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json,read_json,now

def migrate(root:Path)->int:
    changed=0
    for path in root.rglob("evidence.json"):
        evidence=read_json(path,{});metrics=evidence.get("metrics") or {};engagement=[metrics.get(k) for k in ("likes","comments","shares","collects")]
        if metrics.get("plays")==0 and any(isinstance(v,(int,float)) and v>0 for v in engagement):
            metrics["plays"]=None;warnings=evidence.setdefault("metric_warnings",[])
            warning="play_count_zero_conflicts_with_positive_engagement_treated_as_unknown"
            if warning not in warnings:warnings.append(warning)
            evidence.setdefault("migrations",[]).append({"migration":"normalize_play_zero/v1","at":now()});atomic_write_json(path,evidence);changed+=1
    return changed
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root");a=p.parse_args();print(migrate(Path(a.root)))
