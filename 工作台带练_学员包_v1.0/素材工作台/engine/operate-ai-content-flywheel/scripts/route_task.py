#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def route(intent:dict)->dict:
 goal=intent.get("goal")
 context=bool(intent.get("context_ready"));strategy=bool(intent.get("strategy_ready"));production=bool(intent.get("production_adopted"));touch=bool(intent.get("touch_recorded"));result=bool(intent.get("result_ready"))
 if not context:return {"owner":"strategy_lead","ring":"discovery","action":"先读企业资料，生成共同底稿","reason":"还没有可共同引用的企业理解"}
 if goal in {"find_direction","market_intelligence"}:return {"owner":"strategy_lead","ring":"discovery","action":"发现并判断今天最值得测试的方向","reason":"任务需要新的市场机会判断"}
 if goal in {"make_content","revise_content"}:
  if not strategy:return {"owner":"strategy_lead","ring":"judgment","action":"先把客户、场景、主张和单变量钉住","reason":"生产不能重新猜策略"}
  return {"owner":"production_lead","ring":"production","action":"制作并比较内容版本","reason":"策略已确认"}
 if goal in {"publish","touch"}:
  if not production:return {"owner":"production_lead","ring":"production","action":"先做出一个可以使用的版本","reason":"目前还没有具体作品"}
  return {"owner":"growth_lead","ring":"touch","action":"安排真实使用并记录结果","reason":"已经有可以使用的作品"}
 if goal in {"review","diagnose"}:
  if not touch:return {"owner":"growth_lead","ring":"touch","action":"先补真实触达事实","reason":"没有发布或投用事实不能复盘"}
  if not result:return {"owner":"growth_lead","ring":"review","action":"等待或回收真实结果","reason":"结果还没到"}
  return {"owner":"growth_lead","ring":"review","action":"复盘并提出下一实验","reason":"触达和结果已具备"}
 if goal=="upgrade":return {"owner":"orchestrator","ring":"upgrade","action":"把本轮经验写回并开始下一轮","reason":"让三个工位共用同一条新经验"}
 return {"owner":"orchestrator","ring":"judgment","action":"把老板目标拆成一个明确内容任务","reason":"当前目标还不能安全派工"}
def main():
 p=argparse.ArgumentParser();p.add_argument("intent",type=Path);a=p.parse_args();print(json.dumps(route(json.loads(a.intent.read_text(encoding="utf-8"))),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
