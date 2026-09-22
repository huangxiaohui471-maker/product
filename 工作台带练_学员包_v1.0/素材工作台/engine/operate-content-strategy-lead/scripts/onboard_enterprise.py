#!/usr/bin/env python3
"""Create the shared enterprise whitepaper and its legacy runtime projection in one transaction."""
from __future__ import annotations
import argparse,json,shutil
from datetime import datetime
from pathlib import Path
from build_enterprise_whitepaper import build,render
from common import atomic_write_json,read_json
from scan_enterprise_materials import scan
from setup_from_brief import configure

def owner_source()->dict:
 return {"source_id":"src-owner-brief","source_type":"owner_statement","locator":"current onboarding conversation","observed_at":datetime.now().astimezone().isoformat(),"extract_status":"confirmed_owner_input"}

def list_values(value)->list[str]:
 if isinstance(value,list):return [str(x).strip() for x in value if str(x).strip()]
 return [x.strip() for x in str(value or "").replace("，",",").split(",") if x.strip()]

def default_claims(brief:dict)->dict:
 products=list_values(brief.get("products"));proof=list_values(brief.get("proof_assets"));capabilities=list_values(brief.get("production_capabilities"));boundaries=list_values(brief.get("claim_boundaries"));platforms=list_values(brief.get("platforms")) or ["抖音"]
 knowledge=[]
 for statement in [brief.get("long_term_business"),brief.get("business_goal"),brief.get("current_priority"),*proof,*capabilities]:
  if statement:knowledge.append({"kind":"fact","statement":str(statement),"source_refs":["src-owner-brief"]})
 foundation={
  "customer":{"primary_segment":brief.get("target_customer"),"source_refs":["src-owner-brief"]},
  "battlefield":{},
  "solution":{"concept":"、".join(products),"source_refs":["src-owner-brief"]},
  "decision_path":{},
  "channels":[{"platform":x,"business_job":brief.get("business_goal") or brief.get("current_priority"),"confirmed_constraints":boundaries,"source_refs":["src-owner-brief"]} for x in platforms]
 }
 return {"company":brief.get("name"),"created_by":"agent_pending_owner_review","current_business_question":brief.get("business_goal") or brief.get("current_priority"),"strategy_foundation":foundation,"people":[{"segment":brief.get("target_customer") or "待补充","description":brief.get("target_customer") or "待补充"}],"offerings":[{"name":x,"description":brief.get("long_term_business") or ""} for x in products],"scenes":[{"stage":x,"touchpoint":f"当前内容和转化渠道：{x}"} for x in platforms],"knowledge":knowledge,"boundaries":[{"kind":"boundary","statement":x,"source_refs":["src-owner-brief"]} for x in boundaries]}

def merge_claims(base:dict,extra:dict)->dict:
 result=dict(base)
 for key in ("company","created_by","current_business_question"):
  if extra.get(key):result[key]=extra[key]
 for key in ("strategy_foundation","people","offerings","scenes","knowledge","boundaries"):
  if extra.get(key):result[key]=extra[key]
 return result

def onboard(workspace:Path,brief:dict,materials:Path|None=None,claims:dict|None=None)->dict:
 workspace=workspace.expanduser().resolve();context_dir=workspace/"context";context_dir.mkdir(parents=True,exist_ok=True)
 inventory=scan(materials) if materials else {"schema_version":"enterprise_source_inventory/v1","source_root":None,"created_at":datetime.now().astimezone().isoformat(),"items":[],"counts":{"total":0,"text_available":0,"needs_extraction":0}}
 inventory["items"].append(owner_source());inventory["counts"]["total"]=len(inventory["items"]);atomic_write_json(context_dir/"source_inventory.json",inventory)
 prepared=merge_claims(default_claims(brief),claims or {})
 previous_path=context_dir/"shared_enterprise_context.json";previous=read_json(previous_path,{}) if previous_path.is_file() else None
 whitepaper_path=context_dir/"企业人货场白皮书.html"
 # The current files stay simple for learners. Older confirmed meaning is preserved
 # as compact machine state, not duplicated Markdown documentation.
 if previous:
  versions=context_dir/"versions";versions.mkdir(parents=True,exist_ok=True)
  stem=f"V{previous.get('version',0)}_{previous.get('context_id','unknown')}"
  atomic_write_json(versions/f"shared_enterprise_context_{stem}.json",previous)
  if whitepaper_path.is_file():shutil.copy2(whitepaper_path,versions/f"企业人货场白皮书_{stem}.html")
 context=build(inventory,prepared,previous);atomic_write_json(previous_path,context);whitepaper_path.write_text(render(context),encoding="utf-8")
 receipt=configure(workspace,brief,shared_context=context)
 atomic_write_json(context_dir/"onboarding_state.json",{"schema_version":"strategy_onboarding_state/v1","stage":"READY_FOR_DISCOVERY","context_id":context["context_id"],"context_version":context["version"],"whitepaper":str(whitepaper_path)})
 return {"schema_version":"strategy_onboarding_receipt/v1","status":"ready_for_discovery","context_id":context["context_id"],"context_version":context["version"],"whitepaper":str(whitepaper_path),"watch_keywords":receipt["watch_universe"]["keywords"],"learner_message":"企业白皮书已经整理好，我会按这份理解继续找内容。哪里不对，你随时直接纠正。"}

def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--workspace",type=Path,required=True);p.add_argument("--brief",type=Path,required=True);p.add_argument("--materials",type=Path);p.add_argument("--claims",type=Path);a=p.parse_args();result=onboard(a.workspace,read_json(a.brief,{}),a.materials,read_json(a.claims,{}) if a.claims else None);print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
