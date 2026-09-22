#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from common import now, stable_id
from memory_store import MemoryStore

if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--experiment",required=True)
    p.add_argument("--decision",choices=["adopt","hold","reject"],required=True);p.add_argument("--reason",required=True)
    p.add_argument("--cooldown-days",type=int,default=7);a=p.parse_args()
    decided_at=now(); cooldown=None
    if a.decision in {"hold","reject"}: cooldown=(datetime.now().astimezone()+timedelta(days=a.cooldown_days)).isoformat(timespec="seconds")
    event={"schema_version":"decision_event/v1","event_id":stable_id(a.experiment,a.decision,decided_at)[:24],
        "experiment_id":a.experiment,"decision":a.decision,"reason":a.reason,"decided_by":"human",
        "decided_at":decided_at,"cooldown_until":cooldown}
    MemoryStore(Path(a.workspace)).add_decision(event);print(event["event_id"])
