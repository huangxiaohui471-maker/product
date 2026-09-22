#!/usr/bin/env python3
"""Run the bundled material ingestion pipeline; semantic review stays with the host Agent."""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from workspace import ROOT, Workspace, read, write, now


def preflight():
    checks = {"python_3_10_plus": sys.version_info >= (3, 10),
              "ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
              "certifi": bool(importlib.util.find_spec("certifi")),
              "pillow": bool(importlib.util.find_spec("PIL"))}
    return {"local_video_ready": all(checks.values()), "checks": checks,
            "online_search": "使用已有 TikHub / 飞瓜授权；本检查不调用外部服务",
            "semantic_review": "由当前 AI 对话读取原片证据、完成拆解和企业适配"}


def ingest(workspace, request_id, source=None, allow_asr=False):
    request_path = workspace._inside(workspace.engine / "requests" / (request_id + ".json"))
    request = read(request_path)
    if not request or request.get("kind") not in {"analysis", "download"}:
        raise ValueError("请选择一个视频接入/拆解请求")
    if request.get("context_revision") != workspace.context_revision():
        raise ValueError("业务理解已改变，请重新接续")
    if request.get("ingest_receipt"):
        # Preserve a completed download/extraction when semantic review resumes.
        return read(workspace.engine / request["ingest_receipt"])
    source = source or str(workspace._inside(workspace.engine / request.get("attachment", "")))
    if not source.startswith(("https://", "http://")) and not Path(source).is_file():
        raise ValueError("缺少视频文件；抖音分享页请先用原连接器解析，不能当视频直链")
    env = dict(os.environ)
    if not allow_asr:
        env["ASR_PROVIDER"] = "none"
    command = [sys.executable, str(ROOT / "engine/operate-content-strategy-lead/scripts/run_pipeline.py"),
               "--workspace", str(workspace.engine), "--source", source, "--analysis", "local"]
    proc = subprocess.run(command, env=env, capture_output=True, text=True, timeout=600)
    if proc.returncode:
        # Detailed native run manifests remain in the project; do not dump configuration or tokens.
        raise ValueError("视频接入未完成。请检查企业配置、依赖或视频有效性；失败记录保留在 runs 中")
    run = Path(proc.stdout.strip().splitlines()[-1]).resolve()
    workspace._inside(run)
    receipt = {"request_id": request_id, "run": str(run.relative_to(workspace.engine)),
               "finished_at": now(), "status": "evidence_ready_review_pending",
               "asr_enabled": allow_asr, "output_refs": [str((run / "experiment.json").relative_to(workspace.engine))]}
    relative = "receipts/ingest-" + request_id + ".json"
    write(workspace.engine / relative, receipt)
    request["ingest_receipt"] = relative
    write(request_path, request)
    return receipt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["check", "ingest"])
    p.add_argument("--project", type=Path)
    p.add_argument("--request")
    p.add_argument("--source")
    p.add_argument("--allow-asr", action="store_true", help="仅在已有外部转写授权下启用")
    args = p.parse_args()
    if args.action == "check":
        result = preflight()
    else:
        if not args.project or not args.request:
            p.error("ingest requires --project and --request")
        result = ingest(Workspace(args.project), args.request, args.source, args.allow_asr)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
