#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from common import atomic_write_json,read_json

def value(field):
    if isinstance(field,dict):return field.get("value") or field.get("label") or field.get("inference") or field.get("reason") or ""
    return field or ""
def values(field):
    """Flatten model variants into human strings; never stringify dict/list reprs."""
    if isinstance(field,list):
        result=[]
        for item in field:result.extend(values(item))
        return result
    resolved=value(field)
    if isinstance(resolved,list):return values(resolved)
    text=str(resolved or "").strip()
    return [text] if text else []
def confidence(field,default=.7):return float(field.get("confidence",default)) if isinstance(field,dict) else default
def validate_whitebox(value,review_dir:Path|None=None,source_sha256:str|None=None):
    if value is None:return None
    if not isinstance(value,dict):raise ValueError("whitebox_analysis 必须是对象")
    # 白盒是给用户理解的分析内容，不是格式考试。存在什么就展示什么；
    # 缺少固定段数、审计帧、回执或老板问卷都不能阻断策略形成。
    return value
def apply(analysis_path:Path,review_path:Path)->dict:
    analysis=read_json(analysis_path,{});review=read_json(review_path,{});labels=review.get("labels") or {}
    if review.get("schema_version") not in {"model_review/v1","model_review/v2"}:raise ValueError("无法读取这份素材拆解")
    recommendation=labels.get("recommendation") or {};decision=(recommendation.get("decision") if isinstance(recommendation,dict) else None) or ("hold" if "hold" in str(value(recommendation)).lower() else "pending")
    if decision not in {"adopt","hold","reject","pending"}:raise ValueError("recommendation.decision 非法；仅允许 adopt/hold/reject/pending")
    mechanism_parts=values(labels.get("transferable_mechanism"))
    mechanism="；".join(mechanism_parts)
    # The source hook may contain the competitor's product/brand. Preserve it as
    # evidence, but strategy output must use the abstract transferable mechanism.
    source_hook=str(value(labels.get("hook")))
    safe_hook=mechanism_parts[0] if mechanism_parts else "待人工抽象可迁移开场机制"
    analysis["interpretations"].update({"ad_intent":"；".join(values(labels.get("ad_intent"))),"source_opening_hook":source_hook,"opening_hook":safe_hook,"target_situation":"；".join(values(labels.get("target_stage"))),"customer_tension":"；".join(values(labels.get("pain_or_desire"))),"proof_devices":values(labels.get("proof")),"offer":"；".join(values(labels.get("offer"))),"cta":"；".join(values(labels.get("cta"))),"narrative_structure":mechanism_parts,"production_pattern":"；".join(values(labels.get("scene")))})
    analysis["confidence"]["interpretations"]=round(min(confidence(labels.get("hook")),confidence(labels.get("context_fit")),confidence(recommendation)),3)
    whitebox=validate_whitebox(labels.get("whitebox_analysis"))
    if whitebox is not None:analysis["whitebox_analysis"]=whitebox
    analysis["model_review"]={"schema_version":review.get("schema_version"),"reviewer_type":review.get("reviewer_type"),"source":str(review_path),"decision":decision,"recommendation":recommendation,"context_fit":labels.get("context_fit"),"non_transferable_surface":labels.get("non_transferable_surface"),"risk_claims":labels.get("risk_claims"),"whitebox_available":whitebox is not None}
    analysis["evidence_refs_review"]=labels.get("evidence_refs") or [];atomic_write_json(analysis_path,analysis);return analysis
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--analysis",required=True);p.add_argument("--review",required=True);a=p.parse_args();print(apply(Path(a.analysis),Path(a.review))["model_review"]["decision"])
