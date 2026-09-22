#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,ssl
try:
 import certifi
except ImportError:
 certifi=None
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

CONFIG=Path.home()/".config/content-creative-intelligence/tikhub.json"
LEGACY_CONFIG=Path.home()/".xiaohongshu/tikhub_config.json"
ENDPOINT="/api/v1/douyin/app/v3/fetch_user_post_videos"

def token():
 value=os.environ.get("TIKHUB_API_TOKEN","").strip()
 if value:return value
 for path in (CONFIG,LEGACY_CONFIG):
  if path.is_file():
   data=json.loads(path.read_text(encoding="utf-8-sig"));value=str(data.get("api_token") or data.get("tikhub_api_token") or "").strip()
   if value:return value
 return ""
def fetch(sec_user_id:str,cursor:int=0,count:int=20)->dict:
 if not token():raise RuntimeError("TikHub 还没连接好")
 base=os.environ.get("TIKHUB_BASE_URL","https://api.tikhub.io").rstrip("/");url=base+ENDPOINT+"?"+urlencode({"sec_user_id":sec_user_id,"max_cursor":cursor,"count":min(max(count,1),20),"sort_type":0})
 req=Request(url,headers={"Authorization":f"Bearer {token()}","Accept":"application/json","User-Agent":"ContentGrowthLead/0.1"})
 context=ssl.create_default_context(cafile=certifi.where() if certifi else None)
 with urlopen(req,timeout=30,context=context) as r:return json.loads(r.read().decode("utf-8"))
def find_rows(value):
 if isinstance(value,dict):
  for key in ("aweme_list","awemeList","items","videos"):
   rows=value.get(key)
   if isinstance(rows,list) and (not rows or isinstance(rows[0],dict)):return rows
  for child in value.values():
   found=find_rows(child)
   if found is not None:return found
 return None
def normalize(payload:dict)->dict:
 rows=find_rows(payload) or [];items=[]
 for row in rows:
  aid=str(row.get("aweme_id") or row.get("item_id") or row.get("id") or "").strip();stats=row.get("statistics") or {}
  if not aid:continue
  created=row.get("create_time");published=datetime.fromtimestamp(created,tz=timezone.utc).astimezone().isoformat() if isinstance(created,(int,float)) else created
  engagement=[stats.get("digg_count"),stats.get("comment_count"),stats.get("share_count"),stats.get("collect_count")];plays=stats.get("play_count");warnings=[]
  if plays==0 and any(isinstance(x,(int,float)) and x>0 for x in engagement):plays=None;warnings.append("播放数0与正互动冲突，按未知处理")
  items.append({"channel":"douyin","content_id":aid,"title":row.get("desc") or "未命名短视频","published_at":published,"content_locator":f"https://www.douyin.com/video/{aid}","observed_at":datetime.now().astimezone().isoformat(),"data_through":datetime.now().date().isoformat(),"public_metrics":{"plays":plays,"likes":stats.get("digg_count"),"comments":stats.get("comment_count"),"shares":stats.get("share_count"),"collects":stats.get("collect_count")},"metric_warnings":warnings,"internal_metrics":{},"business_results":{},"missing_fields":["内部转化","投放消耗","目标客户质量",*( ["可靠播放数"] if warnings else [])],"source_refs":[f"tikhub:{payload.get('request_id') or 'request'}:{aid}"]})
 return {"schema_version":"content_ledger_import/v1","connector":"tikhub/douyin-account-posts","items":items,"raw_count":len(rows),"normalized_count":len(items)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--sec-user-id",required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--count",type=int,default=20);a=p.parse_args();result=normalize(fetch(a.sec_user_id,count=a.count));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps({"count":len(result["items"]),"output":str(a.output)},ensure_ascii=False));return 0
if __name__=="__main__":raise SystemExit(main())
