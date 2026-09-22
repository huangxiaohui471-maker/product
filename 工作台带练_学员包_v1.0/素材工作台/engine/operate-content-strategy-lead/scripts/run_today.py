#!/usr/bin/env python3
"""Single backstage entry for the content strategy lead's daily discovery."""
from __future__ import annotations
import argparse,json,re
from datetime import datetime,timedelta
from pathlib import Path

from common import atomic_write_json,now,read_json,stable_id
from daily_run import run_daily
from discover_candidates import discover
from import_ad_intelligence import normalize

ACTIVE=Path.home()/".config/content-creative-intelligence/active-workspace.json"
FEIGUA_COOKIE=Path.home()/".config/feigua-yt/cookie.txt"
FEIGUA_STATE=Path.home()/".config/feigua-yt/live-status.json"

def active_workspace(explicit:str="")->Path:
    value=explicit or str(read_json(ACTIVE,{}).get("workspace") or "")
    if not value:raise ValueError("还没有完成企业业务配置")
    path=Path(value).expanduser().resolve()
    if not (path/"config/enterprise_context.json").is_file():raise ValueError("企业业务配置需要重新确认")
    return path

def require_active_whitepaper(workspace:Path)->dict:
    context=read_json(workspace/"context/shared_enterprise_context.json",{})
    if context.get("schema_version")!="shared_enterprise_context/v1":raise ValueError("先让我把你的企业理解整理成白皮书")
    return context

def feigua_ready()->bool:
    try:
        state=read_json(FEIGUA_STATE,{})
        checked=datetime.fromisoformat(str(state.get("checked_at") or "").replace("Z","+00:00"))
        return state.get("live_query_passed") is True and FEIGUA_COOKIE.is_file() and datetime.now().astimezone()-checked.astimezone()<timedelta(hours=24)
    except Exception:return False

def feigua_candidates(workspace:Path)->list[dict]:
    if not feigua_ready():return []
    import feigua_search
    watch=read_json(workspace/"config/watch_universe.json",{})
    keyword=str(next(iter(watch.get("keywords") or []),""))
    yesterday=datetime.now()-timedelta(days=1);day=yesterday.strftime("%Y%m%d")
    try:
        rows,_,_=feigua_search.search(FEIGUA_COOKIE.read_text(encoding="utf-8").strip(),keyword,day,day,1,"-1","ExposureCount",1,10,0,True)
    except Exception:
        atomic_write_json(FEIGUA_STATE,{"live_query_passed":False,"checked_at":now()})
        return []
    result=[]
    for index,row in enumerate(rows,2):
        try:candidate=normalize(row,"feigua_yitou",index,True)
        except ValueError:continue
        if not candidate.get("canonical_url"):continue
        # Feigua provides the paid-creative signal; the retained media is
        # independently resolved from the public canonical URL through TikHub.
        candidate.update({"schema_version":"candidate/v1","media_url":"","source_route":"feigua_signal+tikhub_public_media"})
        result.append(candidate)
    return result

def combined_batch(workspace:Path)->tuple[Path,str]:
    public_path=discover(workspace);public=read_json(public_path,{})
    feigua=feigua_candidates(workspace)
    unique={str(row.get("creative_id")):row for row in public.get("candidates") or []}
    for row in feigua:unique[str(row.get("creative_id"))]=row
    route="TikHub+飞瓜" if feigua else "TikHub"
    path=workspace/"runs"/("daily-source-"+now().replace(":","-"))/"candidates.json"
    atomic_write_json(path,{"schema_version":"candidate_batch/v1","batch_id":stable_id(now(),route)[:24],"created_at":now(),"connector":route,"source_batches":[str(public_path)],"candidates":list(unique.values()),"errors":public.get("errors") or [],"cost":public.get("cost") or {},"status":"succeeded"})
    return path,route

def run(workspace:Path,top:int=3)->dict:
    require_active_whitepaper(workspace)
    batch,route=combined_batch(workspace)
    receipt_path=run_daily(workspace,batch,False,top,"local")
    receipt=read_json(receipt_path,{})
    return {"status":receipt.get("current_stage"),"source":route,"workspace":str(workspace),"dashboard":str(workspace/"dashboard.html"),"daily_receipt":str(receipt_path),"learner_message":"今天的素材已经找回来了，我会继续完成深拆后打开看板。" if receipt.get("current_stage")=="WAIT_REVIEW" else "今天的素材和建议已经准备好。"}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--workspace",default="");parser.add_argument("--top",type=int,default=3);args=parser.parse_args()
    print(json.dumps(run(active_workspace(args.workspace),args.top),ensure_ascii=False,indent=2))
