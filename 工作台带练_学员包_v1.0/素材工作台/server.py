#!/usr/bin/env python3
"""Local, single-project workbench. No secrets or models embedded in the page."""
from __future__ import annotations
import argparse
import json
import mimetypes
import secrets
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from workspace import ROOT, Workspace, read, write


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, workspace, port=0):
        super().__init__(("127.0.0.1", port), Handler)
        self.workspace = workspace
        self.session_token = secrets.token_urlsafe(32)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, mime="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def host_ok(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"error": "请从本机启动链接打开"})
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/state":
                return self.send(200, self.server.workspace.overview())
            if parsed.path == "/api/health":
                return self.send(200, {"ok": True})
            if parsed.path == "/media":
                relative = parse_qs(parsed.query).get("path", [""])[0]
                file = self.server.workspace._inside(self.server.workspace.engine / relative)
                if file.suffix.lower() not in {".mp4", ".webm", ".jpg", ".jpeg", ".png", ".wav", ".mp3"} or not file.is_file():
                    return self.send(404, {"error": "素材文件暂时不可用"})
                return self.media(file)
            if parsed.path == "/":
                page = (ROOT / "web/index.html").read_text().replace("__SESSION_TOKEN__", self.server.session_token)
                return self.send(200, page, "text/html; charset=utf-8")
            if parsed.path in {"/app.js", "/style.css"}:
                file = ROOT / "web" / parsed.path[1:]
                return self.send(200, file.read_bytes(), "text/javascript; charset=utf-8" if file.suffix == ".js" else "text/css; charset=utf-8")
            return self.send(404, {"error": "没有这个页面"})
        except (BrokenPipeError, ConnectionResetError):
            return  # Browser stopped media playback or changed the current page.
        except (OSError, ValueError):
            return self.send(400, {"error": "读取失败，请检查项目文件后重新打开"})

    def media(self, file):
        size = file.stat().st_size
        start, end = 0, size - 1
        range_header = self.headers.get("Range", "")
        if range_header:
            try:
                spec = range_header.removeprefix("bytes=")
                first, last = spec.split("-", 1)
                if first:
                    start = int(first); end = min(int(last), size - 1) if last else size - 1
                else:
                    start = max(0, size - int(last))
                if start > end or start < 0:
                    raise ValueError()
            except ValueError:
                return self.send(416, b"")
        self.send_response(206 if range_header else 200)
        self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if range_header:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with file.open("rb") as stream:
            stream.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = stream.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk); remaining -= len(chunk)

    def do_POST(self):
        if not self.host_ok() or self.headers.get("X-Workbench-Token") != self.server.session_token:
            return self.send(403, {"error": "页面已失效，请刷新后重试"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.path in {"/api/upload", "/api/growth-upload"}:
                if not 0 < length <= 250 * 1024 * 1024:
                    raise ValueError("视频需小于 250 MB")
                name = Path(unquote(self.headers.get("X-File-Name", "video.mp4"))).name
                is_growth = self.path == "/api/growth-upload"
                allowed_files = {".csv", ".xlsx", ".json", ".txt", ".md", ".png", ".jpg", ".jpeg", ".pdf"} if is_growth else {".mp4", ".mov", ".webm", ".m4v"}
                if Path(name).suffix.lower() not in allowed_files:
                    raise ValueError("请选择支持的数据表、文档、截图或视频")
                workspace = self.server.workspace
                relative = "uploads/" + uuid.uuid4().hex + Path(name).suffix.lower()
                target = workspace.engine / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                temp = target.with_suffix(".part")
                try:
                    with temp.open("wb") as stream:
                        remaining = length
                        while remaining:
                            chunk = self.rfile.read(min(1024 * 1024, remaining))
                            if not chunk:
                                raise ValueError("视频传输中断，请重新添加")
                            stream.write(chunk); remaining -= len(chunk)
                    temp.replace(target)
                finally:
                    temp.unlink(missing_ok=True)
                if is_growth:
                    importer = __import__("growth")
                    request = importer.request_data(workspace, "整理这份内容数据并保留来源：" + name) if self.headers.get("X-Import-Only") == "true" else importer.request_review(workspace, "根据这份资料分析内容表现：" + name)
                else:
                    request = workspace.request("analysis", "接入并拆解我上传的视频：" + name)
                extra = unquote(self.headers.get("X-Review-Message", ""))
                if is_growth and extra:
                    request["message"] += "；用户说明：" + extra[:4000]
                request.update({"attachment": relative, "original_filename": name})
                write(workspace.engine / "requests" / (request["id"] + ".json"), request)
                return self.send(200, {"ok": True, "result": request})
            if not 0 < length <= 2_000_000:
                raise ValueError("提交内容过大或为空")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("提交内容无效")
            workspace = self.server.workspace
            if self.path == "/api/business":
                result = workspace.set_business(body)
            elif self.path == "/api/start":
                result = workspace.start_content(body.get("material_id"))
            elif self.path == "/api/version":
                result = workspace.save_version(body)
            elif self.path == "/api/adopt":
                result = workspace.adopt_version(body)
            elif self.path == "/api/result":
                result = workspace.record_result(body)
            elif self.path == "/api/learn":
                result = workspace.learn(body)
            elif self.path == "/api/growth-data":
                result = __import__("growth").request_data(workspace, body.get("message"))
            elif self.path == "/api/growth-review":
                result = __import__("growth").request_review(workspace, body.get("message"), body.get("review_id"))
            elif self.path == "/api/growth-next":
                result = __import__("growth").start_next(workspace, body.get("review_id"), body.get("plan_id"))
            elif self.path == "/api/request":
                allowed = {"search", "download", "analysis", "revision", "production"}
                if body.get("kind") not in allowed:
                    raise ValueError("这个动作尚未接通")
                result = workspace.request(body["kind"], body.get("message"), body.get("material_id"), body.get("task_id"))
            else:
                return self.send(404, {"error": "没有这个操作"})
            return self.send(200, {"ok": True, "result": result})
        except ValueError as error:
            return self.send(400, {"error": str(error)})
        except Exception:
            return self.send(500, {"error": "未能保存，请保留输入并重试；原有记录没有被主动删除"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=ROOT / "我的业务")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    server = Server(Workspace(args.project), args.port)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(json.dumps({"url": url, "project": str(args.project.resolve())}, ensure_ascii=False), flush=True)
    if not args.no_open:
        webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
