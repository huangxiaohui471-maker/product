#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from common import append_jsonl,read_jsonl

REQUIRED={"schema_version","feedback_id","experiment_id","event_type","occurred_at","source","metrics","human_notes"}
def ingest(workspace:Path,event:dict)->None:
    missing=REQUIRED-set(event)
    if missing or event.get("schema_version")!="feedback_event/v1":raise ValueError(f"feedback contract failed: {sorted(missing)}")
    if event["event_type"] not in {"published","metric_snapshot","human_review","stopped"}:raise ValueError("feedback event_type invalid")
    path=workspace/"memory/future_feedback.jsonl"
    if not any(row.get("feedback_id")==event["feedback_id"] for row in read_jsonl(path)):append_jsonl(path,event)

def ingest_result(workspace:Path,result:dict)->None:
    required={"schema_version","result_id","experiment_id","observed_at","source","metrics","measurement_window"}
    missing=required-set(result)
    if missing or result.get("schema_version")!="performance_result/v1":raise ValueError(f"performance result contract failed: {sorted(missing)}")
    path=workspace/"memory/future_performance_results.jsonl"
    if not any(row.get("result_id")==result["result_id"] for row in read_jsonl(path)):append_jsonl(path,result)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--file",required=True);a=p.parse_args();payload=json.loads(Path(a.file).read_text(encoding="utf-8"));(ingest_result if payload.get("schema_version")=="performance_result/v1" else ingest)(Path(a.workspace),payload);print("ACK")
