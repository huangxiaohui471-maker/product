#!/usr/bin/env python3
"""Durable handoff between the local page and its host Agent, without fake inference."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from workspace import Workspace, now, read, write, ROOT as workspace_module_root


def inspect(workspace, request_id=None):
    requests = [read(p) for p in sorted((workspace.engine / "requests").glob("*.json"))]
    requests = [r for r in requests if r.get("status") == "queued" and (not request_id or r["id"] == request_id)]
    requests.sort(key=lambda r: (r["kind"] != "context_review", r.get("created_at", "")))
    tasks = []
    for request in requests:
        task = {"request": request, "business": workspace.context(),
                "shared_context": read(workspace.engine / "context/shared_enterprise_context.json")}
        if request.get("material_id"):
            task["material"] = workspace.material(request["material_id"])
            task["evidence_directory"] = str(workspace.engine / "runs" / request["material_id"])
        if request.get("task_id"):
            task["production"] = workspace.production(request["task_id"])
        if request["kind"] in {"growth_data", "growth_review", "next_cycle"}:
            task["ledger"] = read(workspace.engine / "growth/content_ledger.json")
            task["ledger_revision"] = __import__("growth").fingerprint(task["ledger"])
            if request.get("review_id"):
                task["review"] = __import__("growth").get_review(workspace, request["review_id"])
            if request.get("growth_handoff_ref"):
                task["growth_to_strategy"] = read(workspace._inside(workspace.engine / request["growth_handoff_ref"]))
            task["skill_path"] = str(workspace_module_root / "engine" / ("operate-content-growth-lead" if request["kind"] in {"growth_data", "growth_review"} else "operate-content-strategy-lead") / "SKILL.md")
            task["learning"] = read(workspace.engine / "growth/workbench_learning.json")
            if request.get("learning_return_ref"):
                task["growth_learning_return"] = read(workspace._inside(workspace.engine / request["learning_return_ref"]))
        if request.get("attachment"):
            task["attachment_path"] = str(workspace._inside(workspace.engine / request["attachment"]))
        tasks.append(task)
    return tasks


def complete(workspace, request_id, result):
    with workspace.lock:
        request_path = workspace._inside(workspace.engine / "requests" / (request_id + ".json"))
        request = read(request_path)
        if not request:
            raise ValueError("没有这项待办")
        if request.get("status") == "done":
            return request
        if request.get("status") != "queued":
            raise ValueError("这项请求需要重新核对，请承接最新复盘或业务")
        if request.get("context_revision") != workspace.context_revision():
            raise ValueError("业务理解已改变，请根据新业务重新处理，不能提交旧理解下的结果")
        kind = request["kind"]
        if kind == "growth_data":
            outcome = __import__("growth").save_data(workspace, request, result)
        elif kind == "growth_review":
            outcome = __import__("growth").save_review(workspace, request, result)
        elif kind == "next_cycle":
            outcome = __import__("growth").finish_strategy(workspace, request, result)
        elif kind in {"production", "revision"}:
            bundle = workspace.production(request["task_id"])
            existing = next((v for v in bundle.get("workbench_versions", []) if v.get("request_id") == request_id), None)
            if not existing:
                bundle = workspace.save_version({"task_id": request["task_id"], "base_version": result.get("base_version"), "text": result.get("text")})
                bundle["workbench_versions"][-1].update({"author": "agent", "request_id": request_id})
                write(workspace._bundle_path(request["task_id"]), bundle)
                existing = bundle["workbench_versions"][-1]
            outcome = {"version_id": existing["version_id"], "task_id": request["task_id"]}
        else:
            # Machine checks establish that the actual artifacts exist; the Agent
            # still owns semantic judgment. A success message alone is insufficient.
            refs = result.get("output_refs") or []
            if not refs or not result.get("summary"):
                raise ValueError("需要真实结果文件和简短说明，不能只把待办标成完成")
            for ref in refs:
                path = workspace._inside(workspace.engine / ref)
                if not path.is_file():
                    raise ValueError("结果文件不存在")
                if path.suffix == ".json":
                    read(path)  # Reject truncated / invalid JSON.
            if kind == "context_review":
                shared = read(workspace.engine / "context/shared_enterprise_context.json")
                if shared.get("schema_version") != "shared_enterprise_context/v1":
                    raise ValueError("企业共同底稿还没有更新")
                if shared.get("workbench_context_revision") != workspace.context_revision():
                    raise ValueError("共同底稿未对应这次业务更新")
                # Evidence can be reused; suitability must be reconsidered explicitly.
                for material in workspace.materials():
                    if material["adoptable"]:
                        task = read(workspace.engine / "runs" / material["id"] / "experiment.json")
                        if task.get("workbench_context_revision") != workspace.context_revision():
                            raise ValueError("还有旧业务推荐未重新判断或降为待判断")
            outcome = {"output_refs": refs, "summary": result["summary"]}
        request.update({"status": "done", "finished_at": now(), "outcome": outcome})
        write(request_path, request)
        return request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("action", choices=["pending", "complete"])
    parser.add_argument("--request")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    workspace = Workspace(args.project)
    if args.action == "pending":
        result = inspect(workspace, args.request)
    else:
        if not args.request or not args.result:
            parser.error("complete requires --request and --result")
        result = complete(workspace, args.request, read(args.result))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
