#!/usr/bin/env python3
"""Open the interactive dashboard without blocking the agent process."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from common import atomic_write_json, read_json
from render_dashboard import render


def alive(url: str) -> bool:
    try:
        return urllib.request.urlopen(url, timeout=.5).status == 200
    except Exception:
        return False


def launch(workspace: Path, open_browser: bool = True) -> dict:
    workspace=workspace.expanduser().resolve();workspace.mkdir(parents=True,exist_ok=True)
    dashboard=workspace/"dashboard.html";render(workspace,dashboard)
    state_path=workspace/"dashboard-server.json";old=read_json(state_path,{})
    url=str(old.get("url") or "")
    if not url or not alive(url):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
        url=f"http://127.0.0.1:{port}/dashboard.html"
        process=subprocess.Popen(
            [sys.executable,str(Path(__file__).with_name("serve_dashboard.py")),"--workspace",str(workspace),"--port",str(port),"--no-open"],
            cwd=str(Path(__file__).parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,
        )
        for _ in range(40):
            if alive(url):break
            if process.poll() is not None:raise RuntimeError("看板服务未能启动")
            time.sleep(.1)
        if not alive(url):raise RuntimeError("看板服务启动超时")
        atomic_write_json(state_path,{"schema_version":"dashboard_server/v1","pid":process.pid,"url":url,"dashboard":str(dashboard)})
    if open_browser:webbrowser.open(url)
    return {"schema_version":"dashboard_launch/v1","ready":True,"url":url,"interactive":True}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--workspace",required=True);parser.add_argument("--no-open",action="store_true");args=parser.parse_args()
    print(json.dumps(launch(Path(args.workspace),not args.no_open),ensure_ascii=False))
