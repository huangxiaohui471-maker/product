#!/usr/bin/env python3
"""Serve the local dashboard and synchronize browser localStorage over SSE.

Usage:
    python3 sync_server.py --port 8767

Open the editor at /?sync=atlas&role=editor and share /?sync=atlas&role=viewer.
This is intentionally dependency-free for local demos. Put it behind HTTPS and
add authentication before using it with confidential data.
"""

import argparse
import json
import mimetypes
import os
import queue
import threading
import time
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(ROOT, ".sync-data")
ROOMS = {}
ROOMS_LOCK = threading.RLock()


def room_path(room):
    safe = "".join(ch for ch in room if ch.isalnum() or ch in "-_")[:80] or "default"
    return os.path.join(STATE_DIR, safe + ".json")


def load_room(room):
    with ROOMS_LOCK:
        if room in ROOMS:
            return ROOMS[room]
        state = {"revision": 0, "data": {}, "updatedAt": None, "clients": []}
        try:
            with open(room_path(room), "r", encoding="utf-8") as handle:
                saved = json.load(handle)
                state.update({k: saved.get(k) for k in ("revision", "data", "updatedAt")})
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        state["clients"] = []
        ROOMS[room] = state
        return state


def save_room(room, state):
    os.makedirs(STATE_DIR, exist_ok=True)
    temp = room_path(room) + ".tmp"
    payload = {k: state[k] for k in ("revision", "data", "updatedAt")}
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    os.replace(temp, room_path(room))


class SyncHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        room = query.get("room", ["default"])[0]
        if parsed.path == "/api/state":
            state = load_room(room)
            self.send_json({k: state[k] for k in ("revision", "data", "updatedAt")})
            return
        if parsed.path == "/api/events":
            self.handle_events(room)
            return
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "local-dashboard-sync"})
            return
        if parsed.path == "/" or parsed.path == "/index.html":
            # Keep the requested share URL intact while serving the existing entry page.
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path != "/api/state":
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        room = query.get("room", ["default"])[0]
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ValueError("data must be an object")
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json({"error": "invalid payload"}, HTTPStatus.BAD_REQUEST)
            return
        with ROOMS_LOCK:
            state = load_room(room)
            state["revision"] += 1
            state["data"] = data
            state["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            save_room(room, state)
            event = json.dumps({"revision": state["revision"], "data": data, "updatedAt": state["updatedAt"]}, ensure_ascii=False)
            clients = list(state["clients"])
        for client in clients:
            try:
                client.put_nowait(event)
            except queue.Full:
                pass
        self.send_json({"ok": True, "revision": state["revision"]})

    def handle_events(self, room):
        client = queue.Queue(maxsize=10)
        state = load_room(room)
        with ROOMS_LOCK:
            state["clients"].append(client)
            initial = {k: state[k] for k in ("revision", "data", "updatedAt")}
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(("data: %s\n\n" % json.dumps(initial, ensure_ascii=False)).encode("utf-8"))
            self.wfile.flush()
            while True:
                try:
                    event = client.get(timeout=20)
                    self.wfile.write(("data: %s\n\n" % event).encode("utf-8"))
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with ROOMS_LOCK:
                if client in state["clients"]:
                    state["clients"].remove(client)


def main():
    parser = argparse.ArgumentParser(description="Local HTML dashboard sync server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8767")))
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    args = parser.parse_args()
    os.chdir(ROOT)
    server = ThreadingHTTPServer((args.host, args.port), SyncHandler)
    print("Dashboard: http://127.0.0.1:%d/?sync=atlas&role=editor" % args.port)
    print("Share:    http://127.0.0.1:%d/?sync=atlas&role=viewer" % args.port)
    print("Data:     %s" % STATE_DIR)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
