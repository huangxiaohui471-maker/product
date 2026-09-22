#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json, read_json

def migrate(workspace: Path) -> int:
    changed = 0
    for path in workspace.glob("runs/*/creative/evidence.json"):
        evidence = read_json(path, {})
        adapter = (evidence.get("provenance") or {}).get("adapter", "manual")
        desired = "public_content_only" if adapter == "tikhub" else "user_supplied_unverified"
        if evidence.get("evidence_class") != desired:
            evidence["evidence_class"] = desired
            changed += 1
        evidence.setdefault("organic_metrics", dict(evidence.get("metrics") or {}))
        evidence.setdefault("paid_metrics", {})
        evidence.setdefault("estimated_metrics", {})
        atomic_write_json(path, evidence)
    return changed

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    print(migrate(Path(args.workspace)))
