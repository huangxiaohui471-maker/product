from __future__ import annotations

from pathlib import Path
from typing import Any

from common import now, stable_id

def _bigrams(value:str)->set[str]:
    clean="".join(ch for ch in value.lower() if ch.isalnum())
    return {clean[i:i+2] for i in range(max(0,len(clean)-1))}

def _context_fit(analysis:dict[str,Any],context:dict[str,Any])->float:
    interpretations=analysis.get("interpretations") or {}
    source=" ".join(str(interpretations.get(k) or "") for k in ("target_situation","customer_tension","action_answer","offer","production_pattern"))
    target=" ".join([str(context.get("target_customer") or ""),str(context.get("business_goal") or ""),str(context.get("current_priority") or ""),*map(str,context.get("products") or [])])
    a,b=_bigrams(source),_bigrams(target)
    return round(len(a&b)/max(1,min(len(a),len(b))),3) if a and b else 0.0


def score_candidate(evidence: dict[str, Any], analysis: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Transparent baseline ranker; unknown metrics are not silently converted to zero."""
    metrics = evidence.get("metrics") or {}
    available = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
    evidence_level = (evidence.get("paid_evidence") or {}).get("level", "unknown")
    evidence_weight = {"verified_paid": 1.0, "strong_signal": .8, "weak_signal": .55, "unknown": .25}.get(evidence_level, .25)
    completeness = sum(bool(v) for v in (analysis.get("interpretations") or {}).values()) / 10
    context_fit=_context_fit(analysis,context)
    return {"creative_id": evidence["creative_id"], "evidence_strength": evidence_weight,
            "analysis_completeness": round(min(completeness, 1), 3), "context_fit":context_fit,"metrics_available": sorted(available),
            "reference_score": round(.35 * evidence_weight + .25 * min(completeness, 1)+.4*context_fit, 3),
            "warning": None if evidence_level in {"verified_paid", "strong_signal"} else "仅为效果型素材候选，不代表真实投放效果"}


def propose(evidence: dict[str, Any], analysis: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    i = analysis.get("interpretations") or {}; score = score_candidate(evidence, analysis, context)
    mechanism = i.get("opening_hook") or "开场信息组织方式"
    exp_id = stable_id(context.get("context_id"), evidence["creative_id"], mechanism)[:24]
    return {"schema_version": "experiment_task/v1", "experiment_id": exp_id,
        "enterprise_context_id": context.get("context_id"), "created_at": now(),
        "business_goal": context.get("business_goal", ""), "target_customer": context.get("target_customer", ""),
        "customer_situation": i.get("target_situation", ""),
        "hypothesis": f"借用“{mechanism}”这一机制，可能提升目标用户继续观看并理解行动答案的概率。",
        "why_now": f"候选参考分 {score['reference_score']}；{score.get('warning') or '证据较强'}",
        "evidence_creative_ids": [evidence["creative_id"]], "borrow_mechanism": mechanism,
        "context_fit_reason": "系统会结合企业白皮书判断这条素材能否迁移；热度只作为辅助信号。",
        "do_not_copy": ["原文案", "原人物身份", "原品牌资产", "未经证实的效果承诺"],
        "claim_boundaries": context.get("claim_boundaries", []),
        "single_variable": {"name": "opening_hook", "from": "当前开场", "to": mechanism},
        "constants": ["产品", "受众", "核心承诺", "投放设置"], "required_assets": [],
        "draft_brief": "建议先把这个开场机制换成你的真实业务信息，直接做出第一版内容。",
        "future_success_signals": ["3秒留存", "完播率", "点击率", "转化成本"],
        "decision": "pending", "decision_reason": None, "scorecard": score}
