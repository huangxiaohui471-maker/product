#!/usr/bin/env python3
from __future__ import annotations

"""Release smoke test: every local script named by SKILL.md must ship."""

import re
import sys
from pathlib import Path


def validate(skill_dir: Path) -> list[str]:
    skill = skill_dir / "SKILL.md"
    if not skill.is_file():
        return ["missing:SKILL.md"]
    referenced = sorted(set(re.findall(r"scripts/[A-Za-z0-9_.-]+\.py", skill.read_text(encoding="utf-8"))))
    errors = [f"missing:{relative}" for relative in referenced if not (skill_dir / relative).is_file()]
    if not referenced:
        errors.append("no_script_references_found")
    return errors


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    failures = validate(root)
    print({"ok": not failures, "errors": failures})
    raise SystemExit(1 if failures else 0)
