#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path

def run(state:dict,policy:dict)->dict:
 status=state.get("status");owner=state.get("current_owner");action="stop";message="当前状态不允许自动继续";dispatch=None
 if status in {"cancelled","completed"}:action="stop";message="任务已经结束"
 elif status=="running" and owner in {"strategy_lead","production_lead","growth_lead"}:action="dispatch";dispatch=owner;message=state.get("next_action")
 elif status in {"waiting_confirmation","waiting_permission"}:action="ask";message=(state.get("waiting_for") or {}).get("what") or state.get("next_action")
 elif status=="waiting_result":action="wait";message="真实结果还没到；到观察时间再检查"
 elif status=="tool_failure":
  failures=int(policy.get("same_failure_count",0))
  if failures<2:action="retry";message="再重试一次当前连接"
  else:action="ask";message="同一个连接已经连续失败，已停止自动重试并准备降级方案"
 elif status=="missing_context":action="dispatch";dispatch="strategy_lead";message="先补企业共同底稿"
 return {"schema_version":"automation_receipt/v1","project_id":state.get("project_id"),"cycle_id":state.get("cycle_id"),"task_id":state.get("task_id"),"checked_at":datetime.now().astimezone().isoformat(),"decision":action,"dispatch_to":dispatch,"learner_message":message,"next_check":policy.get("next_check") if action=="wait" else None,"budget":{"daily_budget":policy.get("daily_budget"),"spent_today":policy.get("spent_today")},"stopped":action in {"ask","stop"}}
def main():
 p=argparse.ArgumentParser();p.add_argument("state",type=Path);p.add_argument("policy",type=Path);p.add_argument("output",type=Path);a=p.parse_args();r=run(json.loads(a.state.read_text(encoding="utf-8")),json.loads(a.policy.read_text(encoding="utf-8")));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(r["decision"],r["learner_message"]);return 0
if __name__=="__main__":raise SystemExit(main())
