#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from common import read_json,read_jsonl
from memory_store import MemoryStore
from render_dashboard import render


REQUIRED = {"schema_version", "event_id", "experiment_id", "decision", "reason", "decided_by", "decided_at", "cooldown_until"}


class DashboardHandler(SimpleHTTPRequestHandler):
    workspace: Path
    render_lock = threading.Lock()

    def _task(self,experiment_id:str)->dict:
        for path in self.workspace.joinpath("runs").glob("*/experiment.json"):
            task=read_json(path,{})
            if task.get("experiment_id")==experiment_id:return task
        return {}

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/decisions":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            event = json.loads(self.rfile.read(length))
            if REQUIRED - set(event) or event.get("schema_version") != "decision_event/v1" or event.get("decision") not in {"adopt", "hold", "reject"}:
                raise ValueError("invalid decision event")
            task=self._task(event["experiment_id"])
            if not task:raise ValueError("unknown experiment")
            store = MemoryStore(self.workspace)
            existing = {row.get("event_id") for row in read_jsonl(store.decisions_path)}
            if event["event_id"] not in existing:
                store.add_decision(event)
            # The dashboard is a static artifact, so durable state must be
            # rendered before the browser reloads it. atomic_write_text keeps
            # concurrent readers from observing a partial page.
            with self.render_lock:
                render(self.workspace, self.workspace / "dashboard.html")
            body = b'{"ok":true}'
            self.send_response(200)
        except Exception:
            body = b'{"ok":false}'
            self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(workspace: Path, host: str, port: int, open_browser: bool = True) -> None:
    workspace = workspace.resolve()
    DashboardHandler.workspace = workspace
    handler = partial(DashboardHandler, directory=str(workspace))
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{server.server_port}/dashboard.html"
    print(url, flush=True)
    if open_browser:
        threading.Timer(.25, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    serve(Path(args.workspace), args.host, args.port, not args.no_open)
