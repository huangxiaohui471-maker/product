#!/usr/bin/env python3
from __future__ import annotations

"""Render the learner-facing daily creative intelligence desk.

The renderer intentionally separates the simple user surface from engineering
artifacts. It reads the evidence chain, but only exposes original media,
editorial conclusions, a single next action, and understandable memory.
"""

import argparse
import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from common import atomic_write_json, atomic_write_text, now, read_json, read_jsonl


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def compact(value: int | float | None) -> str:
    if value is None:
        return "—"
    value = int(value)
    if value >= 10000:
        return f"{value / 10000:.1f}万".replace(".0万", "万")
    return f"{value:,}"


def short_date(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value)).astimezone().strftime("%m月%d日")
    except Exception:
        return "今日收录"


def rel_asset(workspace: Path, raw: str | None) -> str:
    if not raw:
        return ""
    source = Path(raw)
    if not source.is_absolute():
        candidates = [Path.cwd() / source, workspace / source]
        candidates.extend(parent / source for parent in workspace.parents)
        source = next((p for p in candidates if p.exists()), candidates[0])
    try:
        return Path(os.path.relpath(source.resolve(), workspace.resolve())).as_posix()
    except Exception:
        return ""


def clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        rows = value
    elif value:
        rows = [value]
    else:
        rows = []
    result = []
    for row in rows:
        if isinstance(row, list):
            result.extend(str(x) for x in row if x)
        elif isinstance(row, dict):
            text=str(row.get("value") or row.get("label") or row.get("inference") or row.get("reason") or "").strip()
            if text:result.append(text)
        elif row:
            text = str(row).strip()
            if text.startswith("[") and text.endswith("]"):
                try:
                    parsed = json.loads(text.replace("'", '"'))
                    result.extend(str(x) for x in parsed if x)
                    continue
                except Exception:
                    pass
            result.append(text)
    return result


ZH_LABELS = {
    "distress_scene_plus_category_reversal": "危机画面开场，紧接着反转常见品类认知",
    "problem_first_contrast_then_numbered_mechanism_breakdown": "先抛出问题，再用反差和分点拆解讲清原因",
    "sun_protection_desire_conflicts_with_road_safety": "防晒需求与骑行安全的冲突",
    "narrated_statistics_cases_and_illustrative_footage_unverified": "用数据、案例和画面增强说服力，但来源尚未核验",
    "voiceover_montage_of_road_incidents_riders_and_graphics": "画外音串联事故、骑行与图解画面",
    "editorial_safety_commentary_not_direct_response_ad": "安全议题型自然内容，不是直接转化广告",
    "awareness_and_problem_education": "认知与问题教育阶段",
    "creator_search_discovery_cta": "引导搜索创作者，不是购买行动",
    "none": "未见",
    "organic_like": "更像自然内容",
}


def zh(value: Any, fallback: str = "待主编归纳") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return text
    return ZH_LABELS.get(text, fallback)


def human_source(value: Any, fallback: str = "对应时段的原片画面与口播") -> str:
    """Translate machine evidence references into a location a learner can understand."""
    text = "、".join(clean_list(value)).strip()
    if not text:
        return fallback
    import re
    times = re.findall(r"(?:\d{1,2}:\d{2}(?::\d{2})?|\d+(?:\.\d+)?s)(?:\s*[–—-]\s*(?:\d{1,2}:\d{2}(?::\d{2})?|\d+(?:\.\d+)?s))?", text, flags=re.I)
    if times:
        return "原片 " + "、".join(dict.fromkeys(times))
    return fallback


def whitebox_html(analysis: dict[str, Any], transcript_note: str) -> str:
    """Render detailed user reasoning without exposing internal machine fields."""
    wb = analysis.get("whitebox_analysis") or {}
    if not wb:
        interp = analysis.get("interpretations") or {}
        ready=bool(interp.get('opening_hook') and interp.get('customer_tension') and clean_list(interp.get('proof_devices')))
        if not ready:return '<div class="whitebox pending-whitebox"><b>这条还在处理中</b><p>处理完成前不会把它推荐给你。</p></div>'
        return f'''<div class="whitebox"><dl class="breakdown"><dt>开场</dt><dd>{esc(zh(interp.get('opening_hook'), '未见明确开场'))}</dd><dt>说给谁听</dt><dd>{esc(zh(interp.get('customer_tension'), '未见明确对象'))}</dd><dt>用了什么证明</dt><dd>{esc('、'.join(zh(x, '画面或口播证明') for x in clean_list(interp.get('proof_devices'))))}</dd><dt>卖什么</dt><dd>{esc(zh(interp.get('offer'), '这条没有直接销售'))}</dd><dt>结尾</dt><dd>{esc(zh(interp.get('cta'), '这条没有明确行动'))}</dd><dt>完整口播</dt><dd>{esc(transcript_note)}</dd></dl></div>'''
    timeline = "".join(
        f'''<article class="wb-step"><div class="wb-time">{esc(row.get('time'))}</div><div><span>{esc(row.get('stage'))}</span><h4>{esc(row.get('why_it_matters'))}</h4><div class="wb-av"><p><b>画面</b>{esc(row.get('visual'))}</p><p><b>口播/信息</b>{esc(row.get('spoken_message'))}</p></div><p><b>两者怎么配合：</b>{esc(row.get('how_they_work_together'))}</p><small>回看位置：{esc(human_source(row.get('evidence'), '原片 '+str(row.get('time') or '对应片段')))}</small></div></article>'''
        for row in wb.get("timeline") or []
    )
    raw_chain = wb.get("persuasion_chain") or []
    if isinstance(raw_chain, str):
        chain = f'''<div class="wb-reason"><b>说服顺序</b><p>{esc(raw_chain)}</p></div>'''
    else:
        chain = "".join(
            f'''<div class="wb-reason"><b>{esc(row.get('question'))}</b><p>{esc(row.get('answer'))}</p><small>{esc(human_source(row.get('evidence')))}</small></div>'''
            if isinstance(row, dict) else f'''<div class="wb-reason"><p>{esc(row)}</p></div>'''
            for row in raw_chain
        )
    raw_claims = wb.get("claims_to_check") or []
    claims = "".join(
        f'''<tr><td>{esc(row.get('source_says'))}</td><td>{esc(row.get('what_we_can_confirm'))}</td><td>{esc(row.get('needed_before_use'))}</td></tr>'''
        if isinstance(row, dict) else f'''<tr><td>{esc(row)}</td><td>目前只确认来源素材这样表达</td><td>使用前补充企业自己的证据</td></tr>'''
        for row in raw_claims
    )
    raw_transfer = wb.get("transfer_reasoning") or {}
    transfer = raw_transfer if isinstance(raw_transfer, dict) else {"reason": str(raw_transfer)}
    reconstruction=wb.get("reconstruction") or {}
    shot_rows="".join(f'''<div class="rebuild-shot"><b>{esc(row.get('time'))}</b><div><strong>{esc(row.get('job'))}</strong><p>画面：{esc(row.get('visual'))}</p><p>文字/口播：{esc(row.get('text'))}</p></div></div>''' for row in reconstruction.get("shots") or [])
    owner_questions=clean_list(reconstruction.get("owner_questions") or wb.get("open_questions") or [])[:1]
    rebuild_html=(f'''<h4>换成你的业务，可以这样重拍</h4><p>{esc(reconstruction.get('goal'))}</p><div class="rebuild-plan">{shot_rows}</div>''' if reconstruction else "")
    question_html=(f'''<h4>只有这一点会影响结果</h4><ul>{''.join(f'<li>{esc(x)}</li>' for x in owner_questions)}</ul>''' if owner_questions else "")
    return f'''<div class="whitebox"><p class="wb-logic">{esc(wb.get('one_sentence_logic'))}</p><h4>每一段拍了什么、说了什么</h4>{timeline}<h4>为什么这样写</h4><div class="wb-reasons">{chain}</div><h4>哪些话不能照抄</h4><div class="wb-table"><table><thead><tr><th>原素材怎么说</th><th>可以学什么</th><th>要换成什么</th></tr></thead><tbody>{claims}</tbody></table></div><h4>可以学什么</h4><div class="wb-transfer"><div><b>保留</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in clean_list(transfer.get('keep')))}</ul></div><div><b>替换</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in clean_list(transfer.get('replace')))}</ul></div></div><p>{esc(transfer.get('reason'))}</p>{rebuild_html}{question_html}</div>'''


