#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
from run_once import run

def parse_time(value:str)->datetime:return datetime.fromisoformat(value.replace("Z","+00:00"))

def trigger_due(trigger:dict,signal:dict,now:datetime)->tuple[bool,str]:
 kind=trigger.get("kind")
 if kind=="manual":return True,"人工启动"
 if kind=="time":
  run_at=trigger.get("run_at")
  if not run_at:return False,"还没有设定开工时间"
  due=now>=parse_time(run_at);return due,"已到开工时间" if due else "等待设定时间"
 if kind=="event":
  due=signal.get("event")==trigger.get("event");return due,"已收到启动事件" if due else "等待指定事件"
 if kind=="condition":
  due=signal.get(trigger.get("field"))==trigger.get("equals");return due,"启动条件已满足" if due else "启动条件还没满足"
 return False,"启动方式尚未识别"

def evaluate(state:dict,policy:dict,trigger:dict,signal:dict,now:datetime)->dict:
 due,reason=trigger_due(trigger,signal,now)
 if not due:return {"schema_version":"automation_receipt/v1","project_id":state.get("project_id"),"cycle_id":state.get("cycle_id"),"task_id":state.get("task_id"),"checked_at":now.isoformat(),"trigger":{"kind":trigger.get("kind"),"due":False,"reason":reason},"decision":"wait","dispatch_to":None,"learner_message":reason,"next_check":trigger.get("run_at") or policy.get("next_check"),"budget":{"daily_budget":policy.get("daily_budget"),"spent_today":policy.get("spent_today")},"stopped":False}
 receipt=run(state,policy);receipt["trigger"]={"kind":trigger.get("kind"),"due":True,"reason":reason};return receipt

def main()->int:
 p=argparse.ArgumentParser();p.add_argument("state",type=Path);p.add_argument("policy",type=Path);p.add_argument("trigger",type=Path);p.add_argument("output",type=Path);p.add_argument("--signal",type=Path);p.add_argument("--now");a=p.parse_args();load=lambda path:json.loads(path.read_text(encoding="utf-8"));now=parse_time(a.now) if a.now else datetime.now().astimezone();result=evaluate(load(a.state),load(a.policy),load(a.trigger),load(a.signal) if a.signal else {},now);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(result["decision"],result["learner_message"]);return 0
if __name__=="__main__":raise SystemExit(main())
