#!/usr/bin/env python3
"""Build a shared enterprise context and a plain-language HTML whitepaper."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_shared_context import validate  # noqa: E402


def stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def render_cards(title: str, rows: list[dict], empty: str) -> str:
    cards = []
    for row in rows:
        label = row.get("segment") or row.get("name") or row.get("stage") or "未命名"
        detail = row.get("description") or row.get("need") or row.get("value") or row.get("touchpoint") or ""
        cards.append(f'<article class="card"><h3>{html.escape(str(label))}</h3><p>{html.escape(str(detail))}</p></article>')
    body = "".join(cards) if cards else f'<p class="empty">{html.escape(empty)}</p>'
    return f'<section><div class="section-head"><span>{html.escape(title)}</span></div><div class="cards">{body}</div></section>'


def render_knowledge(rows: list[dict]) -> str:
    labels = {"fact": "资料里写明", "inference": "我们目前的理解", "hypothesis": "还不确定", "unknown": "暂时不知道", "boundary": "不能这样说"}
    items = []
    for row in rows:
        kind = row["kind"]
        items.append(
            f'<li class="knowledge {kind}"><div><b>{html.escape(labels.get(kind, kind))}</b>'
            f'<p>{html.escape(row["statement"])}</p></div></li>'
        )
    return "".join(items)


def _text(value, fallback: str = "资料里还没有") -> str:
    if isinstance(value, list):
        value = "；".join(str(item) for item in value if str(item).strip())
    return str(value).strip() if value not in (None, "", []) else fallback


def render_strategy_foundation(foundation: dict) -> str:
    customer=foundation.get("customer") or {};battlefield=foundation.get("battlefield") or {};solution=foundation.get("solution") or {};decision=foundation.get("decision_path") or {};channels=foundation.get("channels") or []
    tried="；".join(f'{x.get("name","过去的办法")}：{x.get("failure_gap","资料里没说哪里不够")}' for x in customer.get("tried_alternatives",[]) if isinstance(x,dict))
    actors="；".join(f'{x.get("role","做决定的人")}在意：{x.get("main_concern","资料里还没有")}' for x in decision.get("actors",[]) if isinstance(x,dict))
    channel="；".join(" / ".join(p for p in (str(x.get("platform") or ""),str(x.get("track") or "")) if p) for x in channels if isinstance(x,dict))
    scene=battlefield.get("primary_scene") or {}
    if isinstance(scene,dict):scene=scene.get("statement") or " · ".join(str(scene.get(k) or "") for k in ("time","action","feeling")).strip(" ·")
    cards=[
     ("01","我们最想帮谁",_text(customer.get("primary_segment")),[("他现在遇到",_text(customer.get("visible_symptoms"))),("真正的问题",_text(customer.get("root_problem"))),("以前试过",tried or "资料里还没有"),("最后想得到",_text(customer.get("desired_outcome_scene")))]),
     ("02","先解决哪个场景",_text(scene),[("为什么从这里开始",_text(battlefield.get("priority_reason"))),("希望发生",_text(battlefield.get("hope_scene")))]),
     ("03","为什么选我们",_text(solution.get("positioning_sentence")),[("客户拿我们和谁比",_text(solution.get("comparison_against"))),("最关键的不同",_text(solution.get("primary_advantage"))),("能拿出的证明",_text(solution.get("evidence")))]),
     ("04","顾客为什么愿意行动",actors or "资料里还没写清谁做决定、他担心什么",[("他最担心什么",_text(decision.get("primary_barrier"))),("怎么让他放心",_text(decision.get("mitigation"))),("希望他下一步做什么",_text(decision.get("next_action")))]),
     ("05","内容出现在哪里",channel or "资料里还没写清渠道和赛道",[("这次要带来什么",_text([x.get("business_job") for x in channels if isinstance(x,dict)])),("哪些话不能说",_text([v for x in channels if isinstance(x,dict) for v in x.get("confirmed_constraints",[])]))])]
    body=[]
    for number,title,lead,details in cards:
     rows="".join(f'<li><span>{html.escape(label)}</span><b>{html.escape(value)}</b></li>' for label,value in details);body.append(f'<article class="judgment"><i>{number}</i><h3>{html.escape(title)}</h3><p>{html.escape(lead)}</p><ul>{rows}</ul></article>')
    return '<section><div class="section-head"><span>这家公司最重要的 5 件事</span><small>系统会按这份理解继续工作；哪里不对，随时直接纠正</small></div><div class="judgments">'+"".join(body)+"</div></section>"


def render(context: dict) -> str:
    question = context.get("current_business_question") or "暂时没有指定本轮业务问题"
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(context["company"])}｜企业人货场白皮书</title>
<style>
:root{{--ink:#122033;--muted:#637083;--paper:#f5f3ed;--card:#fff;--blue:#246bfd;--line:#dfe4ea;--warn:#a25a00}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}
main{{max-width:1120px;margin:auto;padding:48px 22px 80px}} header{{padding:42px;border-radius:26px;background:#10223d;color:white}}
.eyebrow{{color:#8fb4ff;font-weight:700}} h1{{font-size:clamp(32px,5vw,58px);line-height:1.1;margin:12px 0}} .question{{font-size:20px;max-width:760px}}
.meta{{color:#bdc9d8;font-size:14px}} section{{margin-top:34px}} .section-head{{font-size:24px;font-weight:800;margin-bottom:14px}}
.section-head small{{display:block;font-size:14px;font-weight:500;color:var(--muted);margin-top:2px}} .judgments{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}} .judgment{{background:white;border:1px solid var(--line);padding:22px;border-radius:18px}} .judgment:first-child{{grid-column:span 2}} .judgment i{{font-style:normal;color:var(--blue);font-weight:800;font-size:13px}} .judgment h3{{margin:4px 0 8px;font-size:21px}} .judgment>p{{font-size:18px;font-weight:750;margin:0 0 15px}} .judgment ul{{border-top:1px solid var(--line);padding-top:11px}} .judgment li{{display:grid;grid-template-columns:120px 1fr;gap:12px}} .judgment li span{{color:var(--muted);font-size:13px}} .judgment li b{{font-weight:550}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}} .card{{background:var(--card);border:1px solid var(--line);padding:20px;border-radius:18px}}
.card h3{{margin:0 0 8px}} .card p{{margin:0;color:var(--muted)}} ul{{list-style:none;padding:0;display:grid;gap:10px}}
.knowledge{{background:white;border:1px solid var(--line);border-left:5px solid var(--blue);padding:16px 18px;border-radius:14px;display:flex;gap:20px;justify-content:space-between}}
.knowledge p{{margin:4px 0 0}} .knowledge small{{color:var(--muted);white-space:nowrap}} .unknown{{border-left-color:var(--warn)}} .boundary{{border-left-color:#c73535}}
.empty{{color:var(--muted)}} footer{{margin-top:42px;color:var(--muted);font-size:14px}} @media(max-width:640px){{header{{padding:28px}}.judgments{{grid-template-columns:1fr}}.judgment:first-child{{grid-column:auto}}.judgment li{{grid-template-columns:1fr;gap:1px}}.knowledge{{display:block}}.knowledge small{{white-space:normal}}}}
</style></head><body><main>
<header><div class="eyebrow">我对这家公司的理解 · 第 {context["version"]} 版</div><h1>{html.escape(context["company"])}<br>企业白皮书</h1><p class="question">这次最想解决：{html.escape(question)}</p><p class="meta">你只要看内容对不对。看不懂的系统信息，我已经放到后台。</p></header>
{render_strategy_foundation(context.get("strategy_foundation") or {})}
{render_cards("人｜客户是谁", context["people"], "现有资料还没有讲清客户是谁。")}
{render_cards("货｜提供什么", context["offerings"], "现有资料还没有讲清产品或服务。")}
{render_cards("场｜生意发生在哪里", context["scenes"], "现有资料还没有讲清客户在哪些场景接触和购买。")}
<section><div class="section-head"><span>还有哪些重要信息</span></div><ul>{render_knowledge(context["knowledge"] + context["boundaries"])}</ul></section>
<footer>这是当前版本。你纠正后，旧版本会自动保留。</footer>
</main></body></html>'''


def build(inventory: dict, claims: dict, previous: dict | None = None) -> dict:
    sources = [
        {key: item[key] for key in ("source_id", "source_type", "locator", "observed_at")}
        for item in inventory.get("items", [])
    ]
    version = (previous or {}).get("version", 0) + 1
    company = str(claims.get("company") or "").strip()
    created_at = datetime.now().astimezone().isoformat()
    context = {
        "schema_version": "shared_enterprise_context/v1",
        "context_id": stable_id(company, str(version), created_at),
        "company": company,
        "version": version,
        "supersedes": (previous or {}).get("context_id"),
        "created_at": created_at,
        "created_by": claims.get("created_by") or "agent_pending_owner_review",
        "current_business_question": claims.get("current_business_question"),
        "strategy_foundation": claims.get("strategy_foundation") or {},
        "people": claims.get("people") or [],
        "offerings": claims.get("offerings") or [],
        "scenes": claims.get("scenes") or [],
        "knowledge": claims.get("knowledge") or [],
        "boundaries": claims.get("boundaries") or [],
        "sources": sources,
    }
    errors = validate(context)
    if errors:
        raise ValueError(";".join(errors))
    return context


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    claims = json.loads(args.claims.read_text(encoding="utf-8"))
    previous = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous else None
    context = build(inventory, claims, previous)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "shared_enterprise_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "企业人货场白皮书.html").write_text(render(context), encoding="utf-8")
    print(json.dumps({"context_id": context["context_id"], "version": context["version"], "html": str(args.output_dir / "企业人货场白皮书.html")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