def latest_candidates(workspace: Path,day:str|None=None) -> list[dict[str, Any]]:
    day = day or datetime.now().astimezone().strftime("%Y-%m-%d")
    files = list((workspace / "runs").glob(f"discovery-{day}*/candidates.json"))
    files += list((workspace / "runs").glob(f"douplus-{day}*/candidates.json"))
    files += list((workspace / "runs").glob(f"adintel-*-{day}*/candidates.json"))
    for receipt in (workspace/"runs").glob("daily-*/daily_run.json"):
        data=read_json(receipt,{})
        if str(data.get("started_at") or "").startswith(day):
            source=Path(str(data.get("source_batch") or ""))
            if source.is_file():files.append(source)
    files = sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)
    unique={}
    # A daily funnel must describe one source batch. Mixing several searches
    # from the same date creates impressive but false collection counts.
    for file in files[:1]:
        payload=read_json(file,{})
        rows=payload if isinstance(payload,list) else payload.get("candidates",[])
        for row in rows:
            key=str(row.get("creative_id") or row.get("canonical_url") or row.get("provider_record_id"))
            if key and key not in unique:unique[key]=row
    return list(unique.values())


def candidate_delta(workspace: Path, current: list[dict[str, Any]]) -> int:
    """Count first-seen candidates against every earlier discovery batch."""
    files = list((workspace / "runs").glob("discovery-*/candidates.json"))
    files += list((workspace / "runs").glob("douplus-*/candidates.json"))
    files += list((workspace / "runs").glob("adintel-*/candidates.json"))
    files = sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)
    old_ids: set[str] = set()
    for file in files[1:]:
        payload = read_json(file, {})
        previous = payload if isinstance(payload, list) else payload.get("candidates", [])
        old_ids.update(str(x.get("creative_id") or x.get("canonical_url")) for x in previous)
    return sum(1 for x in current if str(x.get("creative_id") or x.get("canonical_url")) not in old_ids)


def latest_daily_intelligence(workspace:Path,day:str|None=None)->dict[str,Any]:
    """Return one coherent daily batch; never mix counts from unrelated runs."""
    day=day or datetime.now().astimezone().strftime("%Y-%m-%d")
    receipts=[]
    for path in (workspace/"runs").glob("daily-*/daily_run.json"):
        data=read_json(path,{})
        if str(data.get("started_at") or "").startswith(day):receipts.append((str(data.get("started_at")),path,data))
    if not receipts:return {}
    return sorted(receipts,key=lambda row:row[0],reverse=True)[0][2]


def team_task_card_html(task:dict[str,Any],analysis:dict[str,Any],adopted:bool)->str:
    """Render the accepted experiment as a handoff card, not downstream production."""
    if not adopted:return ""
    handoff=task.get("production_handoff") or {}
    shots=handoff.get("shots") or ((analysis.get("whitebox_analysis") or {}).get("reconstruction") or {}).get("shots") or []
    questions=handoff.get("owner_questions") or []
    constants=clean_list(task.get("constants"))
    boundaries=clean_list(task.get("claim_boundaries"))
    rows="".join(f'''<li><b>{esc(row.get('time'))} · {esc(row.get('job'))}</b><span>画面：{esc(row.get('visual'))}</span><span>文字/口播：{esc(row.get('text'))}</span></li>''' for row in shots if isinstance(row,dict))
    plain=["【今日内容实验】",str(handoff.get("goal") or task.get("draft_brief") or "") ,"只改："+single_variable_copy(task)]
    plain += [f"{row.get('time')}｜{row.get('visual')}｜{row.get('text')}" for row in shots if isinstance(row,dict)]
    if questions:plain.append("开拍前补齐："+"；".join(str(x) for x in questions))
    if boundaries:plain.append("不能说："+"；".join(boundaries))
    return f'''<section class="task-card"><div class="task-card-head"><div><span>已经选定</span><h3>可直接发给团队的今日实验卡</h3><p>这是本轮实验交接，不会替你自动生成或发布视频。</p></div><button class="quiet" onclick="copyTask(this)">复制给团队</button></div><div class="task-focus"><b>今天只改</b><p>{esc(single_variable_copy(task))}</p></div><ol>{rows}</ol><div class="task-notes"><div><b>其他保持不变</b><p>{esc('、'.join(constants) or '产品、受众、核心承诺和投放设置')}</p></div><div><b>开拍前由老板补齐</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in questions)}</ul></div><div><b>不能直接使用</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in boundaries)}</ul></div></div><textarea class="task-copy" aria-hidden="true">{esc(chr(10).join(plain))}</textarea></section>'''


