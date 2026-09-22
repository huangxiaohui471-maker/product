#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


def e(value) -> str:
    return html.escape(str(value if value not in (None, "") else "暂时没有"))


def plain_variable(value) -> str:
    raw = value.get("name") if isinstance(value, dict) else value
    return {"opening_hook": "开场第一句话", "headline": "标题", "cta": "最后的行动引导", "visual": "画面表达", "structure": "内容顺序"}.get(str(raw or ""), str(raw or "一个关键动作"))


def plain_cta(value) -> str:
    text = str(value or "")
    return text.split("，")[-1].strip() if "，" in text else text


def extract_script_text(source: str) -> str:
    """Pull the actual speech out of a generated HTML artifact without an iframe."""
    if not source:
        return ""
    match = re.search(r'<div[^>]+class=["\'][^"\']*\bfull\b[^"\']*["\'][^>]*>(.*?)</div>', source, re.I | re.S)
    body = match.group(1) if match else ""
    if not body:
        return ""
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"</p\s*>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", "", body)
    return html.unescape(body).strip()


def render(bundle: dict, artifact_source: str = "", interactive: bool = False, action_state: dict | None = None) -> str:
    locked = bundle.get("locked_strategy") or {}
    line = bundle.get("production_line") or {}
    candidates = bundle.get("script_candidates") or []
    selected_ref = bundle.get("selected_script")
    selected_id = selected_ref.get("candidate_id") if isinstance(selected_ref, dict) else selected_ref
    if not selected_id and len(candidates) == 1:
        selected_id = candidates[0].get("candidate_id")
    selected = next((row for row in candidates if row.get("candidate_id") == selected_id), None)
    artifact = bundle.get("current_artifact") or bundle.get("adopted_artifact") or {}
    artifact_path = artifact.get("path") or artifact.get("locator") or ""
    artifact_href = Path(artifact_path).name if artifact_path else ""
    artifact_kind = artifact.get("kind") or artifact.get("type") or ""
    title = (selected or {}).get("title") or (selected or {}).get("hook") or "当前作品还在生成"
    pending_checks = (selected or {}).get("claim_checks") or []
    if artifact_kind == "script":
        status = "口播稿已经写好，使用前还要核对" if pending_checks else "口播稿已经写好，可以进入拍摄"
        action_label = "查看完整口播稿"
    elif artifact_path:
        status, action_label = f"{len(candidates)} 篇文案已经写好", "打开全文"
    else:
        status, action_label = "内容还在写", "打开内容"
    script_text = extract_script_text(artifact_source)
    state_done = bool((action_state or {}).get("status") == "ready_for_shooting")
    if artifact_kind == "script" and interactive:
        if pending_checks:
            action = '<p class="waiting"><b>这版还不能拍。</b>把上面的正确说法告诉我，我会直接改进成品。</p>'
        else:
            button_label = "已经进入拍摄" if state_done else "进入拍摄"
            action = f'<button class="primary" id="advance" onclick="advance(\'ready_for_shooting\')" {"disabled" if state_done else ""}>{e(button_label)}</button>'
    elif artifact_href:
        action = f'<a class="secondary-link" href="{e(artifact_href)}">另开原文件</a>'
    else:
        action = '<span class="waiting">作品生成后会直接出现在这里</span>'
    checks = "".join(f"<li>{e(x)}</li>" for x in pending_checks) or "<li>没有需要补充核对的信息</li>"
    current_warning = f'''<aside class="truth-warning"><b>使用前还要核对</b><ul>{checks}</ul></aside>''' if pending_checks else ""
    evidence = "".join(f"<li>{e(x)}</li>" for x in (selected or {}).get("evidence_refs") or locked.get("material_refs") or []) or "<li>这次没有单独引用外部素材</li>"
    versions = []
    for row in candidates:
        current = row.get("candidate_id") == selected_id
        body = ''.join(f'<p>{e(p)}</p>' for p in re.split(r'\n+', str(row.get('body') or '')) if p.strip())
        versions.append(f'''<details class="version {'current' if current else ''}" {'open' if current else ''}><summary><span>{'推荐先发' if current else '另一篇'}</span><h3>{e(row.get('title') or row.get('hook'))}</h3><p>{e(row.get('hook'))}</p></summary><div class="candidate-body">{body}</div><p class="candidate-cta"><b>结尾：</b>{e(plain_cta(row.get('cta')))}</p></details>''')
    suite = (bundle.get("image_suites") or [])[-1] if bundle.get("image_suites") else {}
    images = "".join(f'''<article class="asset"><b>{e(item.get('job'))}</b><span>{e(item.get('channel_position'))}</span></article>''' for item in suite.get("items") or [])
    line_label = {"sales-content": "销售内容", "short-video": "短视频", "image-suite": "图片"}.get(line.get("line_id"), line.get("label") or "内容")
    recipe = bundle.get("production_recipe") or {}
    method_label = {"ntf-v4": "NTF 销售内容方法", "native": "原生渠道内容方法"}.get(recipe.get("content_method"), recipe.get("content_method") or "当前生产方法")
    method_sentence = "写清客户的问题、产品和下一步，再生成完整文案。" if line.get("line_id") == "sales-content" else "生成可以直接拍摄和发布的脚本。" if line.get("line_id") == "short-video" else "生成封面、解释图、证明图和行动图。"
    variable_label = plain_variable(locked.get("single_variable") or {})
    cta_label = plain_cta((selected or {}).get("cta") or locked.get("desired_action"))
    channel = str((locked.get("touch_destination") or {}).get("channel") or "").lower()
    channel_label = {"xiaohongshu": "小红书正文", "douyin": "抖音脚本", "wechat": "公众号文章", "wechat-mp": "公众号文章"}.get(channel, "完整正文")
    script_block = ''.join(f'<p>{e(paragraph)}</p>' for paragraph in re.split(r'\n+', script_text) if paragraph.strip())
    if not script_block:
        script_block = f'<p>{e((selected or {}).get("body"))}</p>'
    shelf = []
    for row in candidates:
        recommended = row.get("candidate_id") == selected_id
        preview = " ".join(str(row.get("body") or "").split())[:110]
        shelf.append(f'''<article class="shelf-card {'recommended' if recommended else ''}"><span>{'推荐先发' if recommended else '完整文案'}</span><h3>{e(row.get('title') or row.get('hook'))}</h3><b>{e(row.get('hook'))}</b><p>{e(preview)}…</p><button onclick="switchTab('versions',document.querySelector('[data-tab=versions]'))">查看全文</button></article>''')
    return f'''<!doctype html><html lang="zh-CN" data-interactive="{str(interactive).lower()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>内容生产工作台</title><style>
:root{{--paper:#f6f3ec;--card:#fffefa;--ink:#26231f;--muted:#716b61;--navy:#142f4f;--gold:#bf9418;--line:#ddd6c9;--green:#186c54;--shadow:0 14px 36px rgba(33,37,41,.09)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}.shell{{max-width:1180px;margin:auto;padding:28px 28px 70px}}.serif{{font-family:"Songti SC","STSong",serif}}.mast{{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:3px double var(--navy);padding-bottom:16px}}.mast h1{{color:var(--navy);font-size:30px;line-height:1.2;margin:0 0 7px}}.mast p,.date{{margin:0;color:var(--muted)}}.date{{text-align:right;font-size:13px}}.date b{{display:block;color:var(--navy);font-size:15px}}.context{{display:flex;gap:18px;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid var(--line);color:var(--muted);font-size:13px}}.context b{{color:var(--ink)}}.tabs{{display:flex;gap:3px;border-bottom:2px solid var(--navy);position:sticky;top:0;background:rgba(246,243,236,.97);z-index:10;padding-top:12px}}.tab{{border:0;background:none;color:var(--muted);font:inherit;font-weight:750;padding:10px 15px 8px;border-bottom:4px solid transparent;cursor:pointer}}.tab[aria-selected="true"]{{color:var(--navy);border-color:var(--gold)}}.page{{display:none;padding-top:26px}}.page.active{{display:block}}.section-head h2{{color:var(--navy);font-size:25px;margin:0}}.section-head p{{color:var(--muted);margin:3px 0 18px}}
.lead{{display:grid;grid-template-columns:minmax(260px,.72fr) minmax(430px,1.28fr);background:var(--card);box-shadow:var(--shadow);border-top:5px solid var(--navy)}}.lead-side{{background:var(--navy);color:white;padding:34px;display:flex;flex-direction:column;justify-content:space-between}}.lead-side span{{color:#e4c35f;font-weight:800}}.lead-side strong{{font-size:24px;line-height:1.35;margin:12px 0}}.lead-side p{{color:#cad5df}}.lead-main{{padding:36px 40px}}.state{{display:inline-block;background:var(--gold);color:#1d180b;padding:3px 10px;font-size:12px;font-weight:800}}.lead-main h2{{color:var(--navy);font-size:30px;line-height:1.35;margin:18px 0 10px}}.hook{{font-size:17px}}.script{{background:var(--paper);border-left:4px solid var(--gold);padding:18px 22px;margin:20px 0;max-height:520px;overflow:auto}}.script p{{font-size:16px;margin:0 0 1em}}.primary{{border:0;display:inline-block;background:var(--gold);color:#1d180b;font:inherit;font-weight:850;padding:12px 20px;text-decoration:none;min-height:46px;cursor:pointer}}.primary:disabled{{background:#d8d0bc;color:#6f685c;cursor:default}}.secondary-link{{color:var(--navy);font-weight:750;margin-left:14px}}.waiting{{color:var(--muted)}}.why{{display:grid;grid-template-columns:110px 1fr;gap:9px 16px;border-top:1px solid var(--line);margin-top:22px;padding-top:18px}}.why dt{{color:var(--gold);font-weight:800}}.why dd{{margin:0}}.truth-warning{{margin-top:18px;background:#fff8df;border:1px solid #dfc678;padding:14px 17px}}.truth-warning b{{color:#755400}}.truth-warning ul{{margin:6px 0 0}}.toast{{position:fixed;left:50%;bottom:24px;transform:translate(-50%,20px);opacity:0;background:var(--navy);color:white;padding:11px 18px;transition:.2s;pointer-events:none}}.toast.show{{opacity:1;transform:translate(-50%,0)}}
.package-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);margin-bottom:22px}}.package-grid article{{background:var(--card);padding:20px}}.package-grid b,.package-grid span{{display:block}}.package-grid b{{color:var(--navy);font-size:18px}}.package-grid span{{color:var(--muted)}}.method-hero{{display:grid;grid-template-columns:.7fr 1.3fr;background:var(--card);border-top:5px solid var(--navy);margin-bottom:22px}}.method-name{{background:var(--navy);color:white;padding:28px}}.method-name span{{color:#e4c35f;font-size:12px;font-weight:800}}.method-name h3{{font-size:24px;margin:8px 0}}.method-copy{{padding:28px 32px}}.method-copy h3{{color:var(--navy);margin:0 0 8px}}.method-copy p{{margin:0}}.flow{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line)}}.flow div{{background:var(--card);padding:20px}}.flow b{{display:block;color:var(--navy);font-size:18px}}.flow span{{color:var(--muted)}}.versions{{display:grid;gap:16px}}.version{{background:var(--card);border:1px solid var(--line);padding:0}}.version.current{{border-top:5px solid var(--gold)}}.version summary{{padding:20px;cursor:pointer}}.version summary>span{{color:var(--gold);font-size:12px;font-weight:800}}.version h3{{color:var(--navy);margin:7px 0}}.candidate-body{{padding:4px 24px 20px;border-top:1px solid var(--line);max-width:78ch}}.candidate-body p{{margin:1em 0}}.candidate-cta{{padding:0 24px 20px}}.proof{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}.proof section{{background:var(--card);border-top:4px solid var(--navy);padding:22px}}.proof h3{{margin:0;color:var(--navy)}}.assets{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line)}}.asset{{background:var(--card);padding:18px}}.asset b,.asset span{{display:block}}.asset span{{color:var(--muted)}}ul{{padding-left:20px}}.empty{{background:var(--card);padding:24px;color:var(--muted)}}
@media(max-width:760px){{.shell{{padding:16px 14px 50px}}.mast{{grid-template-columns:1fr}}.date{{text-align:left}}.tabs{{overflow:auto}}.tab{{white-space:nowrap;min-height:44px}}.lead,.method-hero{{grid-template-columns:1fr}}.lead-side,.lead-main{{padding:24px 20px}}.lead-main h2{{font-size:24px}}.package-grid,.flow,.versions,.proof,.assets{{grid-template-columns:1fr}}.why{{grid-template-columns:1fr}}}}
</style><style>.content-shelf{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.shelf-card{{background:var(--card);border-top:4px solid var(--navy);padding:22px;display:flex;flex-direction:column;min-height:310px}}.shelf-card.recommended{{border-color:var(--gold)}}.shelf-card>span{{color:var(--gold);font-size:12px;font-weight:800}}.shelf-card h3{{color:var(--navy);font-size:20px;line-height:1.4;margin:8px 0}}.shelf-card>b{{color:var(--muted)}}.shelf-card p{{flex:1}}.shelf-card button{{align-self:flex-start;border:0;background:var(--navy);color:white;padding:9px 14px;font:inherit;cursor:pointer}}@media(max-width:760px){{.content-shelf{{grid-template-columns:1fr}}}}</style></head><body><div class="shell"><header class="mast"><div><h1 class="serif">内容生产工作台</h1><p>文案、图片和视频都放在这里。</p></div><div class="date"><b>内容生产负责人</b>{e(status)}</div></header>
<div class="context"><span>内容类型 <b>{e(line_label)}</b></span><span>写给 <b>{e(locked.get('target_audience'))}</b></span><span>希望他 <b>{e(locked.get('desired_action'))}</b></span></div>
<nav class="tabs"><button class="tab" data-tab="package" aria-selected="true" onclick="switchTab('package',this)">做好的内容</button><button class="tab" data-tab="versions" aria-selected="false" onclick="switchTab('versions',this)">查看全文</button><button class="tab" data-tab="materials" aria-selected="false" onclick="switchTab('materials',this)">参考素材</button><button class="tab" data-tab="line" aria-selected="false" onclick="switchTab('line',this)">这次的写法</button></nav><main>
<section class="page active" id="package"><div class="section-head"><h2 class="serif">这次写好了 {len(candidates)} 篇</h2></div><div class="package-grid"><article><b>{len(candidates)} 篇文案</b><span>每篇都是完整稿</span></article><article><b>{e(channel_label)}</b><span>正文已经写好</span></article><article><b>{len(suite.get('items') or [])} 张图片</b><span>{'图片已经做好' if images else '这次还没有做图片'}</span></article></div><div class="content-shelf">{''.join(shelf)}</div>{('<h2 class="serif">配套图片</h2><div class="assets">'+images+'</div>') if images else ''}</section>
<section class="page" id="versions"><div class="section-head"><h2 class="serif">{len(candidates)} 篇完整文案</h2></div><div class="versions">{''.join(versions) or '<div class="empty">文案还没写好。</div>'}</div>{(f'<details class="version current" open><summary><span>{e(channel_label)}</span><h3>{e(title)}</h3><p>正文如下。</p></summary><div class="candidate-body">{script_block}</div>{action}{current_warning}</details>') if artifact_path else ''}</section>
<section class="page" id="materials"><div class="section-head"><h2 class="serif">参考素材</h2></div><div class="proof"><section><h3>用了这些资料</h3><ul>{evidence}</ul></section><section><h3>发布前看一眼</h3><ul>{checks}</ul></section></div></section>
<section class="page" id="line"><div class="section-head"><h2 class="serif">这次用了什么写法</h2></div><article class="method-hero"><div class="method-name"><span>使用</span><h3>{e(line_label)}</h3><p>{e(method_label)}</p></div><div class="method-copy"><h3>用来做什么</h3><p>{e(method_sentence)}</p></div></article><div class="flow"><div><b>客户</b><span>{e(locked.get('target_audience'))}</span></div><div><b>场景</b><span>{e(locked.get('customer_scene'))}</span></div><div><b>开场</b><span>{e(variable_label)}</span></div><div><b>结尾</b><span>{e(cta_label)}</span></div></div></section>
</main><div class="toast" id="toast">已进入拍摄</div></div><script>function switchTab(id,button){{document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id===id));document.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t===button?'true':'false'));window.scrollTo({{top:0,behavior:'smooth'}})}}async function advance(action){{const b=document.getElementById('advance');if(!b)return;try{{const r=await fetch('/api/advance',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:'{{"action":"ready_for_shooting"}}'}});if(!r.ok)throw 0;b.disabled=true;b.textContent='已进入拍摄';const t=document.getElementById('toast');t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200)}}catch(_){{alert('连接断开了，请重新打开工作台')}}}}</script></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("bundle", type=Path); parser.add_argument("output", type=Path); parser.add_argument("--interactive",action="store_true"); args = parser.parse_args()
    bundle=json.loads(args.bundle.read_text(encoding="utf-8"));artifact=bundle.get("current_artifact") or bundle.get("adopted_artifact") or {};artifact_path=Path(artifact.get("path") or artifact.get("locator") or "")
    if artifact_path and not artifact_path.is_absolute(): artifact_path=args.output.parent/artifact_path.name
    source=artifact_path.read_text(encoding="utf-8") if artifact_path.is_file() else ""
    state_path=args.output.parent/".production-workbench-state.json"
    try:state=json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:state={}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(render(bundle,source,args.interactive,state), encoding="utf-8"); print(args.output); return 0


if __name__ == "__main__": raise SystemExit(main())
