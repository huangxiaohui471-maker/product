#!/usr/bin/env python3
"""Create a conservative first weekly diagnosis from a real content ledger."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def metric(snapshot: dict, name: str):
    value = (snapshot.get("public_metrics") or {}).get(name)
    return value if isinstance(value, (int, float)) else None


def clean_title(value: str, limit: int = 34) -> str:
    title = " ".join(str(value or "未命名内容").split())
    title = title.split("#", 1)[0].strip()
    title = re.split(r"[。！？?!🤯]", title, maxsplit=1)[0].strip()
    return title if len(title) <= limit else title[:limit] + "…"


def _account_review(rows: list[dict]) -> dict:
    candidates = []
    for row in rows:
        snap = (row.get("snapshots") or [{}])[-1]
        likes = metric(snap, "likes")
        plays = metric(snap, "plays")
        reads = metric(snap, "reads")
        comments = metric(snap, "comments")
        shares = metric(snap, "shares")
        collects = metric(snap, "collects")
        interaction = sum(x or 0 for x in (likes, comments, shares, collects)) if any(x is not None for x in (likes, comments, shares, collects)) else None
        value = plays if plays is not None else reads if reads is not None else interaction
        metric_name = "播放" if plays is not None else "阅读" if reads is not None else "公开互动"
        title = row.get("title") or "未命名内容"
        writing = any(word in title for word in ("提示词", "写作", "文案", "AI味"))
        tool_use = any(word in title for word in ("失忆", "效率", "工具"))
        business = any(word in title for word in ("企业", "商业", "机会", "趋势", "DeepSeek", "创业"))
        category = "AI写作" if writing else "AI商业认知" if business else "AI工具使用" if tool_use else "其他"
        candidates.append({
            "content_id": row.get("content_id"), "title": clean_title(title),
            "value": value, "metric": metric_name, "published_at": row.get("published_at"),
            "topic": row.get("topic"), "format": row.get("format"), "category": category,
            "likes": likes, "comments": comments, "shares": shares, "collects": collects,
        })
    known = [x for x in candidates if x["value"] is not None]
    known.sort(key=lambda x: x["value"], reverse=True)
    values = sorted(x["value"] for x in known)
    median = values[len(values) // 2] if values else None
    top = known[:min(2, len(known))]
    low = list(reversed(known[-min(2, len(known)):])) if known else []
    total = sum(values) if values else 0
    top_share = round(sum(x["value"] for x in top[:2]) / total * 100) if total else None
    metric_name = known[0]["metric"] if known else "公开表现"
    conclusions = []
    if median is not None:
        conclusions.append(f"{len(known)} 条内容的{metric_name}中位数是 {median}。")
    if top:
        conclusions.append(f"互动最高：《{top[0]['title']}》，{top[0]['value']}。")
    if top_share is not None and len(known) >= 3:
        conclusions.append(f"前两条占全部{metric_name}的 {top_share}%。")
    if not conclusions:
        conclusions.append("公开数据还不完整，先补齐作品表现再判断账号方向。")
    conclusions.append("这里没有成交数据。")
    category_rows = []
    for category in ("AI写作", "AI工具使用", "AI商业认知", "其他"):
        group = [x for x in known if x.get("category") == category]
        if group:
            category_rows.append({"name": category, "count": len(group), "average": round(sum(x["value"] for x in group) / len(group), 1), "metric": metric_name})
    next_week = []
    if top:
        next_week.append(f"再写一条《{top[0]['title']}》同类题材，换一个开场。")
    if len(top) > 1:
        next_week.append(f"《{top[1]['title']}》留作对照，题材、形式和结尾不变。")
    if low:
        next_week.append(f"重写《{low[0]['title']}》的第一屏或前 3 秒，正文不动。")
    return {
        "kind": "account_baseline",
        "content_count": len(rows), "known_count": len(known), "metric": metric_name,
        "median": median, "top_items": top, "low_items": low, "content_groups": category_rows,
        "conclusions": conclusions, "next_week_plan": next_week[:3],
        "missing_for_business_judgment": ["咨询或留资", "成交", "投放消耗"],
    }


def has_result(row: dict) -> bool:
    """Only published content with at least one real result belongs in performance review."""
    if not row.get("published_at"):
        return False
    snap = (row.get("snapshots") or [{}])[-1]
    public = snap.get("public_metrics") or {}
    internal = snap.get("internal_metrics") or {}
    business = snap.get("business_results") or {}
    return any(isinstance(value, (int, float)) for box in (public, internal, business) for value in box.values())


def build(ledger: dict) -> dict:
    all_rows = ledger.get("items") or []
    rows = [row for row in all_rows if has_result(row)]
    waiting_rows = [row for row in all_rows if row not in rows]
    known_likes = [metric((row.get("snapshots") or [{}])[-1], "likes") for row in rows]
    known_likes = [x for x in known_likes if x is not None]
    median = sorted(known_likes)[len(known_likes) // 2] if known_likes else None
    result = []
    for row in rows:
        snap = (row.get("snapshots") or [{}])[-1]
        likes = metric(snap, "likes")
        comments = metric(snap, "comments")
        shares = metric(snap, "shares")
        collects = metric(snap, "collects")
        interactions = sum(x or 0 for x in (likes, comments, shares, collects)) if any(x is not None for x in (likes, comments, shares, collects)) else None
        facts = [label for value, label in ((likes, f"点赞 {likes}"), (comments, f"评论 {comments}"), (shares, f"分享 {shares}"), (collects, f"收藏 {collects}")) if value is not None]
        if not facts:
            facts = ["公开互动数据暂时不知道"]
        if likes is None or median is None:
            observation = "还没有足够的公开数据。"
        elif likes > median:
            observation = "点赞高于这批内容的中位数。"
        elif likes < median:
            observation = "点赞低于这批内容的中位数。"
        else:
            observation = "点赞接近这批内容的中位数。"
        save_share = (shares or 0) + (collects or 0)
        if interactions is None:
            explanation = "数据还没回来，先不猜原因。"
        elif save_share >= max((likes or 0) * 0.5, 10):
            explanation = "收藏和分享较多。"
        elif comments is not None and comments >= 4:
            explanation = "评论较多。"
        else:
            explanation = "题材、开场和画面都不同，目前不能判断是哪一项造成。"
        if interactions is not None:
            explanation += " 这里没有成交数据。"
        result.append({
            "content_id": row.get("content_id"),
            "facts": facts,
            "observations": [observation],
            "primary_explanation": explanation,
            "competing_explanations": ["发布时间或初始流量不同", "主题、开场和画面同时变化"],
            "unknowns": ["内部转化", "投放消耗", "目标客户质量"],
            "hypotheses": ["下一次只改变一个开场变量，才能更清楚地比较"],
            "decision": "validate",
            "next_experiment": "产品、受众和发布位置不变，只换开场。",
        })
    account_review = _account_review(rows)
    next_action = (account_review.get("next_week_plan") or ["下一周只测试一个开场变量；等内部结果补齐后再判断成交。"])[0]
    return {"schema_version": "batch_diagnosis/v1", "review_mode": "account_baseline", "items": result, "account_review": account_review, "waiting_items": [{"content_id": row.get("content_id"), "title": clean_title(row.get("title")), "reason": "还没发布或数据还没回来"} for row in waiting_rows], "weekly_summary": {"content_count": len(rows), "waiting_count": len(waiting_rows), "known_like_count": len(known_likes), "next_action": next_action}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build(json.loads(args.ledger.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(len(result["items"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
