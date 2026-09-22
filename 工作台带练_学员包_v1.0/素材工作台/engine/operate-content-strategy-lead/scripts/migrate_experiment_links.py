#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json,read_json
from render_dashboard import render

def _adapter(evidence:dict)->str:
    return str(evidence.get("adapter") or (evidence.get("provenance") or {}).get("adapter") or "manual")

def migrate(workspace:Path)->int:
    count=0; rows=[]
    for exp in (workspace/"runs").glob("*/experiment.json"):
        task=read_json(exp,{});evidence=read_json(exp.parent/"creative/evidence.json",{})
        media=(evidence.get("media") or {}).get("sha256")
        changed=False
        if media and task.get("source_media_sha256")!=media:
            task["source_media_sha256"]=media;changed=True
        rows.append((exp,task,media,_adapter(evidence)))
        if changed:atomic_write_json(exp,task);count+=1

    # When a connector later enriches an earlier manual copy of the same bytes,
    # display the newest connector-backed task and hide the evidence-poor copy.
    by_media={}
    for row in rows:
        if row[2]:by_media.setdefault(row[2],[]).append(row)
    for group in by_media.values():
        if len(group)<2:continue
        preferred=sorted((r for r in group if r[3] not in {"manual","unknown","none"}),key=lambda r:r[0].parent.name,reverse=True)
        if not preferred:continue
        winner=preferred[0]
        for exp,task,_,_ in group:
            visible=exp==winner[0]
            if task.get("visible_in_dashboard",True)!=visible or (visible and not task.get("is_evidence_enrichment")):
                task["visible_in_dashboard"]=visible
                if visible:task["is_evidence_enrichment"]=True
                atomic_write_json(exp,task);count+=1
    render(workspace,workspace/"dashboard.html");return count
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("workspace");a=p.parse_args();print(migrate(Path(a.workspace)))
