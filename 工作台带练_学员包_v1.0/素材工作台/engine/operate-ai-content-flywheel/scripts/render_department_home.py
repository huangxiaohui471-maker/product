#!/usr/bin/env python3
from __future__ import annotations
import argparse,html,json
from pathlib import Path

def read(path):
    try:return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception:return {}
def e(v):return html.escape(str(v or ""))

def project_view(workspace:Path)->dict:
    workspace=workspace.resolve();project=workspace.parent if workspace.name==".content-flywheel" else workspace;engine=workspace if workspace.name==".content-flywheel" or (workspace/"context").is_dir() else workspace/".content-flywheel";handoffs=engine/"handoffs"
    context=read(engine/"context/shared_enterprise_context.json") or read(engine/"config/enterprise_context.json")
    strategy=read(handoffs/"strategy_to_production.json") or read(engine/"strategy_to_production.json")
    runs=sorted(handoffs.glob("production_run_*.json"),key=lambda p:p.stat().st_mtime,reverse=True) if handoffs.is_dir() else [];production=read(runs[0]) if runs else read(engine/"production_run.json")
    growth_task=read(handoffs/"growth_to_strategy.json")
    ledger=read(engine/"growth/content_ledger.json")
    if growth_task:
        current="strategy";headline="上一轮已经复盘，下一轮正在接着做";note=growth_task.get("direction");action="内容策略负责人正在接手";href=""
    elif ledger and (project/"05_复盘成果/复盘工作台.html").is_file():
        current="growth";headline="真实结果已经回来";note="增长负责人已经把账号和单条内容放在同一张台上。";action="打开复盘工作台";href="05_复盘成果/复盘工作台.html"
    elif production.get("status") in {"AWAITING_SELECTION","AWAITING_REVIEW"}:
        current="production";headline="内容首版已经出来了";note="满意就直接用；不满意只说最明显的一处。";action=production.get("next_user_action") or "看一眼首版，说一处要改的地方";href="04_内容成果/内容生产工作台.html"
    elif production:
        current="production"
        if (project/"04_内容成果/内容生产工作台.html").is_file():headline="内容首版已经出来了";note="完整作品、采用的方法和使用前要核对的内容，都在生产台里。";action="打开内容生产工作台";href="04_内容成果/内容生产工作台.html"
        else:headline="内容正在制作";note="系统正在沿着已经定下来的方向继续，不需要你重新解释业务。";action="先不用操作，完成后我会回来找你";href=""
    elif strategy:
        current="production";headline="今天做什么已经定下来了";note="内容生产负责人会沿着同一个方向继续，不重新问你一遍。";action="去看内容怎么做出来";href="04_内容成果/内容生产工作台.html"
    elif context:
        current="strategy";headline="AI已经认识这家公司";note="内容策略负责人正在找今天最值得做的一个方向。";action="继续找今天值得做的内容";href=".content-flywheel/dashboard.html"
    else:
        current="context";headline="先让我认识你的公司";note="把现有资料放进项目就好，不用提前整理。";action="告诉我：你主要卖什么？";href=""
    stages=[("内容策略负责人","正在接手" if current=="strategy" else "本轮方向已留下" if strategy else "等待开始"),("内容生产负责人","正在制作" if current=="production" else "本轮作品已留下" if production else "等待方向"),("内容增长负责人","本轮复盘已留下" if growth_task else "正在复盘" if current=="growth" else "等待真实结果")]
    return {"company":context.get("company") or context.get("enterprise_name") or "AI内容部门","headline":headline,"note":note,"action":action,"href":href,"stages":stages,"documents":len([p for p in project.iterdir() if p.is_file()]) if project.is_dir() else 0,"materials":len((read(engine/"materials/material_library.json").get("items") or []))}

def render(v):
    rows="".join(f'<li><span>{e(a)}</span><b>{e(b)}</b></li>' for a,b in v["stages"]);action=f'<a class="primary" href="{e(v["href"])}">{e(v["action"])}</a>' if v["href"] else f'<span class="waiting">{e(v["action"])}</span>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>内容飞轮驾驶舱</title><style>:root{{--paper:#f6f3ec;--card:#fffefa;--ink:#26231f;--muted:#716b61;--navy:#142f4f;--gold:#bf9418;--line:#ddd6c9;--green:#186c54}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1120px;margin:auto;padding:28px 26px 70px}}header{{border-bottom:3px double var(--navy);padding-bottom:15px}}h1,h2{{font-family:"Songti SC","STSong",serif;color:var(--navy)}}h1{{font-size:30px;margin:0}}header p{{color:var(--muted);margin:4px 0}}.hero{{display:grid;grid-template-columns:.7fr 1.3fr;background:var(--card);margin-top:26px;border-top:5px solid var(--navy);box-shadow:0 14px 36px rgba(33,37,41,.09)}}.side{{background:var(--navy);color:white;padding:34px}}.side span{{color:#e4c35f;font-weight:800}}.side h2{{color:white;font-size:25px;line-height:1.35}}.main{{padding:36px 40px}}.main h2{{font-size:32px;line-height:1.3;margin:0 0 12px}}.main p{{font-size:17px}}.primary{{display:inline-block;background:var(--gold);color:#1d180b;font-weight:850;padding:12px 20px;text-decoration:none;min-height:46px;margin-top:12px}}.team{{display:grid;grid-template-columns:1.25fr .75fr;gap:18px;margin-top:20px}}.card{{background:var(--card);border-top:4px solid var(--navy);padding:22px}}.card h2{{margin:0 0 10px;font-size:20px}}ul{{list-style:none;padding:0;margin:0}}li{{display:flex;justify-content:space-between;gap:16px;padding:13px 0;border-top:1px solid var(--line)}}li:first-child{{border-top:0}}li b{{text-align:right}}.memory strong{{font-size:30px;color:var(--green)}}.memory p{{color:var(--muted)}}.waiting{{color:var(--muted)}}@media(max-width:700px){{main{{padding:16px 14px 50px}}.hero,.team{{grid-template-columns:1fr}}.side,.main{{padding:24px 20px}}.main h2{{font-size:26px}}li{{align-items:flex-start}}}}</style></head><body><main><header><h1>内容飞轮驾驶舱</h1><p>{e(v['company'])} · 一条主线，三位负责人接力</p></header><section class="hero"><div class="side"><span>总控正在接棒</span><h2>这里只告诉你：现在到哪一步，接下来去哪。</h2></div><div class="main"><h2>{e(v['headline'])}</h2><p>{e(v['note'])}</p><small>你现在只做一件事</small>{action}</div></section><section class="team"><div class="card"><h2>三位负责人现在在做什么</h2><ul>{rows}</ul></div><div class="card memory"><h2>已经留在部门里</h2><p><strong>{v['documents']}</strong> 份现有资料</p><p><strong>{v['materials']}</strong> 条可继续使用的素材</p></div></section></main></body></html>'''

def main():
    p=argparse.ArgumentParser();p.add_argument("workspace",type=Path);p.add_argument("output",type=Path);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(render(project_view(a.workspace)),encoding="utf-8");print(a.output)
if __name__=="__main__":main()