def load_rows(workspace: Path, day: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    day = day or datetime.now().astimezone().strftime("%Y-%m-%d")
    for run in sorted((workspace / "runs").glob("*"), reverse=True):
        evidence = read_json(run / "creative/evidence.json", {})
        analysis = read_json(run / "analysis/analysis.json", {})
        task = read_json(run / "experiment.json", {})
        # Unfinished strategy review is work-in-progress, not yesterday's news.
        # Carry it forward until V2 review closes the gate, even across dates.
        # A review completed today is today's decision inventory even when the
        # source was collected before midnight.  Collection date and judgment
        # date are different product events and must not be conflated.
        reviewed_at=str(task.get("reviewed_at") or "")[:10]
        if not run.name.startswith(day) and reviewed_at != day:
            manifest=read_json(run/"run_manifest.json",{})
            active_pending=task.get("needs_strategy_review") and manifest.get("status")=="succeeded" and manifest.get("current_stage") not in {"DONE","FAILED_PERMANENT"}
            if not active_pending:continue
        if not evidence or not analysis or not task or not task.get("visible_in_dashboard", True):
            continue
        media = evidence.get("media") or {}
        rows.append({
            "run": run,
            "evidence": evidence,
            "analysis": analysis,
            "task": task,
            "media_hash": media.get("sha256"),
            "adapter": (evidence.get("provenance") or {}).get("adapter", "manual"),
        })

    # Prefer connector-enriched evidence for byte-identical media.
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["media_hash"] or row["evidence"].get("creative_id") or row["run"].name
        old = unique.get(key)
        if old is None or (old["adapter"] == "manual" and row["adapter"] != "manual"):
            unique[key] = row
    return list(unique.values())


def evidence_label(evidence: dict[str, Any]) -> str:
    evidence_class = evidence.get("evidence_class")
    class_labels = {
        "verified_paid_platform_library": "平台广告素材",
        "verified_paid_owned_account": "自己投过的素材",
        "authorized_top_ad": "推广榜单素材",
        "third_party_ad_library": "飞瓜素材",
        "commercial_like_proxy": "转化素材候选",
        "public_content_only": "公开对标素材",
        "user_supplied_unverified": "自己提供的素材",
    }
    if evidence_class in class_labels:
        return class_labels[evidence_class]
    level = (evidence.get("paid_evidence") or {}).get("level")
    return {
        "verified_paid": "自己投过的素材",
        "strong_signal": "推广素材候选",
        "weak_signal": "转化素材候选",
    }.get(level, "公开对标素材")


def action_state(task: dict[str, Any]) -> tuple[str, str, bool]:
    state=str(task.get("recommendation_state") or "")
    legacy=str((task.get("review_gate") or {}).get("decision") or "")
    if state=="recommended" or legacy=="adopt" or task.get("adoptable"):
        if task.get("decision") in {"hold","reject"} and not task.get("adoptable") and not state:
            return "留作参考", "看完整拆解", False
        return "今天建议做", "开始做内容", True
    if state=="observe" or legacy=="hold":return "留作参考", "看完整拆解", False
    return "还在整理", "先看拆解", False


def single_variable_copy(task: dict[str, Any]) -> str:
    """Translate the experiment contract into one visible, shootable change."""
    variable = task.get("single_variable") or {}
    handoff = task.get("production_handoff") or {}
    shots = handoff.get("shots") or []
    if variable.get("name") == "opening_hook" and shots:
        first = shots[0] if isinstance(shots[0], dict) else {}
        visual = str(first.get("visual") or "").strip().rstrip("。")
        text = str(first.get("text") or "").strip().rstrip("。")
        if visual and text:
            return f"前3秒：{visual}；{text}"
        if visual or text:
            return f"前3秒：{visual or text}"
    return zh(variable.get("to") or task.get("borrow_mechanism"), "只替换一个开场表达")


def plain_topic(task: dict[str, Any]) -> str:
    questions = (task.get("production_handoff") or {}).get("owner_questions") or []
    if questions:
        text = str(questions[0]).strip()
        quoted = re.search(r"[‘'“\"]([^’'”\"]{4,100})[’'”\"]", text)
        if quoted:
            return quoted.group(1).strip()
        for prefix in ("你要不要做一条", "你愿意做一条"):
            if text.startswith(prefix):
                text = text[len(prefix):]
        if "？" in text:
            text = text.split("？", 1)[0]
        if "?" in text:
            text = text.split("?", 1)[0]
        text = re.sub(r"的反常识开口版吗?$", "", text.strip())
        return text.strip("'‘’\"“”吗 ")
    return zh(task.get("borrow_mechanism"), "今天的选题还没写好")


def plain_shortlist_status(value: Any) -> str:
    text = str(value or "候选")
    return {"待深拆": "还没拆解", "已进入深拆": "已拆解", "今日主推": "推荐", "本次读取失败": "原片暂时打不开"}.get(text, text)


def render(workspace: Path, output: Path, day: str | None = None) -> None:
    rows = load_rows(workspace,day)
    context = read_json(workspace / "config/enterprise_context.json", {})
    watch = read_json(workspace / "config/watch_universe.json", {})
    seen = read_jsonl(workspace / "memory/seen_creatives.jsonl")
    decisions = read_jsonl(workspace / "memory/decisions.jsonl")
    candidates = latest_candidates(workspace,day)
    daily_intel = latest_daily_intelligence(workspace,day)
    funnel = daily_intel.get("candidate_funnel") or {}
    shortlist = daily_intel.get("shortlist") or []
    if not shortlist:
        shortlist=[{"rank":index,"creative_id":row.get("creative_id"),"title":row.get("title"),"platform":row.get("platform"),"author_name":row.get("author_name"),"canonical_url":row.get("canonical_url"),"reason":"与当前观察范围相关，已进入今日候选","visible_signal":{"likes":(row.get("search_metrics") or {}).get("likes")},"status":"待深拆"} for index,row in enumerate(candidates[:8],1)]
    new_candidates = candidate_delta(workspace, candidates)
    upgraded_evidence = sum(1 for row in rows if row["task"].get("is_evidence_enrichment"))
    paid_classes = {"verified_paid_platform_library", "verified_paid_owned_account", "authorized_top_ad", "third_party_ad_library"}
    has_paid_source = any(row["evidence"].get("evidence_class") in paid_classes for row in rows)
    desk_title = "每日内容情报 · 自然流+投放" if has_paid_source else "每日内容情报 · 自然流"
    intel_title = "今天找到的推广素材" if has_paid_source else "今天找到的热门内容"
    intel_note = "这些素材上过推广榜，但不代表今天还在投。" if has_paid_source else "这些是公开内容，不代表同行正在投广告。"

    today = (datetime.strptime(day,"%Y-%m-%d").strftime("%Y年%m月%d日") if day else datetime.now().astimezone().strftime("%Y年%m月%d日"))
    company = context.get("name") or "当前企业"
    goal = context.get("business_goal") or "验证下一个内容方向"
    priority = context.get("current_priority") or "找到今天只测的一个变量"

    # Decisions are durable product state: an adopted item stays selected; held
    # items are suppressed so reload advances to the next useful direction.
    latest_decision: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        latest_decision[str(decision.get("experiment_id"))] = decision
    def current_decision(task: dict[str, Any]) -> str:
        decision = latest_decision.get(str(task.get("experiment_id"))) or {}
        state = str(decision.get("decision") or "")
        if state == "adopt":
            try:
                decided = datetime.fromisoformat(str(decision.get("decided_at") or "").replace("Z", "+00:00")).astimezone()
                if decided.date() != datetime.now().astimezone().date():
                    return "" if task.get("is_evidence_enrichment") else "used"
            except ValueError:
                return ""
        if state in {"hold", "reject"} and decision.get("cooldown_until"):
            try:
                if datetime.fromisoformat(str(decision["cooldown_until"]).replace("Z", "+00:00")) <= datetime.now().astimezone():
                    return ""
            except ValueError:
                pass
        if state:return state
        mapped={"recommended":"adopt","observe":"hold","excluded":"reject","processing":"processing"}.get(str(task.get("recommendation_state") or ""),"")
        if mapped:return mapped
        # Old v1 reviews could say "adopt" while the experiment itself stayed
        # on hold because the production handoff was incomplete.  The terminal
        # task state wins; otherwise a reference item becomes a false ready job.
        terminal=str(task.get("decision") or "")
        if terminal in {"hold","reject"} and not task.get("adoptable"):
            return terminal
        # Backward-compatible migration path: old workspaces stored the model
        # recommendation only inside review_gate.
        return str((task.get("review_gate") or {}).get("decision") or "")
    def row_ready(row:dict[str,Any])->bool:
        explicit=row["task"].get("content_ready")
        if explicit is not None:return bool(explicit)
        interp=row["analysis"].get("interpretations") or {}
        return bool(interp.get("opening_hook") and interp.get("customer_tension") and clean_list(interp.get("proof_devices")) and current_decision(row["task"]) not in {"","pending","processing"})
    adopted = [r for r in rows if current_decision(r["task"]) == "adopt" and row_ready(r)]
    available = [r for r in rows if current_decision(r["task"]) not in {"hold", "reject", "used", "processing"} and row_ready(r)]
    display_rows = [r for r in rows if current_decision(r["task"]) != "reject" and row_ready(r)]
    reviewed_rows = [r for r in display_rows if (r["task"].get("review_gate") or {}).get("decision") in {"adopt", "hold", "reject"}]
    rows.sort(key=lambda r: (current_decision(r["task"])=="adopt", float((r["task"].get("scorecard") or {}).get("context_fit") or 0), float((r["task"].get("scorecard") or {}).get("reference_score") or 0)), reverse=True)
    if adopted:
        lead = sorted(adopted, key=lambda r: str((latest_decision.get(str(r["task"].get("experiment_id"))) or {}).get("decided_at", "")), reverse=True)[0]
    else:
        ordered_available = [r for r in rows if r in available]
        lead = ordered_available[0] if ordered_available else None

    def video_markup(row: dict[str, Any], cls: str = "") -> str:
        media = row["evidence"].get("media") or {}
        src = rel_asset(workspace, media.get("local_path"))
        shots = (row["analysis"].get("observations") or {}).get("shots") or []
        poster = rel_asset(workspace, (shots[6] if len(shots) > 6 else shots[0]).get("path")) if shots else ""
        return f'<video class="{cls}" controls preload="metadata" playsinline poster="{esc(poster)}"><source src="{esc(src)}" type="video/mp4">当前浏览器无法播放该视频。</video>'

    def poster_markup(row: dict[str, Any]) -> str:
        shots = (row["analysis"].get("observations") or {}).get("shots") or []
        poster = rel_asset(workspace, (shots[6] if len(shots) > 6 else shots[0]).get("path")) if shots else ""
        return f'<img src="{esc(poster)}" alt="代表素材封面" loading="lazy">'

    def metric_strip(evidence: dict[str, Any]) -> str:
        metrics = evidence.get("metrics") or {}
        items = [("赞", metrics.get("likes")), ("评论", metrics.get("comments")), ("分享", metrics.get("shares")), ("收藏", metrics.get("collects"))]
        return "".join(f'<span><b>{compact(v)}</b>{esc(k)}</span>' for k, v in items if v is not None)

    def correction(task: dict[str, Any]) -> str:
        return f'''<details class="correction"><summary>这个方向不适合我</summary><div class="correction-body"><label for="why-{esc(task.get('experiment_id'))}">愿意的话说一句原因；不说也可以直接换</label><textarea id="why-{esc(task.get('experiment_id'))}" placeholder="例如：我们现在不做低价套餐"></textarea><button class="quiet" onclick="correct(this)">换一个方向</button></div></details>'''

    task_card_html = ""
    if lead:
        task, evidence, analysis = lead["task"], lead["evidence"], lead["analysis"]
        interp = analysis.get("interpretations") or {}
        review = task.get("review_gate") or {}
        state, button_label, enabled = action_state(task)
        saved_decision = latest_decision.get(str(task.get("experiment_id"))) or {}
        if saved_decision.get("decision") == "adopt":
            state, button_label, enabled = "已经交给生产", "已进入内容制作", False
            task_card_html = team_task_card_html(task,analysis,True)
        allowed = ((review.get("recommendation") or {}).get("allowed_use") or "")
        reconstruction = ((analysis.get("whitebox_analysis") or {}).get("reconstruction") or {})
        main_copy = allowed or reconstruction.get("goal") or task.get("draft_brief") or task.get("hypothesis") or "把这个机制换成你的真实业务信息，直接做出第一版内容。"
        if "人工确认" in str(main_copy):main_copy="把这个机制换成你的真实业务信息，直接做出第一版内容。"
        transfer_reason = (((analysis.get("whitebox_analysis") or {}).get("transfer_reasoning") or {}).get("reason") if isinstance((analysis.get("whitebox_analysis") or {}).get("transfer_reasoning"),dict) else "")
        fit_raw = transfer_reason or task.get("context_fit_reason") or ((review.get("context_fit") or {}).get("reason") or "")
        if any(token in str(fit_raw).lower() for token in ("多模态", "匹配度", "confidence", "0.", "系统", "白皮书", "迁移", "辅助信号")):
            fit_raw = "你的客户也正在怀疑 AI 为什么没带来业务变化；这个开场先说中他的困惑，再把答案带到你的课程。"
        if fit_raw and not any("\u4e00" <= ch <= "\u9fff" for ch in str(fit_raw)):
            fit = "这条素材可以借它的说服顺序，但不能直接照搬。真正开拍时，要换成你自己的产品、真实信息和成交入口。"
        else:
            fit = str(fit_raw)
        non_transferable = review.get("non_transferable_surface")
        if isinstance(non_transferable, dict):
            non_transferable = non_transferable.get("value")
        no_copy = clean_list(non_transferable) or clean_list(task.get("do_not_copy"))
        strategy_title = plain_topic(task)
        lead_html = f'''
        <div class="lead-media">{video_markup(lead, "lead-video")}<div class="media-caption"><span>{esc(evidence.get('platform','公开渠道'))} · @{esc((evidence.get('author') or {}).get('display_name') or '原作者')}</span><span>{esc(evidence_label(evidence))}</span></div></div>
        <div class="lead-copy">
          <div class="decision-state">{esc(state)}</div>
          <h2>{esc(strategy_title)}</h2>
          <dl class="why-grid"><dt>为什么今天做</dt><dd>{esc(fit or task.get('why_now'))}</dd><dt>具体怎么写</dt><dd>{esc(single_variable_copy(task))}</dd></dl>
          <div class="decision-actions"><button class="primary {'ready' if enabled else 'guarded'}" onclick="choose(this,'{'use' if enabled else 'inspect'}')">{esc(button_label)}</button><button class="text-button" onclick="choose(this,'swap')">换一个方向</button></div>
          {correction(task)}
          <details class="evidence-drawer"><summary>看完整拆解</summary><div class="drawer-grid"><div><h3>画面</h3><p>{esc(zh(interp.get('production_pattern'), '待补充'))}</p><h3>用了什么证明</h3><p>{esc('、'.join(zh(x, '待确认的画面或口播') for x in clean_list(interp.get('proof_devices'))) or '还没有找到')}</p></div><div><h3>不要照抄</h3><ul>{''.join(f'<li>{esc(zh(x, x))}</li>' for x in no_copy[:5])}</ul><h3>结尾</h3><p>{esc(zh(interp.get('cta'), '没有明确行动'))}</p></div></div></details>
          <button class="mobile-primary {'ready' if enabled else 'guarded'}" onclick="choose(this,'{'use' if enabled else 'inspect'}')">{esc(button_label)}</button>
        </div>'''
    else:
        lead_html = '''<div class="empty-state"><b>今天还没有可拆解的视频</b><p>系统会继续按已确定的对标范围查找；也可以直接放入一条本地视频开始。</p></div>'''

    # Mechanism intelligence: group exact reviewed labels and preserve source media.
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in reviewed_rows:
        narrative = (row["analysis"].get("interpretations") or {}).get("narrative_structure") or []
        label = (narrative[0] if narrative else None) or row["task"].get("borrow_mechanism") or "待主编归纳"
        groups.setdefault(zh(label), []).append(row)

    cluster_html = ""
    for index, (label, members) in enumerate(groups.items(), 1):
        thumbs = "".join(f'<button class="thumb" onclick="openMaterial(\'{esc(m["evidence"].get("creative_id"))}\')" aria-label="查看代表素材">{poster_markup(m)}</button>' for m in members[:4])
        signal = evidence_label(members[0]["evidence"])
        cluster_html += f'''<article class="cluster-row"><div class="cluster-index">{index}</div><div class="cluster-copy"><div class="cluster-meta">{len(members)} 条素材 · {esc(signal)}</div><h3>{esc(label)}</h3><p>这些素材用了相近的画面、口播和成交顺序。点开任一原片，就能看它具体怎么做。</p></div><div class="thumb-strip">{thumbs}</div></article>'''
    if not cluster_html:
        cluster_html = '<div class="empty-state">今天还没有发现反复出现、值得单独总结的素材打法。</div>'

    library_html = ""
    for row in display_rows:
        evidence, analysis, task = row["evidence"], row["analysis"], row["task"]
        interp = analysis.get("interpretations") or {}
        media = evidence.get("media") or {}
        metrics = metric_strip(evidence)
        transcript = (analysis.get("observations") or {}).get("transcript") or []
        transcript_text = " ".join(x.get("text", "") for x in transcript if x.get("text"))
        transcript_note = transcript_text if float((analysis.get("confidence") or {}).get("transcript") or 0) >= .35 else "这条视频可用语音较少，系统主要依据画面拆解。"
        cid = evidence.get("creative_id") or row["run"].name
        material_state = {"adopt":"今天推荐","hold":"留作参考"}.get(current_decision(task),"可以参考")
        library_html += f'''<article class="material" id="m-{esc(cid)}" data-creative="{esc(cid)}"><div class="material-video">{video_markup(row, "library-video")}<span class="duration">{int(float(media.get('duration_sec') or 0))}秒</span></div><div class="material-body"><div class="material-meta"><span>{esc(evidence.get('platform','本地素材'))} · @{esc((evidence.get('author') or {}).get('display_name') or '原作者')}</span><span>{short_date(evidence.get('published_at'))}</span></div><h3>{esc(zh(interp.get('opening_hook') or task.get('borrow_mechanism'), '待拆解素材'))}</h3><div class="metrics">{metrics or '<span>暂无可靠互动指标</span>'}</div><div class="tags"><span>{esc(evidence_label(evidence))}</span><span>{material_state}</span></div><details class="full-breakdown"><summary>看完整拆解和判断过程</summary>{whitebox_html(analysis, transcript_note)}</details></div></article>'''
    if not library_html:
        library_html = '<div class="empty-state">素材库为空，新素材入库后会自动出现在这里。</div>'
    deep_ids = {r["evidence"].get("creative_id") for r in display_rows}
    batch_ids={row.get("creative_id") for row in candidates}
    batch_deep_count=sum(1 for creative_id in deep_ids if creative_id in batch_ids)
    funnel_deep_count=funnel.get("deep_reviewed",batch_deep_count) if daily_intel else batch_deep_count
    pending_html = "".join(
        f'''<article class="candidate"><div><span>{esc(c.get('platform','公开渠道'))} · @{esc(c.get('author_name') or '原作者')}</span><b>{esc(c.get('title') or '待深度拆解素材')}</b></div><div><span>{compact((c.get('search_metrics') or {}).get('likes'))} 赞</span><a href="{esc(c.get('canonical_url'))}" target="_blank" rel="noreferrer">看原片</a></div></article>'''
        for c in candidates if c.get("creative_id") not in deep_ids
    )
    lead_creative_id=(lead or {}).get("evidence",{}).get("creative_id")
    shortlist_html="".join(f'''<article class="short-card {'chosen' if row.get('creative_id')==lead_creative_id else ''}"><div><span>#{esc(row.get('rank'))} · {esc(row.get('platform') or '公开渠道')} · @{esc(row.get('author_name') or '原作者')}</span><b>{esc(row.get('title') or '待查看素材')}</b></div><p>{esc('推荐：'+row.get('reason') if row.get('creative_id')==lead_creative_id else row.get('reason'))}</p><footer><span>{esc('推荐' if row.get('creative_id')==lead_creative_id else plain_shortlist_status(row.get('status')))}</span>{f'<a href="{esc(row.get("canonical_url"))}" target="_blank" rel="noreferrer">看原片</a>' if row.get('canonical_url') else ''}</footer></article>''' for row in shortlist[:8])
    if not shortlist_html:shortlist_html='<div class="empty-state">今天还没有取得候选素材；系统不会用历史数量冒充今日结果。</div>'

    recent_decisions = decisions[-8:]
    memory_items = "".join(f'<li><b>{esc({"adopt":"已选用","use":"已选用","hold":"先放一放","reject":"已跳过"}.get(d.get("decision"), "已记录"))}</b><span>{esc((d.get("decided_at") or d.get("created_at") or "")[:10])}</span></li>' for d in recent_decisions)
    memory_html = memory_items or '<li class="memory-empty">还没有人工决策。从今天开始，系统会自动记住你用过和跳过的方向。</li>'
    observed_accounts=[str(value) for value in watch.get("seed_accounts",[]) if isinstance(value,str) and value][:8]
    observation_html="".join(f"<li><b>@{esc(name)}</b><span>持续关注</span></li>" for name in observed_accounts) or '<li class="memory-empty">系统还在学习哪些账号真正与你相关；反复出现有用素材的账号会自动留下。</li>'

    styles = r'''
:root{--paper:#f6f3ec;--card:#fffefa;--ink:#26231f;--muted:#716b61;--navy:#142f4f;--navy2:#234d78;--gold:#bf9418;--line:#ddd6c9;--green:#186c54;--orange:#a65f22;--shadow:0 14px 36px rgba(33,37,41,.09)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif}button,textarea{font:inherit}button{cursor:pointer}.serif{font-family:"Songti SC","STSong","Noto Serif SC",serif}.shell{max-width:1180px;margin:auto;padding:28px 28px 70px}.mast{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:3px double var(--navy);padding-bottom:16px}.mast h1{color:var(--navy);font-size:30px;line-height:1.2;margin:0 0 7px;letter-spacing:.03em}.mast p{margin:0;color:var(--muted)}.date{text-align:right;color:var(--muted);font-size:13px}.date b{display:block;color:var(--navy);font-size:15px}.context-strip{display:flex;gap:18px;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid var(--line);color:var(--muted);font-size:13px}.context-strip b{color:var(--ink)}.tabs{display:flex;gap:3px;border-bottom:2px solid var(--navy);position:sticky;top:0;background:rgba(246,243,236,.97);z-index:10;padding-top:12px}.tab{border:0;background:none;color:var(--muted);font-weight:750;padding:10px 15px 8px;border-bottom:4px solid transparent}.tab[aria-selected="true"]{color:var(--navy);border-color:var(--gold)}.page{display:none;padding-top:26px}.page.active{display:block}.section-head{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:18px}.section-head h2{margin:0;color:var(--navy);font-size:25px}.section-head p{margin:4px 0 0;color:var(--muted)}.daily-summary{color:var(--navy);font-weight:700}.lead{display:grid;grid-template-columns:minmax(300px,.82fr) minmax(380px,1.18fr);background:var(--card);box-shadow:var(--shadow);border-top:5px solid var(--navy);min-height:480px}.lead-media{background:#111;position:relative;min-height:480px;display:grid;place-items:center}.lead-video{display:block;width:100%;height:480px;object-fit:contain;background:#111}.media-caption{position:absolute;left:0;right:0;bottom:0;padding:22px 16px 12px;background:linear-gradient(transparent,rgba(0,0,0,.82));color:white;display:flex;justify-content:space-between;font-size:12px}.lead-copy{padding:34px 38px}.decision-state{display:inline-block;background:var(--navy);color:white;padding:3px 10px;font-size:12px;letter-spacing:.08em}.lead-copy h2{font-size:29px;line-height:1.35;color:var(--navy);margin:18px 0 12px}.lead-answer{font-size:17px;margin:0 0 20px}.why-grid{display:grid;grid-template-columns:92px 1fr;gap:9px 14px;border-top:1px solid var(--line);padding-top:18px}.why-grid dt{color:var(--gold);font-weight:800}.why-grid dd{margin:0}.decision-actions{display:flex;align-items:center;gap:16px;margin-top:25px}.primary{border:0;background:var(--gold);color:#1d180b;font-weight:850;padding:12px 20px;min-height:46px}.primary.ready{background:var(--green);color:white}.primary.guarded{background:var(--gold)}.text-button{border:0;background:none;color:var(--muted);text-decoration:underline;text-underline-offset:3px}.primary:focus-visible,.text-button:focus-visible,.tab:focus-visible,summary:focus-visible{outline:3px solid #4d8ed2;outline-offset:3px}.correction{margin-top:12px;color:var(--muted);font-size:13px}.correction summary,.evidence-drawer summary,.material summary{cursor:pointer;text-decoration:underline;text-underline-offset:3px}.correction-body{display:grid;gap:8px;margin-top:10px}.correction textarea{width:100%;min-height:72px;border:1px solid var(--line);padding:10px;background:white}.quiet{justify-self:start;border:1px solid var(--navy);background:white;color:var(--navy);padding:7px 11px}.evidence-drawer{border-top:1px dashed var(--line);margin-top:24px;padding-top:13px}.drawer-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;padding-top:12px}.drawer-grid h3{font-size:13px;color:var(--gold);margin:8px 0 3px}.drawer-grid p,.drawer-grid ul{margin:0}.drawer-grid ul{padding-left:18px}.brief-band{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin-top:20px}.brief-band div{background:var(--card);padding:18px}.brief-band b{display:block;color:var(--navy);font-size:20px}.brief-band span{color:var(--muted);font-size:12px}.cluster-row{display:grid;grid-template-columns:40px minmax(260px,.85fr) minmax(360px,1.15fr);gap:22px;align-items:center;border-top:1px solid var(--line);padding:24px 0}.cluster-index{font:700 30px/1 Georgia,serif;color:var(--gold)}.cluster-meta{color:var(--gold);font-size:12px;font-weight:800}.cluster-copy h3{color:var(--navy);font-size:20px;line-height:1.42;margin:4px 0 7px}.cluster-copy p{color:var(--muted);margin:0}.thumb-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;min-height:150px}.thumb{padding:0;border:0;background:#111;min-width:0}.thumb-video{display:block;width:100%;height:150px;object-fit:cover;pointer-events:none}.library-tools{display:flex;gap:10px}.library-tools input{min-width:260px;border:1px solid var(--line);background:white;padding:9px 12px}.library-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.material{background:var(--card);border:1px solid var(--line)}.material:has(.full-breakdown[open]){grid-column:1/-1}.material-video{position:relative;background:#111;aspect-ratio:16/11}.material:has(.full-breakdown[open]) .material-video{max-height:520px}.library-video{width:100%;height:100%;display:block;object-fit:contain}.duration{position:absolute;right:8px;bottom:8px;background:rgba(0,0,0,.75);color:white;padding:2px 6px;font-size:11px}.material-body{padding:16px}.material-meta{display:flex;justify-content:space-between;color:var(--muted);font-size:12px}.material h3{color:var(--navy);font-size:17px;line-height:1.45;margin:9px 0}.metrics{display:flex;gap:12px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:9px 0;color:var(--muted);font-size:11px}.metrics b{display:block;color:var(--ink);font-size:14px}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:11px 0}.tags span{border:1px solid var(--line);padding:2px 7px;color:var(--muted);font-size:11px}.full-breakdown{margin-top:14px}.whitebox{margin-top:16px;border-top:1px solid var(--line);padding-top:18px}.wb-logic{font-size:18px;color:var(--navy);max-width:820px}.whitebox h4{font-size:17px;color:var(--navy);margin:24px 0 10px}.wb-step{display:grid;grid-template-columns:80px 1fr;gap:16px;padding:17px 0;border-top:1px solid var(--line)}.wb-step:first-of-type{border-top:0}.wb-time{font-weight:850;color:var(--gold)}.wb-step span{font-size:11px;color:var(--muted)}.wb-step h4{margin:2px 0 8px;color:var(--ink)}.wb-av{display:grid;grid-template-columns:1fr 1fr;gap:9px}.wb-av p,.wb-reason,.wb-transfer>div{background:var(--paper);padding:11px;margin:0}.wb-av b{display:block;color:var(--gold);font-size:11px}.wb-step small,.wb-reason small{color:var(--muted)}.wb-reasons{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}.wb-reason p{margin:6px 0}.wb-table{overflow:auto}.wb-table table{width:100%;border-collapse:collapse}.wb-table th,.wb-table td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}.wb-table th{font-size:11px;color:var(--muted)}.wb-transfer{display:grid;grid-template-columns:1fr 1fr;gap:10px}.pending-whitebox{background:#fff8df;border:1px solid #ead49d;padding:16px}.breakdown{display:grid;grid-template-columns:70px 1fr;gap:6px 10px;margin-top:12px}.breakdown dt{color:var(--gold);font-weight:800}.breakdown dd{margin:0}.pending-head{margin:34px 0 12px;border-top:2px solid var(--navy);padding-top:18px}.pending-head h3{color:var(--navy);margin:0}.pending-head p{color:var(--muted);margin:3px 0}.candidate-list{background:var(--card);border:1px solid var(--line)}.candidate{display:grid;grid-template-columns:1fr auto;gap:20px;padding:13px 16px;border-top:1px solid var(--line)}.candidate:first-child{border-top:0}.candidate div{display:flex;gap:12px;align-items:center}.candidate span{color:var(--muted);font-size:12px}.candidate b{font-size:14px}.candidate a{color:var(--navy);font-weight:700;white-space:nowrap}.memory-layout{display:grid;grid-template-columns:1fr 1fr;gap:24px}.memory-panel{background:var(--card);border-top:4px solid var(--navy);padding:24px}.memory-panel h3{color:var(--navy);margin:0 0 12px}.memory-panel ul{list-style:none;padding:0;margin:0}.memory-panel li{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding:10px 0}.memory-panel li span{color:var(--muted)}.empty-state,.memory-empty{background:#fffdf6;border:1px dashed var(--line);padding:24px;color:var(--muted)}.system-note{margin-top:42px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:14px}.toast{position:fixed;left:50%;bottom:26px;transform:translate(-50%,20px);background:var(--navy);color:white;padding:11px 18px;opacity:0;pointer-events:none;transition:.2s ease-out;z-index:50}.toast.show{opacity:1;transform:translate(-50%,0)}@media(max-width:820px){.shell{padding:18px 16px 50px}.mast{grid-template-columns:1fr}.date{text-align:left}.tabs{overflow-x:auto}.tab{white-space:nowrap;padding-inline:11px}.lead{grid-template-columns:1fr}.lead-media,.lead-video{min-height:0;height:360px}.lead-copy{padding:25px 22px}.lead-copy h2{font-size:24px}.cluster-row{grid-template-columns:32px 1fr}.thumb-strip{grid-column:2}.library-grid{grid-template-columns:repeat(2,1fr)}.memory-layout{grid-template-columns:1fr}.wb-reasons{grid-template-columns:1fr 1fr}}@media(max-width:520px){.shell{padding:14px 14px 50px}.mast h1{font-size:25px}.mast p{font-size:13px}.date{display:flex;justify-content:space-between}.context-strip span:nth-child(2){display:none}.page{padding-top:19px}.section-head{display:block}.section-head h2{font-size:23px}.daily-summary{margin-top:8px}.lead-media,.lead-video{height:275px}.lead-copy{padding:20px 18px}.lead-copy h2{font-size:22px;margin:13px 0 8px}.lead-answer{font-size:15px}.why-grid,.drawer-grid,.wb-av,.wb-transfer{grid-template-columns:1fr}.why-grid dt{margin-top:5px}.decision-actions{align-items:stretch;flex-direction:column}.primary{width:100%}.brief-band{grid-template-columns:1fr}.cluster-row{grid-template-columns:28px 1fr;gap:12px}.thumb-strip{grid-template-columns:repeat(3,1fr);min-height:122px}.thumb-video{height:122px}.library-tools input{min-width:0;width:100%}.library-grid{grid-template-columns:1fr}.material-meta{gap:10px}.candidate{grid-template-columns:1fr}.candidate div{align-items:flex-start;flex-direction:column;gap:3px}.memory-layout{grid-template-columns:1fr}.wb-step{grid-template-columns:1fr}.wb-reasons{grid-template-columns:1fr}}
/* Mobile action stays visible; it is the same single action, not a second decision. */
.mobile-primary{display:none}
.thumb img{display:block;width:100%;height:150px;object-fit:cover}
.mast,.context-strip,.section-head,.lead-copy,.cluster-copy,.material-body,.candidate{min-width:0}
.pending-pool{margin-top:32px;border-top:2px solid var(--navy);padding-top:14px}.pending-pool>summary{cursor:pointer;color:var(--navy);font-weight:800}.pending-pool .pending-head{margin:12px 0;border:0;padding:0}.pending-pool .candidate-list{max-height:560px;overflow:auto}
.today-pool{margin-top:28px}.today-pool h3{margin:0;color:var(--navy);font-size:21px}.today-pool>p{margin:3px 0 14px;color:var(--muted)}.short-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.short-card{background:var(--card);border:1px solid var(--line);padding:14px;display:flex;flex-direction:column;min-height:190px}.short-card.chosen{border:2px solid var(--gold);padding:13px}.short-card div span{display:block;color:var(--muted);font-size:11px}.short-card b{display:block;margin-top:7px;line-height:1.45}.short-card p{color:var(--muted);font-size:13px;flex:1}.short-card footer{display:flex;justify-content:space-between;gap:8px;font-size:12px}.short-card footer span{color:var(--gold);font-weight:800}.short-card a{color:var(--navy)}
.task-card{margin-top:24px;background:var(--navy);color:white;padding:24px}.task-card-head{display:flex;justify-content:space-between;gap:20px}.task-card-head span{color:#e4c35f;font-weight:800;font-size:12px}.task-card h3{font-size:22px;margin:3px 0}.task-card-head p{margin:0;color:#c8d3df}.task-card .quiet{background:transparent;color:white;border-color:#93a8be;align-self:start}.task-focus{background:white;color:var(--ink);padding:14px 18px;margin:18px 0}.task-focus b{color:var(--gold)}.task-focus p{font-size:17px;margin:3px 0}.task-card>ol{padding-left:22px}.task-card>ol li{padding:9px 0;border-top:1px solid rgba(255,255,255,.17)}.task-card>ol b,.task-card>ol span{display:block}.task-card>ol span{color:#d8e0e7}.task-notes{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.task-notes>div{background:rgba(255,255,255,.08);padding:13px}.task-notes p,.task-notes ul{margin:5px 0}.task-copy{position:fixed;left:-9999px;width:1px;height:1px}
h1,h2,h3,p,dd,.daily-summary,.candidate b{overflow-wrap:anywhere}
@media(max-width:520px){
  .shell{padding-bottom:50px}
  .date{display:block;text-align:left}
  .context-strip{display:grid;grid-template-columns:1fr;gap:3px}
  .daily-summary{font-size:13px}
  .lead-media,.lead-video{height:250px}
  .decision-actions{display:flex}
  .mobile-primary{display:none}
  .thumb img{height:122px}
  .short-grid,.task-notes{grid-template-columns:1fr}.task-card{padding:18px}.task-card-head{display:block}.task-card-head button{margin-top:12px}.short-card{min-height:0}
}
'''

    script = r'''
let queue=JSON.parse(localStorage.getItem('creative_decisions')||'[]');
const staticPreview=location.protocol==='file:'||location.pathname.includes('/static-html/');
function toast(message){const el=document.querySelector('.toast');el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),1800)}
function switchTab(id,button){document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id===id));document.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t===button?'true':'false'));history.replaceState(null,'','#'+id);window.scrollTo({top:0,behavior:'smooth'})}
function eventId(){return crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+Math.random().toString(36).slice(2)}
async function remember(event){if(staticPreview){toast('这是静态预览，不能保存选择');return false}try{const response=await fetch('/api/decisions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(event)});if(!response.ok)throw new Error('save failed');return true}catch(_){toast('当前连接断开了，我会重新打开可操作版');return false}}
async function choose(button,decision){const card=button.closest('[data-id]');if(decision==='inspect'){card.querySelector('.evidence-drawer').open=true;card.querySelector('.evidence-drawer').scrollIntoView({behavior:'smooth',block:'center'});return}const decidedAt=new Date(),cooldown=decision==='use'?null:new Date(decidedAt.getTime()+3*86400000).toISOString(),event={schema_version:'decision_event/v1',event_id:eventId(),experiment_id:card.dataset.id,decision:decision==='use'?'adopt':'hold',reason:'',decided_by:'human',decided_at:decidedAt.toISOString(),cooldown_until:cooldown,interaction:decision};if(!await remember(event))return;if(decision==='use'){document.querySelectorAll('.primary,.mobile-primary').forEach(b=>{b.textContent='已进入内容制作';b.disabled=true});toast('已经交给内容生产负责人')}else{toast('已经换成下一个方向');setTimeout(()=>location.reload(),500)}}
function correct(button){const box=button.closest('.correction-body'),text=box.querySelector('textarea').value.trim();if(!text){toast('可以不填；只有想纠正系统时再写');return}remember({schema_version:'decision_event/v1',event_id:eventId(),experiment_id:button.closest('[data-id]').dataset.id,decision:'hold',reason:text,decided_by:'human',decided_at:new Date().toISOString(),cooldown_until:null,interaction:'correction'});box.closest('details').open=false;toast('收到，下次会避开这类判断')}
function openMaterial(id){const tab=document.querySelector('[data-tab="library"]');switchTab('library',tab);requestAnimationFrame(()=>{const el=document.getElementById('m-'+CSS.escape(id));if(el){el.scrollIntoView({behavior:'smooth',block:'start'});el.querySelector('video')?.play().catch(()=>{})}})}
function filterMaterials(input){const q=input.value.trim().toLowerCase();document.querySelectorAll('.material').forEach(el=>el.hidden=q&&!el.textContent.toLowerCase().includes(q))}
async function copyTask(button){const text=button.closest('.task-card').querySelector('.task-copy').value;try{await navigator.clipboard.writeText(text);toast('已复制，可以直接发给团队')}catch(_){const area=button.closest('.task-card').querySelector('.task-copy');area.style.position='static';area.style.width='100%';area.style.height='180px';area.select();toast('请复制这张任务卡文字')}}
window.addEventListener('load',()=>{const id=location.hash.slice(1);const tab=document.querySelector(`[data-tab="${id}"]`);if(tab)switchTab(id,tab);if(staticPreview){document.querySelectorAll('.decision-actions,.correction').forEach(el=>el.hidden=true);const lead=document.querySelector('.lead-copy');if(lead){const note=document.createElement('p');note.className='preview-note';note.textContent='当前是静态预览，仅供查看。请使用系统自动打开的可操作版。';lead.appendChild(note)}}})
'''

    doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(company)} · {esc(desk_title)}</title><style>{styles}</style></head><body><div class="shell">
    <header class="mast"><div><h1 class="serif">{esc(desk_title)}</h1><p>今天找到 {funnel.get('discovered',len(candidates))} 条素材，选出 {1 if lead else 0} 个选题。</p></div><div class="date"><b>{esc(company)}</b>{today}</div></header>
    <div class="context-strip"><span>当前目标 <b>{esc(goal)}</b></span><span>当前重点 <b>{esc(priority)}</b></span><span>今天找到 <b>{funnel.get('discovered',len(candidates))} 条</b> · 推荐 <b>{1 if lead else 0} 条</b> · 已拆解 <b>{funnel_deep_count} 条</b> · 跳过重复 <b>{funnel.get('already_seen',0)} 条</b></span></div>
    <nav class="tabs" aria-label="主导航"><button class="tab" data-tab="today" aria-selected="true" onclick="switchTab('today',this)">今天写什么</button><button class="tab" data-tab="intel" aria-selected="false" onclick="switchTab('intel',this)">今日素材</button><button class="tab" data-tab="library" aria-selected="false" onclick="switchTab('library',this)">原视频</button><button class="tab" data-tab="memory" aria-selected="false" onclick="switchTab('memory',this)">记住了什么</button></nav>
    <main>
      <section class="page active" id="today"><div class="section-head"><div><h2 class="serif">今天推荐这个选题</h2></div><div class="daily-summary">{'已经写好选题和拆解' if lead else '还在找素材'}</div></div><article class="lead" data-id="{esc((lead or {}).get('task',{}).get('experiment_id','empty'))}">{lead_html}</article><div class="brief-band"><div><b>{1 if lead else 0}</b><span>个推荐选题</span></div><div><b>{len(display_rows)}</b><span>条已拆解视频</span></div><div><b>{len(seen)}</b><span>条看过的素材</span></div></div><section class="today-pool"><h3>另外 {len(shortlist)} 条候选</h3><div class="short-grid">{shortlist_html}</div></section></section>
      <section class="page" id="intel"><div class="section-head"><div><h2 class="serif">{esc(intel_title)}</h2><p>{esc(intel_note)}</p></div><div class="daily-summary">{len(groups)} 种常见写法</div></div>{cluster_html}</section>
      <section class="page" id="library"><div class="section-head"><div><h2 class="serif">原视频和拆解</h2></div><div class="library-tools"><input type="search" placeholder="搜索开场、卖点或作者" oninput="filterMaterials(this)" aria-label="搜索素材"></div></div><div class="library-grid">{library_html}</div>{f'<details class="pending-pool"><summary>还有 {max(0,len(candidates)-len(deep_ids))} 条没有拆解</summary><div class="candidate-list">{pending_html}</div></details>' if pending_html else ''}</section>
      <section class="page" id="memory"><div class="section-head"><div><h2 class="serif">记住了什么</h2></div></div><div class="memory-layout"><section class="memory-panel"><h3>最近选过</h3><ul>{memory_html}</ul></section><section class="memory-panel"><h3>重复素材</h3><p>已经看过 {len(seen)} 条。相同视频不会重复推荐。</p></section><section class="memory-panel"><h3>持续关注的账号</h3><ul>{observation_html}</ul></section></div></section>
    </main></div><div class="toast" role="status" aria-live="polite"></div><script>{script}</script></body></html>'''
    atomic_write_text(output, doc)
    atomic_write_json(workspace/"current_strategy.json",{
        "schema_version":"current_strategy/v1",
        "updated_at":now(),
        "status":"ready" if lead and action_state((lead or {}).get("task",{}))[2] else "processing",
        "experiment_id":(lead or {}).get("task",{}).get("experiment_id"),
        "creative_id":(lead or {}).get("evidence",{}).get("creative_id"),
        "dashboard":str(output),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--day", help="YYYY-MM-DD，仅用于历史证据复核/验收")
    args = parser.parse_args()
    render(Path(args.workspace), Path(args.out),args.day)
    print(args.out)
