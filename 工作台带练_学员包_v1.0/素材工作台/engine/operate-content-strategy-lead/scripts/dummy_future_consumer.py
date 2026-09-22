#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

REQUIRED={"schema_version","experiment_id","enterprise_context_id","target_customer","hypothesis","evidence_creative_ids","single_variable","constants","claim_boundaries"}
def consume(path:Path)->dict:
    card=json.loads(path.read_text(encoding="utf-8"));missing=REQUIRED-set(card)
    if card.get("schema_version")!="experiment_task/v1" or missing: raise ValueError(f"future consumer contract failed: {sorted(missing)}")
    return {"status":"ACK","experiment_id":card["experiment_id"],"consumer":"dummy-producer/v1"}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("card");a=p.parse_args();print(json.dumps(consume(Path(a.card)),ensure_ascii=False))
