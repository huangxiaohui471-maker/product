#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from validate_diagnosis import ladder


def e(value) -> str:
    return html.escape(str(value if value not in (None, "") else "暂时没有"))


def front(value) -> str:
    text = str(value if value not in (None, "") else "暂时没有")
    return html.escape(text.replace("单变量改写", "只改一处").replace("单变量", "只改一处"))


def li(values) -> str:
    return "".join(f"<li>{e(value)}</li>" for value in values or [])


def metric_line(snapshot: dict) -> str:
    data = snapshot.get("public_metrics") or {}
    labels = (("plays", "播放"), ("likes", "点赞"), ("comments", "评论"), ("shares", "分享"), ("collects", "收藏"))
    return " · ".join(f"{label} {data[key]}" for key, label in labels if isinstance(data.get(key), (int, float))) or "公开数据还不完整"


def short_title(value: str, length: int = 32) -> str:
    value = " ".join(str(value or "未命名内容").split())
    value = value.split("#", 1)[0].strip()
    value = re.split(r"[。！？?!🤯]", value, maxsplit=1)[0].strip()
    return value if len(value) <= length else value[:length] + "…"


def trend_chart(contents: list[dict]) -> str:
    points = []
    for row in sorted(contents, key=lambda x: str(x.get("published_at") or "")):
        data = ((row.get("snapshots") or [{}])[-1].get("public_metrics") or {})
        value = sum(data.get(k) or 0 for k in ("likes", "comments", "shares", "collects"))
        if any(isinstance(data.get(k), (int, float)) for k in ("likes", "comments", "shares", "collects")):
            points.append((row, value))
    if not points:
        return '<div class="empty">数据回来后，这里会出现表现趋势。</div>'
    width, height, left, top, bottom = 760, 250, 44, 22, 46
    usable_w, usable_h, high = width-left-18, height-top-bottom, max(v for _,v in points) or 1
    coords=[]
    for i,(row,value) in enumerate(points):
        coords.append((left+usable_w*i/max(1,len(points)-1), top+usable_h*(1-value/high), row, value))
    path=" ".join(("M" if i==0 else "L")+f" {x:.1f} {y:.1f}" for i,(x,y,_,_) in enumerate(coords))
    marks="".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5"><title>{e(short_title(row.get("title"),18))}：{value}</title></circle><text x="{x:.1f}" y="{height-18}" text-anchor="middle">{e(str(row.get("published_at") or "")[:10][5:])}</text>' for x,y,row,value in coords)
    return f'''<div class="chart"><svg viewBox="0 0 {width} {height}" role="img" aria-label="内容公开互动趋势"><line x1="{left}" y1="{top+usable_h}" x2="{width-18}" y2="{top+usable_h}"/><path d="{path}"/>{marks}</svg><p>按发布时间排列；每个点是点赞、评论、分享和收藏的合计。</p></div>'''


