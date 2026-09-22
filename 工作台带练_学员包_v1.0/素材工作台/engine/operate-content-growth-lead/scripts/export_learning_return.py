#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
from validate_diagnosis import ladder,validate

def export(handoff:dict,ledger:dict,diagnosis:dict)->dict:
    errors=validate(diagnosis,ledger)
    if errors:raise ValueError("会诊未通过："+";".join(errors))
    focus=next((x for x in diagnosis.get("items") or [] if x.get("content_id")==handoff.get("artifact_id")),None) or (diagnosis.get("items") or [None])[0]
    if not focus:raise ValueError("还没有可以回传的真实复盘")
    focus=ladder(focus)
    return {"schema_version":"growth_learning_return/v1","return_id":f"return-{handoff['task_id']}-{handoff['version_id']}","task_id":handoff["task_id"],"cycle_id":handoff["cycle_id"],"context_id":handoff["context_id"],"artifact_id":handoff["artifact_id"],"version_id":handoff["version_id"],"created_at":datetime.now().astimezone().isoformat(),"touch_facts":diagnosis.get("touch_facts") or [],"result_facts":focus["facts"],"observations":focus["observations"],"measurement":{"window":focus.get("measurement_window") or "待补充","data_through":focus.get("data_through"),"missing_fields":focus["unknowns"]},"primary_explanation":focus.get("primary_explanation"),"competing_explanations":focus.get("competing_explanations") or [],"hypotheses":focus["hypotheses"],"unknowns":focus["unknowns"],"decision":focus["decision"],"next_experiment":{"change":focus.get("next_experiment") or "下一次只改变一处","hold":focus.get("hold_conditions") or [],"start_condition":focus.get("start_condition") or "下一次制作时"},"upgrade_candidates":diagnosis.get("upgrade_candidates") or [],"source_refs":list(dict.fromkeys(focus.get("source_refs") or []))}

def main():
 p=argparse.ArgumentParser();p.add_argument("handoff",type=Path);p.add_argument("ledger",type=Path);p.add_argument("diagnosis",type=Path);p.add_argument("output",type=Path);a=p.parse_args();r=export(*[json.loads(x.read_text(encoding="utf-8")) for x in (a.handoff,a.ledger,a.diagnosis)]);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(r["return_id"]);return 0
if __name__=="__main__":raise SystemExit(main())
