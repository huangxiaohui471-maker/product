#!/usr/bin/env python3
"""同行流量雷达 · 当日汇报摘要生成器

用法:
  python3 _build/radar_brief.py --date 2026-09-22 [--runs _build/runs]

作用: 读取当日各步产物 + 自动找出更早一期做对比，输出 7 个问题的结论摘要。
只读，不改任何产物；用于生成每日 14 行汇报。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(p: Path) -> dict:
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def earlier_runs(runs: Path, date: str) -> list[str]:
    """返回早于 date 的期次日期列表（倒序）。"""
    dates = sorted(
        {p.name[:10] for p in runs.glob("20*-*.json") if len(p.name) >= 11 and p.name[:4].isdigit()},
        reverse=True,
    )
    return [d for d in dates if d < date]


def find_prev(runs: Path, date: str, stem: str) -> tuple[str, dict]:
    """找最近一期含该产物的期次。"""
    for d in earlier_runs(runs, date):
        p = runs / f"{d}-{stem}.json"
        if p.exists():
            return d, load(p)
    return "", {}


def n(v) -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return str(v)


# ---------- 1 抖音深挖：新进榜 + 美妆占比 ----------
def q1(runs: Path, date: str) -> list[str]:
    out: list[str] = []
    deep = load(runs / f"{date}-deep.json")
    accs = [a for a in (deep.get("accounts") or []) if not a.get("error")]
    prev_d, prev = find_prev(runs, date, "deep")
    prev_names = {a.get("nickname") for a in (prev.get("accounts") or []) if not a.get("error")}

    new_accs = [a for a in accs if a.get("nickname") not in prev_names]
    qual = [a for a in new_accs if (a.get("beauty_share") or 0) >= 0.30]
    out.append(f"[1] 抖音深挖 {len(accs)} 号（对比期 {prev_d or '无'}，新进 {len(new_accs)} 个）")
    if qual:
        for a in sorted(qual, key=lambda x: -(x.get("beauty_share") or 0)):
            out.append(
                f"    ✅ 新进且达标 {a.get('nickname')}｜{n(a.get('fans'))}粉｜"
                f"美妆占比 {a.get('beauty_share'):.0%}｜爆款率 {a.get('hit_rate')}｜{a.get('verdict')}"
            )
    else:
        out.append("    ⚠️ 新进榜账号中美妆占比≥30% 的：无")
    for a in new_accs:
        if a not in qual:
            out.append(
                f"    · 新进未达标 {a.get('nickname')}｜美妆占比 "
                f"{(a.get('beauty_share') or 0):.0%}｜{a.get('verdict')}"
            )
    return out


# ---------- 2 抖音素材榜 低粉高赞 top3 ----------
def q2(runs: Path, date: str) -> list[str]:
    d = load(runs / f"{date}-rival.json")
    mats = [m for m in (d.get("materials") or []) if (m.get("flags") or {}).get("low_fans_hot")]
    out = [f"[2] 素材榜「低粉高赞」命中 {len(mats)} 条，前 3："]
    for i, m in enumerate(mats[:3], 1):
        out.append(
            f"    {i}. {m.get('author_nickname')}｜{n(m.get('author_fans'))}粉 / {n(m.get('likes'))}赞"
            f"｜{'/'.join(m.get('matched_terms') or [])}｜{m.get('title')}"
        )
    if not mats:
        out.append("    ⚠️ 无")
    return out


# ---------- 3 小红书 收藏>点赞 + 账号榜 ----------
def q3(runs: Path, date: str) -> list[str]:
    d = load(runs / f"{date}-xhs.json")
    mats = d.get("materials") or []
    tool = [m for m in mats if (m.get("collects") or 0) > (m.get("likes") or 0)]
    out = [f"[3] 小红书 {d.get('notes_total')} 笔记 / {d.get('accounts_total')} 账号；"
           f"「收藏>点赞」工具型 {len(tool)} 条："]
    for m in tool:
        out.append(
            f"    · {n(m.get('likes'))}赞/{n(m.get('collects'))}藏｜{m.get('author')}｜{m.get('title')}"
        )
    if not tool:
        out.append("    ⚠️ 无")
    accs = sorted(d.get("accounts") or [], key=lambda a: -(a.get("top_score") or 0))[:3]
    out.append("    账号榜（按代表作热度）Top3：" + "；".join(
        f"{a.get('author')}({n(a.get('top_score'))})" for a in accs))
    return out


# ---------- 4 TikTok 内容侧 ----------
def q4(runs: Path, date: str) -> list[str]:
    d = load(runs / f"{date}-tiktok.json")
    reg = d.get("region_actual") or {}
    total = sum(reg.values()) or 1
    us = reg.get("US", 0)
    out = [f"[4] TikTok region=US 实收 {us}/{total} = {us / total:.0%}"
           f"（{d.get('videos_total')} 视频 / {d.get('accounts_total')} 号）"
           + ("⚠️ 美国内容偏少" if us / total < 0.30 else "✅ 达标")]
    lf = [a for a in (d.get("accounts") or []) if a.get("low_fan_hit")]
    out.append(f"    低粉高赞账号 {len(lf)} 个，前 3（粉丝量级 + 作品均播放）：")
    for i, a in enumerate(lf[:3], 1):
        out.append(
            f"    {i}. {a.get('author')}｜{a.get('fans_text')} 粉｜均播 {n(a.get('avg_plays'))}"
            f"｜{a.get('region')}｜{a.get('top_title')}"
        )
    out.append("    素材榜前 3 条选题结构：")
    for i, m in enumerate((d.get("materials") or [])[:3], 1):
        out.append(
            f"    {i}. 播放 {n(m.get('plays'))}｜{m.get('author')}｜{m.get('duration_s')}s"
            f"｜[{m.get('keyword')}]｜{m.get('title')}"
        )
    if d.get("errors"):
        out.append(f"    ⚠️ 未取到的词：{'；'.join(d['errors'])}")
    return out


# ---------- 5 抖音美妆商品榜第一 ----------
def q5(runs: Path, date: str) -> list[str]:
    d = load(runs / f"{date}-market.json")
    rows = ((d.get("rank") or {}).get("rows") or [])
    if not rows:
        reason = (d.get("rank") or {}).get("reason") or "商品榜未取到（webbridge / 蝉妈妈登录态）"
        return [f"[5] ⚠️ 销量榜缺失：{reason}"]
    r = rows[0]
    live, video, card = r.get("live_sold") or 0, r.get("video_sold") or 0, r.get("card_sold") or 0
    tot = max(1, live + video + card)
    driver = "直播" if live / tot > 0.7 else ("视频" if video / tot > 0.5 else "混合")
    out = [
        f"[5] 抖音美妆商品榜第一：{r.get('title')}",
        f"    销量 {n(r.get('sold'))} 件（{r.get('sold_text')}）｜结构：直播 {live / tot:.0%} / "
        f"视频 {video / tot:.0%} / 商品卡 {card / tot:.0%} → 主要靠 {driver} 在拉"
        f"｜关联达人 {n(r.get('creators'))}／视频 {n(r.get('videos'))}",
    ]
    pv = find_prev(runs, date, "market")
    if pv[1]:
        prows = ((pv[1].get("rank") or {}).get("rows") or [])
        if prows:
            out.append(f"    对比期({pv[0]})第一：{prows[0].get('title')}｜{n(prows[0].get('sold'))} 件"
                       f"｜直播 {n(prows[0].get('live_sold'))} / 视频 {n(prows[0].get('video_sold'))}")
    return out


# ---------- 6 人群痛点前 5 + 新词 ----------
def q6(runs: Path, date: str) -> list[str]:
    d = load(runs / f"{date}-market.json")
    pts = d.get("pain_points") or []
    if not pts:
        return ["[6] ⚠️ 人群痛点缺失（webbridge/蝉妈妈不可用）"]
    top5 = pts[:5]
    out = [f"[6] 痛点榜前 5（共 {len(pts)} 词）：" + "；".join(
        f"#{p.get('rank')}{p.get('name')}(热度{p.get('heat')}/互动{n(p.get('interaction_count'))})"
        for p in top5)]
    prev_d, prev = find_prev(runs, date, "market")
    if prev:
        ppts = prev.get("pain_points") or []
        pnames = {p.get("name") for p in ppts}
        # 榜单后端被平台截断（各期长度不同），只在 top100 窗口内比较「新冒头」
        fresh = [p for p in pts[:100] if p.get("name") not in pnames]
        if fresh:
            brief = "/".join(f"{p.get('name')}(热度{p.get('heat')})" for p in fresh[:12])
            out.append(f"    对比期 {prev_d}（{len(pnames)} 词）：top100 内新冒头 {len(fresh)} 个 → {brief}")
        else:
            out.append(f"    对比期 {prev_d}（{len(pnames)} 词）：top100 内零新词，仍是同集换位")
        # top20 内部换位
        prev_rank = {p.get("name"): p.get("rank") for p in (prev.get("pain_points") or [])}
        moves = []
        for p in pts[:20]:
            nm = p.get("name")
            if nm in prev_rank and prev_rank[nm] != p.get("rank"):
                moves.append(f"{nm} #{prev_rank[nm]}→#{p.get('rank')}")
        if moves:
            out.append(f"    top20 换位：{'；'.join(moves[:8])}")
    return out


# ---------- 7 卖点覆盖 top3 + 变化 ----------
def q7(runs: Path, date: str) -> list[str]:
    d = load(runs / f"{date}-claims.json")
    cl = d.get("claims") or []
    if not cl:
        return ["[7] ⚠️ 卖点数据缺失"]
    top = sorted(cl, key=lambda c: -(c.get("coverage") or 0))[:3]
    out = [f"[7] 卖点覆盖 top3（样本 {d.get('sample_size')} 商品）：" + "；".join(
        f"{c.get('label')} {c.get('coverage')}" for c in top)]
    ing = sorted(d.get("ingredients") or [], key=lambda c: -(c.get("coverage") or 0))[:3]
    if ing:
        out.append("    成分 top3：" + "；".join(f"{c.get('label')} {c.get('coverage')}" for c in ing))
    prev_d, prev = find_prev(runs, date, "claims")
    if prev:
        ptop = sorted(prev.get("claims") or [], key=lambda c: -(c.get("coverage") or 0))[:3]
        same = [c.get("label") for c in top] == [c.get("label") for c in ptop]
        pcont = {c.get("label"): c.get("coverage") for c in (prev.get("claims") or [])}
        out.append(f"    对比期 {prev_d}：{'名单未变' if same else '名单有变化'}｜"
                   + "；".join(f"{c.get('label')} {pcont.get(c.get('label'), '新增')}→{c.get('coverage')}"
                               for c in top))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--runs", default="_build/runs")
    args = ap.parse_args()
    runs = Path(args.runs)
    lines: list[str] = []
    for fn in (q1, q2, q3, q4, q5, q6, q7):
        try:
            lines.extend(fn(runs, args.date))
        except Exception as exc:  # noqa: BLE001
            lines.append(f"    ⚠️ {fn.__name__} 计算失败: {exc}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
