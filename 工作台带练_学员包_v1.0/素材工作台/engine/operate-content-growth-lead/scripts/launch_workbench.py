#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,socket,subprocess,sys,time,urllib.request,webbrowser
from pathlib import Path
def alive(url):
    try:return urllib.request.urlopen(url,timeout=.5).status==200
    except Exception:return False
def launch(ledger,diagnosis,output,open_browser=True):
    output=output.resolve();state=output.parent/".growth-workbench-server.json"
    try:old=json.loads(state.read_text(encoding="utf-8"))
    except Exception:old={}
    url=str(old.get("url") or "")
    if not url or not alive(url):
        with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
        url=f"http://127.0.0.1:{port}/{output.name}";proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name("serve_workbench.py")),"--ledger",str(ledger.resolve()),"--diagnosis",str(diagnosis.resolve()),"--output",str(output),"--port",str(port),"--no-open"],cwd=str(Path(__file__).parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        for _ in range(50):
            if alive(url):break
            if proc.poll() is not None:raise RuntimeError("内容复盘工作台未能启动")
            time.sleep(.1)
        if not alive(url):raise RuntimeError("内容复盘工作台启动超时")
        state.write_text(json.dumps({"url":url,"pid":proc.pid},ensure_ascii=False),encoding="utf-8")
    if open_browser:webbrowser.open(url)
    return {"ready":True,"interactive":True,"url":url}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--ledger",required=True);p.add_argument("--diagnosis",required=True);p.add_argument("--output",required=True);p.add_argument("--no-open",action="store_true");a=p.parse_args();print(json.dumps(launch(Path(a.ledger),Path(a.diagnosis),Path(a.output),not a.no_open),ensure_ascii=False))
