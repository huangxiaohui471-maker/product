#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import read_json
from run_pipeline import run
from tikhub_adapter import detail_by_url, media_urls
from cost_ledger import CostLedger


def evidence_seed(candidate: dict, public_detail: dict | None = None) -> dict:
    detail = public_detail or {}
    organic = dict(detail.get("metrics") or candidate.get("organic_metrics") or {})
    return {
        "creative_id": detail.get("creative_id") or candidate["creative_id"],
        "platform": detail.get("platform") or candidate.get("platform") or "unknown",
        "canonical_url": detail.get("canonical_url") or candidate.get("canonical_url") or candidate.get("source_library_url"),
        "author": detail.get("author") or {"display_name": candidate.get("author_name") or candidate.get("advertiser")},
        "published_at": detail.get("published_at"),
        "metrics": organic,
        "organic_metrics": organic,
        "paid_metrics": {},
        "estimated_metrics": dict(candidate.get("estimated_metrics") or {}),
        "paid_evidence": candidate.get("paid_evidence") or {"level": "unknown", "sources": ["unverified_import"]},
        "evidence_class": candidate.get("evidence_class") or "user_supplied_unverified",
        "source_snapshot_path": candidate.get("_source_batch_path"),
        "provenance": {
            "adapter": f"{candidate.get('provider','generic')}_export",
            "adapter_version": "ad-intelligence-export/v1",
            "provider_record_id": candidate.get("provider_record_id"),
            "source_library_url": candidate.get("source_library_url"),
            "media_resolver": "tikhub" if public_detail else "provider_media_url",
        },
    }


def run_candidate(
    workspace: Path,
    candidate: dict,
    analysis_route: str = "local",
) -> Path:
    direct = str(candidate.get("media_url") or "").strip()
    if direct:
        return run(workspace, direct, analysis_route, evidence_seed(candidate))
    canonical = str(candidate.get("canonical_url") or "").strip()
    if candidate.get("platform") != "douyin" or not canonical:
        raise ValueError("该素材没有可下载媒体；当前自动补全仅支持带抖音原作品链接的记录")
    ledger=CostLedger(workspace);policy=ledger.policy()
    ledger.guard("detail",max_daily=int(policy.get("max_detail_per_day",100)),projected_cost=.001,daily_budget=float(policy.get("daily_budget_usd",1.5)))
    detail, raw = detail_by_url(canonical)
    ledger.record("detail",.001,candidate.get("creative_id") or canonical)
    urls = media_urls(raw)
    if not urls:
        raise RuntimeError("广告情报记录已导入，但 TikHub 未返回可下载原片")
    failures = []
    for url in urls[:4]:
        try:
            return run(workspace, url, analysis_route, evidence_seed(candidate, detail))
        except Exception as error:
            failures.append(type(error).__name__)
    raise RuntimeError(f"所有媒体地址均失败：{failures}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--analysis", choices=["auto", "local", "gemini"], default="local")
    args = parser.parse_args()
    batch = read_json(Path(args.batch), {})
    candidates = batch.get("candidates") or []
    if not 0 <= args.index < len(candidates):
        raise SystemExit("候选索引超出范围")
    candidate={**candidates[args.index],"_source_batch_path":str(Path(args.batch).resolve()),"_source_receipt":batch.get("source_receipt")}
    print(run_candidate(Path(args.workspace), candidate, args.analysis))
