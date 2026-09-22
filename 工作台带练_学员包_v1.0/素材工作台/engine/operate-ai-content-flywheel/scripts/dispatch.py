#!/usr/bin/env python3
"""One plain-language front door. It returns the next role entry without exposing internals."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from workspace_snapshot import build


def intent(text: str, current: str) -> str:
    value = text.strip().lower()
    if any(x in value for x in ("白皮书", "读一下", "读资料", "这个文件夹", "理解这门生意", "对这门生意的理解", "了解我的公司")):
        return "learn_company"
    if any(x in value for x in ("怎么样", "到哪", "进度", "驾驶舱", "全局")):
        return "show_status"
    if any(x in value for x in ("自动任务", "每天找", "每周复盘", "定时")):
        return "configure_automation"
    if any(x in value for x in ("复盘", "最近一周", "最近7天", "账号")):
        return "review_results"
    if any(x in value for x in ("找素材", "收集素材", "相关的素材", "找内容", "今天做什么", "策略工作台", "开工", "市场")):
        return "find_direction"
    if any(x in value for x in ("做成内容", "做出来", "写脚本", "做图片", "做视频", "继续制作")):
        return "make_content"
    if value in {"继续", "就这个", "用这个方向", "接着做"}:
        return current
    return current


def dispatch(text: str, workspace: Path) -> dict:
    state = build(workspace)
    goal = intent(text, state["current"])
    if goal == "learn_company" or not state["context_ready"]:
        goal = "learn_company"
    # A visible artifact without its handoff is not "done". Repair the nearest
    # broken handoff before pretending the flywheel can continue normally.
    issue_codes={row.get("code") for row in (state.get("continuity") or {}).get("issues",[])}
    if goal in {"show_status","make_content","review_content","review_results","wait_or_review_results","next_cycle"} and "UNTRACKED_PRODUCTION" in issue_codes:
        goal="recover_production"
    elif goal in {"show_status","review_results","wait_or_review_results","next_cycle"} and "UNTRACKED_GROWTH" in issue_codes:
        goal="recover_growth"
    routes = {
        "learn_company": ("strategy_lead", "读取企业资料并生成白皮书", "我先把公司资料读懂，白皮书整理好后会直接继续。"),
        "building_whitepaper": ("strategy_lead", "继续整理企业白皮书", "我正在整理公司资料，你暂时不用操作。"),
        "find_direction": ("strategy_lead", "寻找今天值得做的内容方向", "我去找今天值得参考的素材，并替你挑出一个首选方向。"),
        "make_content": ("production_lead", "沿当前方向制作内容", "方向已经接住，我会继续把它做成内容。"),
        "review_content": ("production_lead", "完成当前内容版本", "内容首版已经出来；需要你看时，我只会指出最重要的一处。"),
        "review_results": ("growth_lead", "抓取最近7天并形成复盘", "我会回收最近7天的内容结果，再给出下一周只改什么。"),
        "wait_or_review_results": ("growth_lead", "等待或回收真实结果", "作品已经记下，真实结果回来后我会自动复盘。"),
        "next_cycle": ("strategy_lead", "读取复盘并开始下一轮", "上一轮已经复盘，我会按新结论继续找下一轮方向。"),
        "show_status": ("orchestrator", "刷新内容飞轮驾驶舱", "我会把现在到哪一步、已经有什么和下一步做什么放在一页里。"),
        "configure_automation": ("orchestrator", "设置每天找素材和每周复盘", "每天找素材、每周复盘会按你的时间运行；需要暂停时直接告诉我。"),
        "recover_production": ("production_lead", "把已有作品接回当前任务", "刚才的作品还没有接回当前方向。我先替你整理好，再继续下一步。"),
        "recover_growth": ("growth_lead", "把已有复盘接回内容底账", "刚才的复盘还没有挂回对应内容。我先把事实和判断接好，再给下一步。"),
    }
    owner, action, message = routes[goal]
    return {"owner": owner, "goal": goal, "action": action, "learner_message": message, "snapshot": state}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    parser.add_argument("text")
    args = parser.parse_args()
    print(json.dumps(dispatch(args.text, args.workspace), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
