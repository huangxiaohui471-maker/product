#!/usr/bin/env python3
"""Single deterministic front door: choose one real role and persist the shift."""
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
from dispatch import dispatch

ROLE_SKILLS={
    "strategy_lead":"operate-content-strategy-lead",
    "production_lead":"operate-content-production-lead",
    "growth_lead":"operate-content-growth-lead",
    "orchestrator":"operate-ai-content-flywheel",
}
ROLE_NAMES={"strategy_lead":"策略负责人","production_lead":"生产负责人","growth_lead":"增长负责人","orchestrator":"飞轮总控"}
RINGS={"learn_company":"discovery","building_whitepaper":"discovery","find_direction":"judgment","recover_production":"production","make_content":"production","review_content":"production","recover_growth":"review","review_results":"review","wait_or_review_results":"touch","next_cycle":"upgrade","show_status":"judgment","configure_automation":"upgrade"}

def read(path:Path)->dict:
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:return {}

def turn(workspace:Path,text:str)->dict:
    workspace=workspace.expanduser().resolve();result=dispatch(text,workspace);old=read(workspace/"task_state.json")
    owner=result["owner"];goal=result["goal"];skill=ROLE_SKILLS[owner];skill_path=Path(__file__).resolve().parents[2]/skill/"SKILL.md"
    if not skill_path.is_file():skill_path=Path(__file__).resolve().parents[1]/"SKILL.md"
    role_name=ROLE_NAMES[owner]
    # Roles are operational metadata, not a learner interaction.  Always use
    # the outcome-oriented message returned by the route.
    learner_message=result["learner_message"]
    strategy=read(workspace/"strategy_to_production.json");context=read(workspace/"context/shared_enterprise_context.json")
    state={"schema_version":"flywheel_task_state/v1","project_id":old.get("project_id") or "ai-content-flywheel","cycle_id":strategy.get("cycle_id") or old.get("cycle_id") or "current-cycle","task_id":strategy.get("task_id") or old.get("task_id") or "current-task","updated_at":datetime.now().astimezone().isoformat(),"current_ring":RINGS.get(goal,"judgment"),"current_owner":owner,"status":"repairing" if goal.startswith("recover_") else "running","context_id":strategy.get("context_id") or context.get("context_id") or old.get("context_id") or "current-context","input_refs":[],"artifact_refs":[],"waiting_for":None,"next_action":result["action"],"completion_gate":["只由当前负责人完成本岗位工作","完成后写回真实交接"]}
    workspace.mkdir(parents=True,exist_ok=True);(workspace/"task_state.json").write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"schema_version":"department_turn/v1","owner":owner,"owner_name":role_name,"goal":goal,"skill":skill,"skill_path":str(skill_path),"learner_message":learner_message,"task_state":str(workspace/"task_state.json"),"must_execute_specialist":owner!="orchestrator"}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("workspace",type=Path);p.add_argument("text");a=p.parse_args();print(json.dumps(turn(a.workspace,a.text),ensure_ascii=False,indent=2))
