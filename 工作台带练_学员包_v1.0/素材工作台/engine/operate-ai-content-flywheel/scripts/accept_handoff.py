#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
from contract_gate import validate

def accept(artifact:dict,expected:dict|None=None)->dict:
 errors=validate(artifact)
 if expected:
  for key in ("task_id","cycle_id","context_id"):
   if key in artifact and expected.get(key) and artifact.get(key)!=expected.get(key):errors.append(f"$.{key}:expected_mismatch")
 if errors:return {"accepted":False,"errors":sorted(set(errors)),"next_action":"退回原负责人修正交接，不由总控补写"}
 return {"accepted":True,"schema_version":artifact["schema_version"],"identity":{k:artifact.get(k) for k in ("task_id","cycle_id","context_id","artifact_id","version_id") if artifact.get(k)},"accepted_at":datetime.now().astimezone().isoformat(),"errors":[],"next_action":"按状态进入下一负责人"}
def main():
 p=argparse.ArgumentParser();p.add_argument("artifact",type=Path);p.add_argument("--expected",type=Path);p.add_argument("--receipt",type=Path,required=True);a=p.parse_args();load=lambda x:json.loads(x.read_text(encoding="utf-8")) if x else None;r=accept(load(a.artifact),load(a.expected));a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps({"accepted":r["accepted"],"receipt":str(a.receipt)},ensure_ascii=False));return 0 if r["accepted"] else 1
if __name__=="__main__":raise SystemExit(main())