def render(ledger: dict, diagnosis: dict, interactive: bool = False, action_state: dict | None = None) -> str:
    all_contents = ledger.get("items") or []
    reviewed_ids = {row.get("content_id") for row in diagnosis.get("items") or []}
    contents = [row for row in all_contents if row.get("content_id") in reviewed_ids]
    waiting = diagnosis.get("waiting_items") or [
        {"content_id": row.get("content_id"), "title": short_title(row.get("title")), "reason": "还没发布或数据还没回来"}
        for row in all_contents if row.get("content_id") not in reviewed_ids
    ]
    by_id = {row["content_id"]: row for row in contents}
    ladders = [ladder(row) for row in diagnosis.get("items") or []]
    review = diagnosis.get("account_review") or {}
    top_items = review.get("top_items") or []
    low_items = review.get("low_items") or []
    conclusions = review.get("conclusions") or ["这批内容还没有形成账号层结论。"]
    plan = review.get("next_week_plan") or [(diagnosis.get("weekly_summary") or {}).get("next_action") or "下一条只换开场，其他不变。"]
    headline = plan[0]
    metric_name = review.get("metric") or "公开表现"
    metric_label = "点赞、评论、分享、收藏相加后的中位数" if metric_name == "公开互动" else f"{metric_name}中位数"
    action_done = bool((action_state or {}).get("status") == "next_task_ready")
    hero_item = top_items[0] if top_items else {}
    hero_content = by_id.get(hero_item.get("content_id"), {})
    hero_snap = (hero_content.get("snapshots") or [{}])[-1]
    trend_html = trend_chart(contents)

    rank_rows = []
    for label, rows in (("表现最好", top_items), ("表现较低", low_items)):
        for row in rows:
            content = by_id.get(row.get("content_id"), {})
            snap = (content.get("snapshots") or [{}])[-1]
            rank_rows.append(f'''<article class="rank"><span>{e(label)}</span><h3>{e(short_title(content.get('title') or row.get('title')))}</h3><p>{e(metric_line(snap))}</p></article>''')

    detail_rows = []
    for row in ladders:
        content = by_id.get(row.get("content_id"), {})
        snap = (content.get("snapshots") or [{}])[-1]
        observation = (row.get("observations") or ["目前还没有形成判断"])[0]
        detail_rows.append(f'''<details class="content-row"><summary><span class="content-title">{e(short_title(content.get('title')))}</span><span class="content-metric">{e(metric_line(snap))}</span></summary><div class="detail-body"><p class="finding">{front(observation)}</p><dl><dt>可能原因</dt><dd>{front(row.get('primary_explanation'))}</dd><dt>下次改什么</dt><dd>{front(row.get('next_experiment'))}</dd></dl><div class="facts"><b>数据</b><ul>{li(row.get('facts'))}</ul></div></div></details>''')

    group_rows = []
    for group in review.get("content_groups") or []:
        group_rows.append(f'''<tr><td>{e(group.get('name'))}</td><td>{e(group.get('count'))} 条</td><td>平均 {e(group.get('metric'))} {e(group.get('average'))}</td></tr>''')
    method_records = [row for row in contents if row.get("production_line") or row.get("production_recipe")]
    method_note = "这些内容记录了当时使用的写法，可以直接比较。" if method_records else "旧内容没有记录当时用了什么写法，目前只能比较题材和数据。"
    method_links = []
    for row in method_records:
        line_raw = row.get("production_line") or "内容生产线"
        line = line_raw.get("label") or line_raw.get("name") or "内容生产线" if isinstance(line_raw, dict) else line_raw
        recipe_raw = row.get("production_recipe")
        recipe = (recipe_raw.get("label") or recipe_raw.get("name") or recipe_raw.get("content_method")) if isinstance(recipe_raw, dict) else recipe_raw
        recipe_text = f" · {recipe}" if recipe else ""
        method_links.append(
            f'''<article class="method-link"><h4>{e(short_title(row.get('title')))}</h4><p>这条内容来自：{e(line)}{e(recipe_text)}</p></article>'''
        )

    if interactive:
        action_html = f'''<button class="primary" id="next-action" onclick="startNext()" {"disabled" if action_done else ""}>{"下一轮已经开始" if action_done else "按这个结论开始下一轮"}</button><p class="action-note">{"已经交给内容策略负责人，它会沿着这个结论继续。" if action_done else "点击后会直接交给内容策略负责人。"}</p>'''
    else:
        action_html = '<p class="action-note">要继续时，回到对话说“按这个结论开始下一轮”。</p>'
    return f'''<!doctype html><html lang="zh-CN" data-interactive="{str(interactive).lower()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>内容复盘工作台</title><style>
:root{{--paper:#f6f3ec;--card:#fffefa;--ink:#26231f;--muted:#716b61;--navy:#142f4f;--gold:#bf9418;--line:#ddd6c9;--green:#186c54;--shadow:0 14px 36px rgba(33,37,41,.09)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}.shell{{max-width:1180px;margin:auto;padding:28px 28px 70px}}.serif{{font-family:"Songti SC","STSong",serif}}.mast{{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:3px double var(--navy);padding-bottom:16px}}.mast h1{{color:var(--navy);font-size:30px;line-height:1.2;margin:0 0 7px}}.mast p,.date{{margin:0;color:var(--muted)}}.date{{text-align:right;font-size:13px}}.date b{{display:block;color:var(--navy);font-size:15px}}.context{{display:flex;gap:18px;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid var(--line);color:var(--muted);font-size:13px}}.context b{{color:var(--ink)}}.tabs{{display:flex;gap:3px;border-bottom:2px solid var(--navy);position:sticky;top:0;background:rgba(246,243,236,.97);z-index:10;padding-top:12px}}.tab{{border:0;background:none;color:var(--muted);font:inherit;font-weight:750;padding:10px 15px 8px;border-bottom:4px solid transparent;cursor:pointer}}.tab[aria-selected="true"]{{color:var(--navy);border-color:var(--gold)}}.page{{display:none;padding-top:26px}}.page.active{{display:block}}.section-head h2{{color:var(--navy);font-size:25px;margin:0}}.section-head p{{color:var(--muted);margin:3px 0 18px}}
.lead{{display:grid;grid-template-columns:minmax(310px,.85fr) minmax(430px,1.15fr);background:var(--card);box-shadow:var(--shadow);border-top:5px solid var(--navy)}}.lead-left{{background:var(--navy);color:white;padding:34px}}.lead-left span{{color:#e4c35f;font-size:12px;font-weight:800}}.lead-left h2{{font-size:27px;line-height:1.4;margin:13px 0}}.lead-left p{{color:#cbd6e0}}.lead-right{{padding:34px 38px}}.lead-right>span{{display:inline-block;background:var(--gold);color:#1d180b;padding:3px 10px;font-size:12px;font-weight:800}}.lead-right h2{{color:var(--navy);font-size:27px;line-height:1.4;margin:16px 0}}.judgments{{border-top:1px solid var(--line);padding-top:14px}}.judgments li{{margin:7px 0}}.primary{{border:0;background:var(--gold);color:#1d180b;font:inherit;font-weight:850;padding:12px 20px;min-height:46px;cursor:pointer}}.action-note{{color:var(--muted);font-size:12px;margin:7px 0 0}}.toast{{position:fixed;left:50%;bottom:24px;transform:translate(-50%,20px);opacity:0;background:var(--navy);color:white;padding:11px 18px;transition:.2s;pointer-events:none}}.toast.show{{opacity:1;transform:translate(-50%,0)}}.rank-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:22px}}.rank{{background:var(--card);border-top:4px solid var(--navy);padding:20px}}.rank>span{{color:var(--gold);font-weight:800;font-size:12px}}.rank h3{{color:var(--navy);font-size:18px;line-height:1.45;margin:8px 0}}.rank p{{color:var(--muted);margin:0}}
.status-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin-bottom:22px}}.status-grid article{{background:var(--card);padding:20px}}.status-grid b,.status-grid span{{display:block}}.status-grid b{{font:700 28px Georgia,serif;color:var(--navy)}}.status-grid span{{color:var(--muted)}}.waiting-panel{{background:var(--card);border-left:4px solid var(--gold);padding:18px 22px;margin-top:22px}}.waiting-panel h3{{color:var(--navy);margin:0}}.content-list{{background:var(--card);border:1px solid var(--line)}}.content-row{{border-top:1px solid var(--line)}}.content-row:first-child{{border-top:0}}.content-row>summary{{display:grid;grid-template-columns:1fr auto;gap:20px;padding:17px 19px;cursor:pointer}}.content-title{{font-weight:750;color:var(--navy)}}.content-metric{{color:var(--muted);white-space:nowrap;font-size:12px}}.detail-body{{padding:0 19px 21px}}.finding{{font-size:17px}}dl{{display:grid;grid-template-columns:110px 1fr;gap:9px 15px;border-top:1px solid var(--line);padding-top:15px}}dt{{color:var(--gold);font-weight:800}}dd{{margin:0}}.facts{{background:var(--paper);padding:13px 16px;margin-top:15px}}.facts ul{{margin-bottom:0}}
.method-grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.method-panel{{background:var(--card);border-top:4px solid var(--navy);padding:24px}}.method-panel h3{{color:var(--navy);margin:0 0 10px}}.method-links{{grid-column:1/-1;display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.method-link{{background:var(--card);border-top:3px solid var(--gold);padding:15px 18px}}.method-link h4{{color:var(--navy);margin:0 0 5px;font-size:15px}}.method-link p{{color:var(--muted);margin:0}}table{{width:100%;border-collapse:collapse}}td{{padding:11px 5px;border-top:1px solid var(--line)}}.plan{{counter-reset:step;background:var(--card);border-top:5px solid var(--navy);padding:8px 26px}}.plan li{{counter-increment:step;display:grid;grid-template-columns:44px 1fr;gap:12px;padding:19px 0;border-top:1px solid var(--line);font-size:17px}}.plan li:first-child{{border-top:0}}.plan li:before{{content:counter(step);font:700 28px Georgia,serif;color:var(--gold)}}.next-band{{margin-top:22px;background:var(--navy);color:white;padding:24px}}.next-band span{{color:#e4c35f;font-weight:800;font-size:12px}}.next-band strong{{display:block;font-size:22px;margin-top:4px;max-width:40ch}}ul{{padding-left:20px}}
@media(max-width:760px){{.shell{{padding:16px 14px 50px}}.mast{{grid-template-columns:1fr}}.date{{text-align:left}}.tabs{{overflow:auto}}.tab{{white-space:nowrap}}.status-grid,.lead,.rank-grid,.method-grid{{grid-template-columns:1fr}}.lead-left,.lead-right{{padding:24px 20px}}.content-row>summary{{grid-template-columns:1fr}}.content-metric{{white-space:normal}}dl{{grid-template-columns:1fr}}}}
</style><style>.analytics-grid{{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(300px,.55fr);gap:18px;margin-bottom:22px}}.chart{{background:var(--card);border-top:4px solid var(--navy);padding:18px}}.chart svg{{display:block;width:100%;height:auto}}.chart line{{stroke:var(--line);stroke-width:1}}.chart path{{fill:none;stroke:var(--gold);stroke-width:4}}.chart circle{{fill:var(--navy);stroke:white;stroke-width:3}}.chart text{{fill:var(--muted);font-size:11px}}.chart p{{color:var(--muted);margin:4px 0 0;font-size:12px}}@media(max-width:760px){{.analytics-grid{{grid-template-columns:1fr}}}}</style></head><body><div class="shell"><header class="mast"><div><h1 class="serif">账号复盘</h1><p>最近发了什么，数据怎么样。</p></div><div class="date"><b>内容增长负责人</b>{len(contents)} 条内容已有数据</div></header>
<div class="context"><span>已有数据 <b>{len(contents)} 条</b></span><span>还没数据 <b>{len(waiting)} 条</b></span><span>互动中位数 <b>{e(review.get('median'))}</b></span></div>
<nav class="tabs"><button class="tab" data-tab="account" aria-selected="true" onclick="switchTab('account',this)">账号数据</button><button class="tab" data-tab="method" aria-selected="false" onclick="switchTab('method',this)">内容对比</button><button class="tab" data-tab="detail" aria-selected="false" onclick="switchTab('detail',this)">每条内容</button><button class="tab" data-tab="next" aria-selected="false" onclick="switchTab('next',this)">接下来做</button></nav><main>
<section class="page active" id="account"><div class="section-head"><h2 class="serif">最近 {len(contents)} 条内容</h2><p>没发布、没数据的内容没有放进来。</p></div><div class="status-grid"><article><b>{len(contents)} 条</b><span>已有数据</span></article><article><b>{len(waiting)} 条</b><span>还在等数据</span></article><article><b>{e(review.get('median'))}</b><span>{e(metric_name)}中位数</span></article></div><div class="analytics-grid">{trend_html}<article class="lead-right"><span>数据说明</span><ul class="judgments">{li(conclusions)}</ul></article></div><div class="section-head"><h2 class="serif">表现最好和较低的内容</h2></div><div class="rank-grid">{''.join(rank_rows) or '<p>数据还不够，暂时不能比较。</p>'}</div>{('<section class="waiting-panel"><h3>还在等数据</h3><ul>'+''.join(f'<li>{e(row.get("title"))}：{e(row.get("reason"))}</li>' for row in waiting)+'</ul></section>') if waiting else ''}</section>
<section class="page" id="detail"><div class="section-head"><h2 class="serif">每条内容的数据</h2></div><div class="content-list">{''.join(detail_rows) or '<p>还没有数据。</p>'}</div></section>
<section class="page" id="method"><div class="section-head"><h2 class="serif">哪类内容表现更好</h2><p>{e(method_note)}</p></div><div class="method-grid"><section class="method-panel"><h3>按题材看</h3><table>{''.join(group_rows) or '<tr><td>旧内容还没有分好题材</td></tr>'}</table></section><section class="method-panel"><h3>目前能判断到这里</h3><p>旧内容没有记录开场、画面和写法，暂时不能判断是哪一步带来了差异。</p><p>新内容会记录这些信息，发布后可以继续比较。</p></section><div class="method-links">{''.join(method_links)}</div></div></section>
<section class="page" id="next"><div class="section-head"><h2 class="serif">接下来做什么</h2></div><ol class="plan">{''.join(f'<li>{front(item)}</li>' for item in plan)}</ol><div class="next-band"><span>先做这件事</span><strong>{front(headline)}</strong></div>{action_html}</section>
</main><div class="toast" id="toast">已经交给内容策略负责人</div></div><script>function switchTab(id,button){{document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id===id));document.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t===button?'true':'false'));window.scrollTo({{top:0,behavior:'smooth'}})}}async function startNext(){{const b=document.getElementById('next-action');if(!b)return;try{{const r=await fetch('/api/start-next',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:'{{"action":"start_next"}}'}});if(!r.ok)throw 0;b.disabled=true;b.textContent='下一轮已经开始';const t=document.getElementById('toast');t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200)}}catch(_){{alert('连接断开了，请重新打开工作台')}}}}</script></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("ledger", type=Path); parser.add_argument("diagnosis", type=Path); parser.add_argument("output", type=Path); parser.add_argument("--interactive",action="store_true"); args = parser.parse_args()
    state_path=args.output.parent/".growth-workbench-state.json"
    try:state=json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:state={}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(render(json.loads(args.ledger.read_text(encoding="utf-8")), json.loads(args.diagnosis.read_text(encoding="utf-8")),args.interactive,state), encoding="utf-8"); print(args.output); return 0


if __name__ == "__main__": raise SystemExit(main())
