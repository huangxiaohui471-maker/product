from __future__ import annotations
from typing import Any

REQUIRED_TEXT=("context_id","name","long_term_business","business_goal","current_priority","target_customer")
REQUIRED_LIST=("products","claim_boundaries","production_capabilities")

def validate_context(context: dict[str,Any]) -> list[str]:
    errors=[]
    if context.get("schema_version")!="enterprise_context/v1": errors.append("schema_version 必须为 enterprise_context/v1")
    errors += [f"{key} 未填写" for key in REQUIRED_TEXT if not str(context.get(key) or "").strip()]
    errors += [f"{key} 至少需要一项" for key in REQUIRED_LIST if not isinstance(context.get(key),list) or not context.get(key)]
    scope=context.get("authorization_scope")
    if not isinstance(scope,dict) or not isinstance(scope.get("platforms"),list) or not scope.get("platforms"): errors.append("authorization_scope.platforms 未配置")
    else:
        limit=scope.get("max_downloads_per_run")
        if not isinstance(limit,int) or not 1<=limit<=100:errors.append("authorization_scope.max_downloads_per_run 必须为 1–100")
    if context.get("industry") not in {"ecommerce","education","local_life","custom"}:errors.append("industry 无效")
    if not isinstance(context.get("source"),dict) or not context["source"].get("kind"):errors.append("企业上下文缺少可追溯来源")
    if not str(context.get("updated_at") or "").strip():errors.append("企业上下文缺少更新时间")
    return errors
