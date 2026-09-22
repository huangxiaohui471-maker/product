#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,json,re
from pathlib import Path

def revise(bundle:dict,feedback:str)->dict:
 suites=bundle.get("image_suites") or []
 if not suites:raise ValueError("还没有首版图片套装")
 old=suites[-1];new=copy.deepcopy(old);match=re.search(r"v(\d+)$",str(old.get("version_id")))
 if not match:raise ValueError("版本编号不符合约定")
 new["supersedes"]=old["version_id"];new["version_id"]=re.sub(r"v\d+$",f"v{int(match.group(1))+1}",old["version_id"]);new["user_feedback"]=[feedback];new["items"]=[]
 result=copy.deepcopy(bundle);result["image_suites"].append(new);result["status"]="MAKING_SUITE";result["next_user_action"]="新版做好后看一眼最明显的一处";return result
def main():
 p=argparse.ArgumentParser();p.add_argument("bundle",type=Path);p.add_argument("output",type=Path);p.add_argument("--feedback",required=True);a=p.parse_args();r=revise(json.loads(a.bundle.read_text(encoding="utf-8")),a.feedback);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(r["image_suites"][-1]["version_id"]);return 0
if __name__=="__main__":raise SystemExit(main())
