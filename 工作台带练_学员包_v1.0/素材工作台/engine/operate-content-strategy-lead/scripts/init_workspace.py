#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import atomic_write_json, now


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--industry", choices=["ecommerce", "education", "local_life", "custom"], default="custom")
    args = parser.parse_args()
    root = Path(args.workspace).expanduser().resolve()
    for folder in ["config", "memory", "runs", "logs"]:
        (root / folder).mkdir(parents=True, exist_ok=True)
    context = root / "config" / "enterprise_context.json"
    if not context.exists():
        atomic_write_json(context, {
            "schema_version": "enterprise_context/v1",
            "context_id": args.name,
            "name": args.name,
            "industry": args.industry,
            "long_term_business": "",
            "business_goal": "",
            "current_priority": "",
            "target_customer": "",
            "products": [],
            "proof_assets": [],
            "claim_boundaries": [],
            "production_capabilities": [],
            "recent_used_directions": [],
            "recent_rejected_directions": [],
            "authorization_scope": {"platforms": [], "public_sources_only": True, "max_downloads_per_run": 5},
            "source": {"kind":"learner_initialization","owner":args.name}, "updated_at": now()
        })
    industry_pack=root/"config/industry_pack.json"
    if not industry_pack.exists():
        chains={"ecommerce":"需求→商品理解→证据→下单","education":"问题识别→信任→方案→咨询/报名","local_life":"附近需求→套餐与环境证据→团购/到店","custom":"需求→证据→行动"}
        atomic_write_json(industry_pack,{"schema_version":"industry_pack/v1","industry":args.industry,"purchase_chain":chains[args.industry],"proof_rule":"只使用企业可核验证据","source":{"kind":"built_in","version":"2026-08-10"},"updated_at":now()})
    platform_pack=root/"config/platform_pack.json"
    if not platform_pack.exists():
        atomic_write_json(platform_pack,{"schema_version":"platform_pack/v1","platforms":["douyin"],"available_signals":["public_content","third_party_ad_library"],"paid_truth_rule":"非官方/授权账户不得声称真实消耗或ROI","source":{"kind":"built_in","version":"2026-08-10"},"updated_at":now()})
    task_pack=root/"config/task_run_pack.json"
    if not task_pack.exists():
        atomic_write_json(task_pack,{"schema_version":"task_run_pack/v1","timezone":"Asia/Shanghai","max_candidates":3,"failure_policy":"explicit_degrade_or_block","output":"dashboard.html","source":{"kind":"system_default","version":"2026-08-10"},"updated_at":now()})
    watch = root / "config" / "watch_universe.json"
    if not watch.exists():
        atomic_write_json(watch, {
            "schema_version": "watch_universe/v1", "seed_accounts": [], "keywords": [], "excluded_accounts": []
        })
    cost_policy=root/"config/cost_policy.json"
    if not cost_policy.exists():
        atomic_write_json(cost_policy,{"schema_version":"cost_policy/v1","mode":"standard","daily_budget_usd":1.5,
            "max_search_per_day":50,"max_detail_per_day":100,"max_downloads_per_run":20,"max_comments_per_day":10,
            "alert_at_ratio":0.8,"principle":"value_first_with_runaway_guard"})
    print(root)


if __name__ == "__main__":
    main()
