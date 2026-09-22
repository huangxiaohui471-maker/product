#!/usr/bin/env python3
"""Detect visible work that bypassed the flywheel's minimal handoff state."""
from __future__ import annotations

import json
from pathlib import Path


def _files(path: Path, suffixes: set[str]) -> list[str]:
    if not path.is_dir():
        return []
    return [str(item) for item in path.iterdir() if item.is_file() and item.suffix.lower() in suffixes and not item.name.startswith(".")]


def inspect(workspace: Path) -> dict:
    workspace=workspace.expanduser().resolve()
    project=workspace.parent if workspace.name==".content-flywheel" else workspace
    production=_files(project/"04_内容成果",{".md",".html",".png",".jpg",".jpeg",".mp4",".mov"})
    growth=_files(project/"05_复盘成果",{".md",".html",".csv",".json"})
    production_state=any((workspace/name).is_file() for name in ("production_run.json","production_to_growth.json"))
    growth_state=any((workspace/name).is_file() for name in ("content_ledger.json","growth_learning_return.json")) or (workspace/"growth/content_ledger.json").is_file()
    issues=[]
    if production and not production_state:
        issues.append({"code":"UNTRACKED_PRODUCTION","count":len(production),"owner":"production_lead","action":"把已有作品接回当前策略任务，再继续制作或交接"})
    if growth and not growth_state:
        issues.append({"code":"UNTRACKED_GROWTH","count":len(growth),"owner":"growth_lead","action":"把已有复盘接回内容底账，区分事实与推测"})
    return {"ok":not issues,"project":str(project),"workspace":str(workspace),"issues":issues}


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("workspace",type=Path);args=parser.parse_args()
    print(json.dumps(inspect(args.workspace),ensure_ascii=False,indent=2))
