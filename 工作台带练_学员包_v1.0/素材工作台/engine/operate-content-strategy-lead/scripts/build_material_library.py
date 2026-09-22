#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


def now() -> str:
    return datetime.now().astimezone().isoformat()


def words(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in re.split(r"[,，、;；|\n]", str(value or "")) if part.strip()]


def fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", "", text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def build(payload: dict, context: dict | None = None) -> dict:
    context = context or {}
    seen: set[str] = set()
    items: list[dict] = []
    duplicate_count = 0
    for index, raw in enumerate(payload.get("items") or []):
        transcript = str(raw.get("transcript") or raw.get("text") or raw.get("title") or "").strip()
        fp = fingerprint(transcript or str(raw.get("source_url") or index))
        if fp in seen:
            duplicate_count += 1
            continue
        seen.add(fp)
        tags = {
            "customer": words(raw.get("customer_tags")),
            "product": words(raw.get("product_tags")),
            "problem": words(raw.get("problem_tags")),
            "scene": words(raw.get("scene_tags")),
            "platform": words(raw.get("platform") or payload.get("platform")),
            "goal": words(raw.get("goal_tags")),
        }
        mechanisms = {
            "opening": str(raw.get("opening") or "").strip(),
            "structure": words(raw.get("structure")),
            "evidence": words(raw.get("evidence")),
            "visual": words(raw.get("visual")),
            "expression": words(raw.get("expression")),
        }
        item_id = str(raw.get("material_id") or raw.get("creative_id") or f"material-{fp}")
        usable = bool(transcript and raw.get("source_url") and any(tags.values()))
        items.append({
            "material_id": item_id,
            "source": {
                "url": raw.get("source_url"),
                "author": raw.get("author"),
                "published_at": raw.get("published_at"),
                "collected_at": raw.get("collected_at") or now(),
                "source_class": raw.get("source_class") or payload.get("source_class") or "public_candidate",
            },
            "original": {"title": raw.get("title"), "transcript": transcript, "media_path": raw.get("media_path")},
            "breakdown": mechanisms,
            "tags": tags,
            "enterprise_fit": {
                "context_id": context.get("context_id"),
                "why_relevant": raw.get("why_relevant") or "等待结合企业底稿判断",
                "can_borrow": words(raw.get("can_borrow")),
                "must_not_copy": words(raw.get("must_not_copy")),
            },
            "status": "ready_to_call" if usable else "needs_review",
            "search_text": " ".join([
                transcript,
                *sum(tags.values(), []),
                mechanisms["opening"],
                *mechanisms["structure"],
                *mechanisms["evidence"],
                *mechanisms["visual"],
                *mechanisms["expression"],
                *words(raw.get("can_borrow")),
                str(raw.get("why_relevant") or ""),
            ]).strip(),
            "fingerprint": fp,
        })
    return {
        "schema_version": "content_material_library/v1",
        "library_id": payload.get("library_id") or f"library-{fingerprint(str(context.get('context_id') or 'default'))}",
        "context_id": context.get("context_id"),
        "updated_at": now(),
        "source_count": len(payload.get("items") or []),
        "material_count": len(items),
        "duplicate_count": duplicate_count,
        "items": items,
    }


def read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def pipeline_payload(workspace: Path) -> dict:
    """Adapt existing pipeline artifacts; do not create a second analysis path."""
    rows = []
    for analysis_path in sorted((workspace / "runs").glob("*/analysis/analysis.json")):
        run = analysis_path.parent.parent
        analysis = read(analysis_path)
        evidence = read(run / "creative/evidence.json")
        experiment = read(run / "experiment.json")
        whitebox = analysis.get("whitebox_analysis") or {}
        transfer = whitebox.get("transfer_reasoning") if isinstance(whitebox.get("transfer_reasoning"), dict) else {}
        transcript = " ".join(
            str(item.get("text") or "").strip()
            for item in ((analysis.get("observations") or {}).get("transcript") or [])
            if isinstance(item, dict) and item.get("text")
        )
        interp = analysis.get("interpretations") or {}
        media = evidence.get("media") or {}
        paid = evidence.get("paid_evidence") or {}
        rows.append({
            "creative_id": analysis.get("creative_id") or evidence.get("creative_id"),
            "source_url": evidence.get("canonical_url"),
            "author": (evidence.get("author") or {}).get("display_name") if isinstance(evidence.get("author"), dict) else evidence.get("author"),
            "published_at": evidence.get("published_at"),
            "collected_at": evidence.get("collected_at"),
            "source_class": "paid_signal" if paid else "organic_or_unknown",
            "title": evidence.get("title"),
            "transcript": transcript,
            "media_path": media.get("local_path"),
            "customer_tags": experiment.get("target_customer"),
            "product_tags": experiment.get("product_tags"),
            "problem_tags": interp.get("customer_tension"),
            "scene_tags": experiment.get("customer_situation") or interp.get("target_situation"),
            "platform": evidence.get("platform"),
            "goal_tags": experiment.get("business_goal"),
            "opening": interp.get("opening_hook"),
            "structure": interp.get("narrative_structure"),
            "evidence": interp.get("proof_devices"),
            "visual": interp.get("production_pattern"),
            "expression": [interp.get("offer"), interp.get("cta")],
            "why_relevant": experiment.get("context_fit_reason"),
            "can_borrow": transfer.get("keep") or experiment.get("borrow_mechanism"),
            "must_not_copy": transfer.get("replace") or experiment.get("do_not_copy"),
        })
    return {"platform": "mixed", "source_class": "pipeline_artifact", "items": rows}


def search(library: dict, query: str) -> list[dict]:
    tokens = [item.lower() for item in re.split(r"\s+", query.strip()) if item]
    return [row for row in library.get("items") or [] if not tokens or all(token in str(row.get("search_text") or "").lower() for token in tokens)]


def main() -> int:
    parser = argparse.ArgumentParser(description="把抓回的原料整理成可搜索、可调用的素材库")
    parser.add_argument("input", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--context", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--query")
    args = parser.parse_args()
    if args.workspace:
        context = read(args.workspace / "context/shared_enterprise_context.json")
        payload = pipeline_payload(args.workspace)
        output = args.output or args.workspace / "materials/material_library.json"
    else:
        if not args.input or not args.output:
            parser.error("提供 input output，或使用 --workspace")
        context = read(args.context) if args.context else {}
        payload = read(args.input)
        output = args.output
    result = build(payload, context)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    response = search(result, args.query) if args.query is not None else {"material_count": result["material_count"], "duplicate_count": result["duplicate_count"], "output": str(output)}
    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
