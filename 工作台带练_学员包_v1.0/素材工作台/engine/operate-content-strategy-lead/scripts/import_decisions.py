#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
from memory_store import MemoryStore
from common import atomic_write_text, atomic_write_json, read_jsonl

REQUIRED={"schema_version","event_id","experiment_id","decision","reason","decided_by","decided_at","cooldown_until"}

def import_events(workspace: Path, source: Path) -> int:
    events=json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(events,list): raise ValueError("决策文件必须是 JSON 数组")
    store=MemoryStore(workspace); current=read_jsonl(store.decisions_path);existing={row.get("event_id") for row in current};pending=[]
    for event in events:
        missing=REQUIRED-set(event)
        if missing: raise ValueError(f"决策事件缺字段: {sorted(missing)}")
        if event["schema_version"]!="decision_event/v1" or event["decision"] not in {"adopt","hold","reject"}: raise ValueError("决策契约或枚举无效")
        if event["event_id"] not in existing: pending.append(event);existing.add(event["event_id"])
    if not pending:return 0
    combined=current+pending
    atomic_write_text(store.decisions_path,"".join(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n" for row in combined))
    cooldowns=store.cooldowns()
    for event in pending:
        if event.get("cooldown_until"):cooldowns[event["experiment_id"]]=event["cooldown_until"]
    atomic_write_json(store.cooldowns_path,cooldowns)
    return len(pending)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--workspace",required=True);p.add_argument("--file",required=True);a=p.parse_args();print(import_events(Path(a.workspace),Path(a.file)))
