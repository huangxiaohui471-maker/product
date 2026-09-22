#!/usr/bin/env python3
from __future__ import annotations
import argparse,html,json
from pathlib import Path
from continuity import inspect as inspect_continuity
def e(x):return html.escape(str(x or ""))

def read(path:Path)->dict:
 try:return json.loads(path.read_text(encoding="utf-8-sig"))
 except Exception:return {}

def build_from_workspace(workspace:Path)->list[dict]:
 workspace=workspace.resolve();context=read(workspace/"context/shared_enterprise_context.json");strategy=read(workspace/"strategy_to_production.json");production=read(workspace/"production_run.json");handoff=read(workspace/"production_to_growth.json");growth=read(workspace/"growth_learning_return.json");state=read(workspace/"task_state.json");continuity=inspect_continuity(workspace)
 done=[bool(context),bool(strategy and strategy.get("status")=="ready_for_production"),bool(handoff),bool(handoff),bool(growth),bool(growth and state.get("current_ring")=="upgrade")]
 labels=("发现","判断","生产","触达","复盘","升级");first_open=next((i for i,value in enumerate(done) if not value),None)
 rings=[{"label":label,"status":"done" if done[i] else "current" if i==first_open else "waiting"} for i,label in enumerate(labels)]
 issues=(continuity.get("issues") or []);owner={"strategy_lead":"策略负责人","production_lead":"生产负责人","growth_lead":"增长负责人","orchestrator":"飞轮总控"}.get(state.get("current_owner"),"飞轮总控")
 if issues:
  status="需要接回";blocked="有成果文件没有写回岗位状态";next_action=issues[0]["action"]
 else:
  status="正在进行" if first_open is not None else "本轮完成";blocked="没有卡住";next_action=state.get("next_action") or ("开始认识企业" if not context else "继续当前一步")
 completed=[]
 if context:completed.append("企业资料已经读懂")
 if strategy and strategy.get("status")=="ready_for_production":completed.append("方向已经交给生产")
 if handoff:completed.append("作品已经交给增长")
 if growth:completed.append("真实结果已经复盘")
 return [{"kind":"当前内容任务","title":state.get("task_name") or "这一轮内容飞轮","status_text":status,"current_owner":state.get("current_owner") or "orchestrator","rings":rings,"completed":"；".join(completed) or "还没有可验收结果","blocked_at":blocked,"next_action":f"{owner}：{next_action}","boundary":"状态只来自真实交接；账号基线与本轮作品效果不会拼成一件事"}]
def render(cycles:list[dict])->str:
 cards=[]
 for c in cycles:
  current=c.get("current_owner")
  roles=(("strategy_lead","策略负责人","找方向、做判断"),("production_lead","生产负责人","把方向做成作品"),("growth_lead","增长负责人","触达、复盘、送回学习"))
  team=''.join(f'<div class="role {"active" if key==current else ""}"><b>{name}</b><span>{job}</span><em>{"正在接手" if key==current else "等待接力"}</em></div>' for key,name,job in roles)
  rings="".join(f'<span class="ring {"done" if x.get("status")=="done" else "now" if x.get("status")=="current" else ""}">{e(x.get("label"))}</span>' for x in c.get("rings") or [])
  cards.append(f'''<article class="task"><div class="top"><div><div class="eyebrow">{e(c.get('kind'))}</div><h2>{e(c.get('title'))}</h2></div><span class="state">{e(c.get('status_text'))}</span></div><div class="team">{team}</div><div class="rings">{rings}</div><div class="facts"><div><b>已经完成</b><p>{e(c.get('completed'))}</p></div><div><b>现在卡在</b><p>{e(c.get('blocked_at'))}</p></div><div><b>下一步</b><p>{e(c.get('next_action'))}</p></div></div><small>{e(c.get('boundary'))}</small></article>''')
 return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI内容飞轮驾驶舱</title><style>
:root{{--ink:#0e213b;--paper:#f4f6f9;--line:#dce3ec;--blue:#2b67f6;--green:#168568;--muted:#657285}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1160px;margin:auto;padding:44px 24px 80px}}header{{background:var(--ink);color:white;padding:42px;border-radius:28px}}h1{{font-size:clamp(34px,5vw,58px);line-height:1.08;margin:8px 0}}header p{{font-size:18px;color:#c6d3e4}}.eyebrow{{font-weight:800;color:#74e2c0}}.task{{background:white;border:1px solid var(--line);border-radius:22px;padding:26px;margin-top:18px}}.top{{display:flex;justify-content:space-between;gap:20px}}h2{{font-size:25px;margin:5px 0}}.state{{height:max-content;background:#e7f0ff;color:#1648a8;padding:7px 12px;border-radius:999px;font-weight:800}}.team{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px 0}}.role{{border:1px solid var(--line);border-radius:14px;padding:14px;display:grid;gap:3px;color:var(--muted)}}.role b{{color:var(--ink)}}.role span{{font-size:13px}}.role em{{font-style:normal;font-size:12px}}.role.active{{border-color:var(--blue);background:#eef4ff}}.role.active em{{color:var(--blue);font-weight:800}}.rings{{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin:20px 0}}.ring{{text-align:center;padding:9px 4px;border-radius:10px;background:#edf0f4;color:#8a94a3}}.ring.done{{background:#d9f4e9;color:var(--green)}}.ring.now{{background:#dce8ff;color:#1648a8;font-weight:800}}.facts{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.facts div{{background:#f7f9fb;padding:15px;border-radius:13px}}.facts p{{margin:5px 0}}small{{display:block;color:var(--muted);margin-top:15px}}@media(max-width:720px){{main{{padding:15px 13px 50px}}header{{padding:28px 22px}}.top{{display:block}}.state{{display:inline-block}}.team{{grid-template-columns:1fr}}.rings{{grid-template-columns:repeat(3,1fr)}}.facts{{grid-template-columns:1fr}}}}
</style></head><body><main><header><div class="eyebrow">AI内容飞轮总控</div><h1>今天到哪一步，<br>一眼就知道。</h1><p>这里只显示真的完成、真的等待和真的下一步。</p></header>{''.join(cards) or '<article class="task">目前没有真实任务。</article>'}</main></body></html>'''
def main():
 p=argparse.ArgumentParser();p.add_argument("path",type=Path);p.add_argument("legacy_output",type=Path,nargs="?");p.add_argument("--workspace",type=Path);p.add_argument("--cycles",type=Path);a=p.parse_args()
 output=a.legacy_output or a.path
 if a.legacy_output:cycles=json.loads(a.path.read_text(encoding="utf-8"))
 elif a.workspace:cycles=build_from_workspace(a.workspace)
 elif a.cycles:cycles=json.loads(a.cycles.read_text(encoding="utf-8"))
 else:raise SystemExit("需要 --workspace")
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(render(cycles),encoding="utf-8");print(output);return 0
if __name__=="__main__":raise SystemExit(main())
