#!/usr/bin/env python3
"""Collect only the recent account window, paging backstage and preserving unknowns."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tikhub_account_posts import fetch, normalize


def account_id(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if not value.startswith("http"):
        return value
    query = parse_qs(urlparse(value).query)
    return str((query.get("sec_user_id") or query.get("sec_uid") or [""])[0]).strip()


def next_cursor(payload: dict) -> int | None:
    if isinstance(payload, dict):
        for key in ("max_cursor", "maxCursor", "cursor"):
            value = payload.get(key)
            if isinstance(value, (int, float)) and int(value) > 0:
                return int(value)
        for child in payload.values():
            if isinstance(child, dict):
                found = next_cursor(child)
                if found:
                    return found
    return None


def collect(sec_user_id: str, days: int = 7, max_pages: int = 5, now: datetime | None = None, fetcher=fetch) -> dict:
    now = now or datetime.now().astimezone()
    cutoff = now - timedelta(days=max(1, days))
    cursor = 0
    items: list[dict] = []
    seen: set[str] = set()
    pages = 0
    while pages < max_pages:
        payload = fetcher(sec_user_id, cursor=cursor, count=20)
        pages += 1
        batch = normalize(payload)
        rows = batch.get("items") or []
        oldest = None
        for row in rows:
            try:
                published = datetime.fromisoformat(str(row.get("published_at") or "").replace("Z", "+00:00"))
                published = published.astimezone(now.tzinfo)
            except Exception:
                continue
            oldest = published if oldest is None or published < oldest else oldest
            if published >= cutoff and row["content_id"] not in seen:
                seen.add(row["content_id"])
                items.append(row)
        cursor_next = next_cursor(payload)
        if not rows or not cursor_next or cursor_next == cursor or (oldest and oldest < cutoff):
            break
        cursor = cursor_next
    items.sort(key=lambda row: row.get("published_at") or "", reverse=True)
    return {"schema_version": "content_ledger_import/v1", "connector": "tikhub/douyin-account-posts", "window_days": days, "cutoff": cutoff.isoformat(), "pages_fetched": pages, "items": items, "raw_count": len(items), "normalized_count": len(items)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True, help="sec_user_id or URL containing sec_user_id")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    sid = account_id(args.account)
    if not sid:
        raise ValueError("还没认出这个账号；请把企业抖音主页链接发给我")
    result = collect(sid, days=args.days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(result["items"]), "days": args.days, "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

