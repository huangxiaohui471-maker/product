#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,threading,webbrowser
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from render_growth_workbench import render

def read(path,default):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError):return default
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(path)

class Handler(SimpleHTTPRequestHandler):
    ledger_path:Path;diagnosis_path:Path;output_path:Path;state_path:Path;task_path:Path;lock=threading.Lock()
    def end_headers(self):self.send_header("Cache-Control","no-store");super().end_headers()
    def refresh(self):self.output_path.write_text(render(read(self.ledger_path,{}),read(self.diagnosis_path,{}),True,read(self.state_path,{})),encoding="utf-8")
    def do_POST(self):
        if self.path!="/api/start-next":self.send_error(404);return
        try:
            size=int(self.headers.get("Content-Length","0"));event=json.loads(self.rfile.read(size))
            if event!={"action":"start_next"}:raise ValueError("invalid action")
            diagnosis=read(self.diagnosis_path,{});ledger=read(self.ledger_path,{});review=diagnosis.get("account_review") or {};plan=review.get("next_week_plan") or [(diagnosis.get("weekly_summary") or {}).get("next_action") or "下一轮只改一处，再看结果。"]
            top=(review.get("top_items") or [{}])[0];source=next((x for x in ledger.get("items") or [] if x.get("content_id")==top.get("content_id")),{})
            task={"schema_version":"growth_to_strategy/v1","status":"ready_for_strategy","direction":plan[0],"steps":plan,"keep":"保留这轮已经有效的部分","change":plan[0],"source_content":{"content_id":source.get("content_id"),"title":source.get("title"),"production_line":source.get("production_line"),"production_recipe":source.get("production_recipe")},"created_at":datetime.now().astimezone().isoformat()}
            state={"schema_version":"growth_action/v1","status":"next_task_ready","task":str(self.task_path),"updated_at":task["created_at"]}
            with self.lock:write(self.task_path,task);write(self.state_path,state);self.refresh()
            body=b'{"ok":true}';self.send_response(200)
        except Exception:body=b'{"ok":false}';self.send_response(400)
        self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

def serve(ledger,diagnosis,output,host,port,open_browser=True):
    project=next((p for p in [output.resolve().parent,*output.resolve().parents] if (p/".content-flywheel").is_dir()),output.resolve().parent)
    Handler.ledger_path=ledger.resolve();Handler.diagnosis_path=diagnosis.resolve();Handler.output_path=output.resolve();Handler.state_path=output.parent/".growth-workbench-state.json";Handler.task_path=project/".content-flywheel/handoffs/growth_to_strategy.json"
    output.parent.mkdir(parents=True,exist_ok=True);Handler.refresh(Handler)
    server=ThreadingHTTPServer((host,port),partial(Handler,directory=str(output.parent)));url=f"http://{host}:{server.server_port}/{output.name}";print(url,flush=True)
    if open_browser:threading.Timer(.25,lambda:webbrowser.open(url)).start()
    server.serve_forever()

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--ledger",required=True);p.add_argument("--diagnosis",required=True);p.add_argument("--output",required=True);p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",type=int,default=0);p.add_argument("--no-open",action="store_true");a=p.parse_args();serve(Path(a.ledger),Path(a.diagnosis),Path(a.output),a.host,a.port,not a.no_open)
