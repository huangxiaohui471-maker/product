#!/usr/bin/env python3
"""Open the department home after making the current specialist workbench live."""
from __future__ import annotations
import argparse,json,subprocess,sys,webbrowser
from pathlib import Path
from render_department_home import project_view,render

def call(script:Path,args:list[str])->dict:
    result=subprocess.run([sys.executable,str(script),*args,"--no-open"],cwd=str(script.parent),check=True,capture_output=True,text=True)
    return json.loads(result.stdout.strip().splitlines()[-1])

def launch(project:Path,open_browser=True)->dict:
    project=project.resolve();engine=project/".content-flywheel";view=project_view(engine);skills=Path(__file__).resolve().parents[2]
    if "打开策略" in view["action"] or "继续找今天" in view["action"]:
        result=call(skills/"operate-content-strategy-lead/scripts/launch_dashboard.py",["--workspace",str(engine)])
    elif "生产" in view["action"]:
        runs=sorted((engine/"handoffs").glob("production_run_*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
        if not runs:raise RuntimeError("还没有可以打开的内容生产任务")
        result=call(skills/"operate-content-production-lead/scripts/launch_workbench.py",["--bundle",str(runs[0]),"--output",str(project/"04_内容成果/内容生产工作台.html")])
    elif "复盘" in view["action"]:
        result=call(skills/"operate-content-growth-lead/scripts/launch_workbench.py",["--ledger",str(engine/"growth/content_ledger.json"),"--diagnosis",str(engine/"growth/diagnosis.json"),"--output",str(project/"05_复盘成果/复盘工作台.html")])
    else:result={}
    if result.get("url"):view["href"]=result["url"]
    output=project/"内容飞轮驾驶舱.html";output.write_text(render(view),encoding="utf-8")
    if open_browser:webbrowser.open(output.as_uri())
    return {"ready":True,"home":str(output),"current_workbench":result.get("url")}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--project",required=True);p.add_argument("--no-open",action="store_true");a=p.parse_args();print(json.dumps(launch(Path(a.project),not a.no_open),ensure_ascii=False))
