#!/usr/bin/env python3
"""Turn one learner-facing business brief into validated context and a starter watch universe."""
from __future__ import annotations

import argparse
import json
import stat
from pathlib import Path
from typing import Any

from common import atomic_write_json, now, read_json
from context import validate_context

REQUIRED = ("name", "industry", "long_term_business", "business_goal", "current_priority", "target_customer")
ACTIVE_WORKSPACE=Path.home()/".config/content-creative-intelligence/active-workspace.json"


def _items(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").replace("，", ",").split(",") if item.strip()]


def _starter_keywords(brief: dict[str, Any]) -> list[str]:
    products = _items(brief.get("products"))
    customer = str(brief.get("target_customer") or "").strip()
    goal = str(brief.get("business_goal") or "").strip()
    industry = brief.get("industry")
    suffixes = {
        "ecommerce": ["测评", "开箱", "优惠", "对比"],
        "education": ["招生", "课程", "报名", "案例"],
        "local_life": ["团购", "到店", "附近", "套餐"],
        "custom": ["广告", "案例", "转化"],
    }.get(industry, ["广告", "案例", "转化"])
    seeds = _items(brief.get("keywords"))
    for product in products[:3]:
        seeds.extend(f"{product} {suffix}" for suffix in suffixes[:3])
    if products and customer:
        seeds.append(f"{products[0]} {customer[:12]}")
    if products and goal:
        seeds.append(f"{products[0]} {goal[:12]}")
    seen, result = set(), []
    for seed in seeds:
        key=" ".join(seed.split())
        if key and key not in seen:
            seen.add(key); result.append(key)
    return result[:12]


def configure(workspace: Path, brief: dict[str, Any], shared_context: dict[str, Any] | None = None) -> dict[str, Any]:
    missing=[key for key in REQUIRED if not str(brief.get(key) or "").strip()]
    if not _items(brief.get("products")): missing.append("products")
    if not _items(brief.get("claim_boundaries")): missing.append("claim_boundaries")
    if not _items(brief.get("production_capabilities")): missing.append("production_capabilities")
    if missing:
        raise ValueError("业务简报缺少："+", ".join(missing))
    if brief.get("industry") not in {"ecommerce","education","local_life","custom"}:
        raise ValueError("industry 必须是 ecommerce/education/local_life/custom")
    context=read_json(workspace/"config/enterprise_context.json",{})
    context.update({
        "schema_version":"enterprise_context/v1",
        "context_id":context.get("context_id") or str(brief["name"]),
        "name":str(brief["name"]), "industry":brief["industry"],
        "long_term_business":str(brief["long_term_business"]),
        "business_goal":str(brief["business_goal"]),
        "current_priority":str(brief["current_priority"]),
        "target_customer":str(brief["target_customer"]),
        "products":_items(brief["products"]),
        "proof_assets":_items(brief.get("proof_assets")),
        "claim_boundaries":_items(brief["claim_boundaries"]),
        "production_capabilities":_items(brief["production_capabilities"]),
        "recent_used_directions":context.get("recent_used_directions",[]),
        "recent_rejected_directions":context.get("recent_rejected_directions",[]),
        "authorization_scope":{
            "platforms":_items(brief.get("platforms")) or ["douyin"],
            "public_sources_only":bool(brief.get("public_sources_only",True)),
            "max_downloads_per_run":int(brief.get("max_downloads_per_run",5)),
        },
        "updated_at":now(),
        "source":{"kind":"shared_enterprise_context_projection/v1" if shared_context else "learner_business_brief/v1","owner":str(brief["name"])},
        "shared_context_ref":({"context_id":shared_context["context_id"],"version":shared_context["version"],"path":"context/shared_enterprise_context.json"} if shared_context else context.get("shared_context_ref")),
    })
    errors=validate_context(context)
    if errors: raise ValueError("；".join(errors))
    watch=read_json(workspace/"config/watch_universe.json",{})
    watch.update({
        "schema_version":"watch_universe/v1",
        "seed_accounts":_items(brief.get("seed_accounts")),
        "keywords":_starter_keywords(brief),
        "excluded_accounts":_items(brief.get("excluded_accounts")),
        "generated_from":"shared_enterprise_context/v1" if shared_context else "learner_business_brief/v1",
        "shared_context_id":shared_context.get("context_id") if shared_context else watch.get("shared_context_id"),
        "updated_at":now(),
    })
    if not watch["keywords"]:
        raise ValueError("无法形成观察关键词，请至少提供产品或一个关键词")
    atomic_write_json(workspace/"config/enterprise_context.json",context)
    atomic_write_json(workspace/"config/watch_universe.json",watch)
    industry_pack=read_json(workspace/"config/industry_pack.json",{});industry_pack.update({"industry":brief["industry"],"updated_at":now()});atomic_write_json(workspace/"config/industry_pack.json",industry_pack)
    platform_pack=read_json(workspace/"config/platform_pack.json",{});platform_pack.update({"platforms":context["authorization_scope"]["platforms"],"updated_at":now()});atomic_write_json(workspace/"config/platform_pack.json",platform_pack)
    # The learner should never have to remember or repeat a workspace path.
    active=ACTIVE_WORKSPACE
    atomic_write_json(active,{"workspace":str(workspace.expanduser().resolve()),"context_id":context["context_id"],"updated_at":now()})
    try:active.chmod(stat.S_IRUSR|stat.S_IWUSR)
    except OSError:pass
    return {"schema_version":"setup_receipt/v1","status":"ready","context":context,"watch_universe":watch}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",required=True)
    parser.add_argument("--brief",required=True,help="learner_business_brief/v1 JSON 文件")
    args=parser.parse_args()
    print(json.dumps(configure(Path(args.workspace),read_json(Path(args.brief),{})),ensure_ascii=False,indent=2))
