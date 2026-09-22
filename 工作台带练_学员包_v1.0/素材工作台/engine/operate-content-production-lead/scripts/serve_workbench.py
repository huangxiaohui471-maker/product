#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, threading, webbrowser
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from render_production_workbench import render


def read(path: Path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(path)


class Handler(SimpleHTTPRequestHandler):
    bundle_path: Path; output_path: Path; state_path: Path; lock=threading.Lock()

    def end_headers(self): self.send_header("Cache-Control","no-store");super().end_headers()

    def refresh(self):
        bundle=read(self.bundle_path,{})
        artifact=bundle.get("current_artifact") or bundle.get("adopted_artifact") or {}
        path=Path(artifact.get("path") or artifact.get("locator") or "")
        if path and not path.is_absolute(): path=self.output_path.parent/path.name
        source=path.read_text(encoding="utf-8") if path.is_file() else ""
        self.output_path.write_text(render(bundle,source,True,read(self.state_path,{})),encoding="utf-8")

    def do_POST(self):
        if self.path!="/api/advance": self.send_error(404);return
        try:
            length=int(self.headers.get("Content-Length","0"));event=json.loads(self.rfile.read(length))
            action=event.get("action")
            if action != "ready_for_shooting" or set(event)!={"action"}: raise ValueError("invalid action")
            bundle=read(self.bundle_path,{})
            selected_ref=bundle.get("selected_script");selected_id=selected_ref.get("candidate_id") if isinstance(selected_ref,dict) else selected_ref
            selected=next((x for x in bundle.get("script_candidates") or [] if x.get("candidate_id")==selected_id),{})
            checks=selected.get("claim_checks") or []
            if action=="ready_for_shooting" and checks: raise ValueError("claims still need correction")
            artifact=bundle.get("current_artifact") or bundle.get("adopted_artifact") or {}
            state={"schema_version":"production_action/v1","status":"ready_for_shooting","task_id":bundle.get("task_id"),"artifact":artifact.get("path") or artifact.get("locator"),"artifact_id":artifact.get("artifact_id"),"version_id":artifact.get("version_id"),"production_line":bundle.get("production_line"),"production_recipe":bundle.get("production_recipe"),"updated_at":datetime.now().astimezone().isoformat()}
            with self.lock: write(self.state_path,state);self.refresh()
            body=b'{"ok":true}';self.send_response(200)
        except Exception:
            body=b'{"ok":false}';self.send_response(400)
        self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)


def serve(bundle: Path, output: Path, host: str, port: int, open_browser=True):
    Handler.bundle_path=bundle.resolve();Handler.output_path=output.resolve();Handler.state_path=output.parent/".production-workbench-state.json"
    output.parent.mkdir(parents=True,exist_ok=True);Handler.refresh(Handler)
    server=ThreadingHTTPServer((host,port),partial(Handler,directory=str(output.parent)))
    url=f"http://{host}:{server.server_port}/{output.name}";print(url,flush=True)
    if open_browser: threading.Timer(.25,lambda:webbrowser.open(url)).start()
    server.serve_forever()


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--bundle",required=True);p.add_argument("--output",required=True);p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",type=int,default=0);p.add_argument("--no-open",action="store_true");a=p.parse_args();serve(Path(a.bundle),Path(a.output),a.host,a.port,not a.no_open)
