#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from urllib.parse import urlparse
from common import atomic_write_json,atomic_write_text,stable_id

def sanitize_row(row:dict)->tuple[dict,int]:
    changed=0
    for key,value in list(row.items()):
        if isinstance(value,dict):row[key],n=sanitize_row(value);changed+=n
        elif isinstance(value,list):
            clean=[]
            for item in value:
                if isinstance(item,dict):item,n=sanitize_row(item);changed+=n
                clean.append(item)
            row[key]=clean
        elif isinstance(value,str) and value.startswith(("http://","https://")):
            parsed=urlparse(value)
            if parsed.query and (key in {"canonical_url","media_url","download_url"} or any(s in parsed.netloc for s in ("douyinvod","byteoversea","amemv"))):
                row[key]=None;row[f"{key}_redacted_hash"]=stable_id(value);changed+=1
    return row,changed

def sanitize_value(value):
    if isinstance(value,dict):return sanitize_row(value)
    if isinstance(value,list):
        result=[];total=0
        for item in value:
            clean,n=sanitize_value(item);result.append(clean);total+=n
        return result,total
    return value,0

def sanitize(root:Path)->int:
    total=0
    for path in root.rglob("*.json"):
        try:data=json.loads(path.read_text(encoding="utf-8"))
        except Exception:continue
        data,n=sanitize_value(data)
        if n:atomic_write_json(path,data);total+=n
    for path in root.rglob("*.jsonl"):
        rows=[];changed=0
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():row,n=sanitize_row(json.loads(line));rows.append(row);changed+=n
        except Exception:continue
        if changed:atomic_write_text(path,"".join(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n" for row in rows));total+=changed
    return total
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root");a=p.parse_args();print(sanitize(Path(a.root)))
