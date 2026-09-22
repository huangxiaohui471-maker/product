#!/usr/bin/env python3
"""Create a source-bound inventory from learner-provided enterprise materials."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json"}


def now() -> str:
    return datetime.now().astimezone().isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def readable_text(path: Path) -> str:
    if path.suffix.lower() == ".json":
        try:
            return json.dumps(json.loads(path.read_text(encoding="utf-8-sig")), ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return ""
    if path.suffix.lower() == ".csv":
        try:
            rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))[:30]
            return "\n".join(" | ".join(row) for row in rows)
        except UnicodeDecodeError:
            return ""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return ""


def scan(source_dir: Path) -> dict:
    items = []
    for index, path in enumerate(sorted(source_dir.rglob("*")), 1):
        if not path.is_file() or path.name.startswith("."):
            continue
        text = readable_text(path) if path.suffix.lower() in TEXT_SUFFIXES else ""
        items.append({
            "source_id": f"src-{index:03d}",
            "source_type": "enterprise_file",
            "locator": path.relative_to(source_dir).as_posix(),
            "observed_at": now(),
            "sha256": sha(path),
            "media_type": path.suffix.lower().lstrip(".") or "binary",
            "size_bytes": path.stat().st_size,
            "extract_status": "text_available" if text.strip() else "needs_agent_or_tool_extraction",
            "preview": " ".join(text.split())[:800],
        })
    return {
        "schema_version": "enterprise_source_inventory/v1",
        "source_root": str(source_dir.resolve()),
        "created_at": now(),
        "items": items,
        "counts": {
            "total": len(items),
            "text_available": sum(item["extract_status"] == "text_available" for item in items),
            "needs_extraction": sum(item["extract_status"] != "text_available" for item in items),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = scan(args.source_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
