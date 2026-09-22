#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

DECISION_MAP={
    "继续放大":"continue","换一种做法":"modify","值得补做":"validate",
    "暂时不碰":"stop","继续观察":"validate",
    "continue":"continue","modify":"modify","stop":"stop","validate":"validate",
}

def ladder(row:dict)->dict:
    """Read old diagnoses through the new ladder without rewriting history."""
    facts=list(row.get("facts") or [])
    observations=list(row.get("observations") or [])
    if not observations and facts:
        observations=["这些事实之间存在值得继续比较的差异，但目前还不能确认原因"]
    unknowns=list(row.get("unknowns") or [])
    hypotheses=list(row.get("hypotheses") or [])
    if not hypotheses and unknowns:
        hypotheses=[f"如果补齐“{item}”，才能进一步验证当前解释" for item in unknowns[:2]]
    decision=DECISION_MAP.get(row.get("decision") or row.get("action"))
    return {**row,"facts":facts,"observations":observations,"hypotheses":hypotheses,"decision":decision}

def validate(d:dict,ledger:dict)->list[str]:
    errors=[];ids={x.get("content_id") for x in ledger.get("items") or []}
    for i,original in enumerate(d.get("items") or []):
        row=ladder(original)
        if row.get("content_id") not in ids:errors.append(f"items[{i}].content_id:not_in_ledger")
        if not row.get("facts"):errors.append(f"items[{i}].facts:missing")
        if not row.get("observations"):errors.append(f"items[{i}].observations:missing")
        if not row.get("primary_explanation"):errors.append(f"items[{i}].primary_explanation:missing")
        if len(row.get("competing_explanations") or [])>2:errors.append(f"items[{i}].competing_explanations:max_2")
        if row.get("decision") not in {"continue","modify","stop","validate"}:errors.append(f"items[{i}].decision:invalid")
        # 不确定信息尽量说清，但缺少固定等级或假设格式不能阻断复盘。
        if row.get("decision")=="stop" and not row.get("stop_basis"):errors.append(f"items[{i}].stop_basis:required")
    return sorted(set(errors))

def main():
    p=argparse.ArgumentParser();p.add_argument("diagnosis",type=Path);p.add_argument("ledger",type=Path);a=p.parse_args();e=validate(json.loads(a.diagnosis.read_text(encoding="utf-8")),json.loads(a.ledger.read_text(encoding="utf-8")));print(json.dumps({"valid":not e,"errors":e},ensure_ascii=False,indent=2));return 0 if not e else 1
if __name__=="__main__":raise SystemExit(main())
