#!/usr/bin/env python3
"""Build one current department state from the three real handoffs."""
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path

def derive(strategy:dict|None,production:dict|None,growth:dict|None)->dict:
    base=strategy or {};ring="discovery";owner="strategy_lead";status="running";next_action="找出今天最值得做的方向";refs=[]
    if strategy:
        refs.append("strategy_to_production")
        if strategy.get("status")=="ready_for_production":ring="production";owner="production_lead";next_action="沿当前方向做出第一版内容"
        else:ring="judgment";owner="strategy_lead";next_action="补齐当前方向后直接交给生产"
    if production:
        refs.append("production_run");ring="production";owner="production_lead";next_action=production.get("next_action") or production.get("next_user_action") or "继续完成当前作品"
        if production.get("status")=="ADOPTED":ring="touch";owner="growth_lead";next_action="记录真实使用位置并等待结果"
    if growth:
        refs.append("growth_learning_return");ring="upgrade";owner="orchestrator";next_action="把本轮学习写回并开始下一轮"
    return {"schema_version":"flywheel_task_state/v1","project_id":"ai-content-flywheel","cycle_id":base.get("cycle_id") or (growth or {}).get("cycle_id") or "current-cycle","task_id":base.get("task_id") or (growth or {}).get("task_id") or "current-task","updated_at":datetime.now().astimezone().isoformat(),"current_ring":ring,"current_owner":owner,"status":status,"context_id":base.get("context_id") or "current-context","input_refs":refs,"artifact_refs":refs,"waiting_for":None,"next_action":next_action,"completion_gate":["三个工位使用同一企业底稿","当前状态来自真实交接"]}

def main():
    p=argparse.ArgumentParser();p.add_argument("--strategy",type=Path);p.add_argument("--production",type=Path);p.add_argument("--growth",type=Path);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    load=lambda x:json.loads(x.read_text(encoding="utf-8")) if x and x.is_file() else None
    result=derive(load(a.strategy),load(a.production),load(a.growth));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(result["current_owner"],result["next_action"]);return 0
if __name__=="__main__":raise SystemExit(main())
