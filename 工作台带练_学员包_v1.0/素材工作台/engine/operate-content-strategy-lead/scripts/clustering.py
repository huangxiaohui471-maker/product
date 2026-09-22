from __future__ import annotations
import re
from typing import Any
from common import now, stable_id

_MECHANISM_PHRASES=(
    (r"先(?:展示|给出|亮出|告诉)(?:最终)?(?:结果|成果|答案)","结果前置"),
    (r"(?:结果|成果|答案)(?:先讲|先说|先给|前置)","结果前置"),
    (r"(?:过程|步骤|现场)(?:作为)?(?:佐证|验证|证明|证据)","过程证明"),
)
_MECHANISM_WORDS=(
    (r"成果|答案","结果"),(r"前置|先讲|先说|先给","前置"),
    (r"佐证|验证|证据","证明"),(r"痛点|困扰|难题","问题"),
    (r"开头|起手|起始","开场"),(r"转化|下单|咨询","行动"),
    (r"反差","反差"),(r"对比","对比"),
)

def normalize_mechanism(text: str) -> str:
    """Conservative Chinese synonym normalization for mechanism memory.

    It unifies wording variants but retains different strategic concepts and
    their order; this is rule-based semantic normalization, not an LLM claim.
    """
    normalized=str(text or "unknown").lower()
    for pattern,replacement in _MECHANISM_PHRASES:normalized=re.sub(pattern,replacement,normalized)
    for pattern,replacement in _MECHANISM_WORDS:normalized=re.sub(pattern,replacement,normalized)
    normalized=re.sub(r"[\W_]+","",normalized)
    normalized=re.sub(r"(结果前置)(?:再用|然后用|并用|再|然后)(过程证明)",r"\1\2",normalized)
    # Phrase rewrites can meet an already-present canonical token at a boundary.
    for token in ("结果前置","过程证明","问题开场"):
        normalized=re.sub(f"(?:{token})+",token,normalized)
    return normalized[:120] or "unknown"

def mechanism_key(text: str) -> str:
    return normalize_mechanism(text)

def cluster_tasks(tasks: list[dict[str,Any]]) -> list[dict[str,Any]]:
    groups:dict[str,list[dict[str,Any]]]={}
    for task in tasks:
        mechanism=task.get("borrow_mechanism","")
        if not task.get("adoptable",True) or not mechanism or mechanism.startswith("待多模态模型"):continue
        groups.setdefault(mechanism_key(mechanism),[]).append(task)
    result=[]
    for key,members in groups.items():
        ids=sorted({cid for task in members for cid in task.get("evidence_creative_ids",[])})
        scores=[(task.get("scorecard") or {}).get("evidence_strength",0) for task in members]
        result.append({"schema_version":"strategy_cluster/v1","cluster_id":stable_id("mechanism",key)[:24],
            "label":members[0].get("borrow_mechanism") or "待判机制","mechanism":members[0].get("borrow_mechanism") or "unknown",
            "member_creative_ids":ids,"first_seen_at":min((t.get("created_at",now()) for t in members),default=now()),
            "last_seen_at":max((t.get("created_at",now()) for t in members),default=now()),
            "novelty":"new" if len(ids)==1 else "growing","evidence_strength":round(sum(scores)/len(scores),3) if scores else 0,
            "similarity_basis":"normalized_transferable_mechanism","cluster_version":"mechanism-v1"})
    return sorted(result,key=lambda x:(-x["evidence_strength"],x["cluster_id"]))

def cluster_analyses(analyses:list[dict[str,Any]])->list[dict[str,Any]]:
    groups={}
    for analysis in analyses:
        if not analysis.get("model_review"):continue
        narrative=(analysis.get("interpretations") or {}).get("narrative_structure") or []
        mechanism=str(narrative[0] if narrative else (analysis.get("interpretations") or {}).get("opening_hook") or "")
        if not mechanism:continue
        groups.setdefault(mechanism_key(mechanism),[]).append((analysis,mechanism))
    clusters=[]
    for key,members in groups.items():
        clusters.append({"schema_version":"mechanism_cluster/v1","cluster_id":stable_id("reviewed-mechanism",key)[:24],"label":members[0][1],
            "member_creative_ids":sorted({a.get("creative_id") for a,_ in members if a.get("creative_id")}),"reviewed":True,
            "recommendation_states":sorted({(a.get("model_review") or {}).get("decision","pending") for a,_ in members}),"cluster_version":"reviewed-mechanism-v1"})
    return clusters
