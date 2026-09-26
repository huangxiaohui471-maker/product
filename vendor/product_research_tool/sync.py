#!/usr/bin/env python3
"""把 Product-Research-Tool 的罗盘采集结果接入现有本地工作台。

只更新 cloud_platform.json 的数据行；不改 index.html、策略规则或 WorkBuddy 云端。
罗盘金额是区间（单位：分），所以不会填入现有页面的精确「销售额」字段。
"""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from collector import config
from collector.compass import category_mining, category_overview, product_rank


APP_DIR = Path(__file__).resolve().parents[2]
SNAPSHOT = APP_DIR / "cloud_platform.json"
BASE_SNAPSHOT = APP_DIR / "cloud_platform.base.json"
SOURCE_COMMIT = "7e91a3f437c43d4d574622ab0e702856f661df24"


def leaf_paths(node, parent=()):
    path = parent + (node["name"],)
    result = {node["cid"]: path}
    for child in node.get("children", []):
        result.update(leaf_paths(child, path))
    return result


LEAF_PATHS = leaf_paths(config.CATEGORY_TREE)


def money_range(lower, upper):
    def fmt(fen):
        if fen is None:
            return "?"
        yuan = fen / 100
        if yuan >= 100_000_000:
            return f"¥{yuan / 100_000_000:g}亿"
        if yuan >= 10_000:
            return f"¥{yuan / 10_000:g}万"
        return f"¥{yuan:g}"

    if lower is None and upper is None:
        return None
    if lower == upper:
        return fmt(lower)
    return f"{fmt(lower)}–{fmt(upper)}"


def normalize_product(row, category, date, window):
    product_id = str(row.get("product_id") or "").strip()
    name = str(row.get("name") or "").strip()
    if not product_id or not name:
        raise ValueError("商品榜行缺少商品 ID 或名称")
    sales_lower, sales_upper = row.get("sales_lower"), row.get("sales_upper")
    # 兼容历史快照；新采集结果只使用 sales_amount_*。
    lower = row.get("sales_amount_lower", row.get("pay_lower"))
    upper = row.get("sales_amount_upper", row.get("pay_upper"))
    if lower is not None and (not isinstance(lower, (int, float)) or lower < 0):
        raise ValueError(f"商品 {product_id} 的金额下界无效")
    if upper is not None and (not isinstance(upper, (int, float)) or upper < 0):
        raise ValueError(f"商品 {product_id} 的金额上界无效")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError(f"商品 {product_id} 的金额上下界颠倒")

    leaf = LEAF_PATHS.get(row.get("leaf_category_id"))
    category_name = category.get("name") or "未分类"
    leaf_name = leaf[-1] if leaf else category_name
    path = "/".join(leaf) if leaf else category.get("path") or category_name
    rank = row.get("rank")
    period = f"{window[0]} ~ {window[1]}"
    amount = money_range(lower, upper)
    note = (
        f"抖音罗盘商品榜原始快照；统计周期 {period}；"
        f"用户支付金额为平台区间 {amount or '未披露'}，不是精确销售额；"
        f"销量来自 pay_combo_cnt 区间 {sales_lower or '未披露'}~{sales_upper or '未披露'}。"
        "店铺名不等于品牌，不能据此自动立项。"
    )
    return {
        "record_id": f"prt_compass_{product_id}",
        "数据来源": "抖音罗盘",
        "数据标记": "真实",
        "国家/地区": "中国",
        "所属市场": "中国",
        "品类": "护肤",
        "二级类目": category_name,
        "三级类目": leaf_name,
        "细分品类": leaf_name,
        "类目ID": str(row.get("leaf_category_id") or ""),
        "商品ID": product_id,
        "商品名称": name,
        "品牌": None,
        "店铺": row.get("brand"),
        "榜单排名": f"抖音罗盘·商品榜 第{rank}名（{path}，{period}）" if rank else None,
        "榜单名次": rank,
        "价格": None,
        "价格带": row.get("price_bin"),
        "销售额": None,
        "销售额区间": amount,
        "销量": None,
        "销量区间": (f"{sales_lower:,}-{sales_upper:,}" if sales_lower is not None and sales_upper is not None else None),
        "销量下界": sales_lower,
        "销量上界": sales_upper,
        "销售额下界分": lower,
        "销售额上界分": upper,
        "商品榜真实字段": {"销量": "pay_combo_cnt", "销售额": "new_pay_amt"},
        "环比增速": None,
        "成交金额区间": amount,
        "成交金额下界元": lower / 100 if lower is not None else None,
        "成交金额上界元": upper / 100 if upper is not None else None,
        "统计周期开始": window[0],
        "统计周期结束": window[1],
        "快照日期": date,
        "是否新上榜": bool(row.get("newly_on_ranking")),
        "名次变化": row.get("rank_change"),
        "商品图片": row.get("image_url"),
        "商品链接": row.get("detail_url"),
        "选品笔记": note,
        "采集代码版本": SOURCE_COMMIT,
    }


def build_rows(raw):
    window = raw.get("window")
    date = raw.get("date")
    if not isinstance(window, list) or len(window) != 2 or not all(isinstance(x, str) for x in window):
        raise ValueError("商品榜快照缺少有效的统计窗口")
    if not date or not re.fullmatch(r"\d{4}/\d{2}/\d{2}", str(date)):
        raise ValueError("商品榜快照缺少有效日期")
    categories = raw.get("categories") or []
    if not categories:
        raise ValueError("商品榜快照没有类目")
    out = []
    seen = set()
    for category in categories:
        for row in category.get("rows") or []:
            normalized = normalize_product(row, category, date, window)
            product_id = normalized["商品ID"]
            if product_id in seen:
                continue
            seen.add(product_id)
            out.append(normalized)
    if not out:
        raise ValueError("商品榜快照为空；拒绝覆盖现有数据")
    return out


def record_key(row):
    return (
        str(row.get("数据来源") or ""),
        str(row.get("国家/地区") or ""),
        str(row.get("商品ID") or row.get("商品名称") or ""),
    )


def merge_rows(existing, incoming):
    order = []
    by_key = {}
    for row in existing:
        key = record_key(row)
        if key not in by_key:
            order.append(key)
        by_key[key] = row
    for row in incoming:
        key = record_key(row)
        if key not in by_key:
            order.append(key)
        by_key[key] = row
    return [by_key[key] for key in order]


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def latest_raw():
    raw_dir = Path(config.DATA_RAW)
    matches = sorted(raw_dir.glob("*/compass_product_rank.json"), reverse=True)
    for path in matches:
        raw = load_json(path)
        if sum(len(c.get("rows") or []) for c in raw.get("categories") or []) > 0:
            return path, raw
    raise FileNotFoundError("没有非空罗盘商品榜快照；先用 --collect 采集")


def write_json_atomic(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temp = tempfile.mkstemp(prefix=".snapshot-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def collect():
    end = dt.date.today() - dt.timedelta(days=2)
    begin = end - dt.timedelta(days=6)
    end_str = end.strftime("%Y/%m/%d")
    begin_str = begin.strftime("%Y/%m/%d")
    print(f"[collect] 罗盘窗口 {begin_str} ~ {end_str}", flush=True)
    ranked = product_rank.run(end_str, begin_str, end_str)
    if not ranked.get("ok"):
        raise RuntimeError(f"商品榜采集失败：{ranked.get('error')}")
    # 以下两个原始数据集单独保存，绝不把价格带误作类目或把类目增速写到商品行。
    mined = category_mining.run(end_str, begin_str, end_str)
    overview = category_overview.run(end_str, begin_str, end_str)
    print(f"[collect] 商品榜 {ranked.get('file')}；类目挖掘 {mined.get('rows', 0)} 行；价格带 {overview.get('rows', 0)} 行", flush=True)
    if not mined.get("ok") or not overview.get("ok"):
        print("[collect] 非商品数据采集未完成；保留原始文件，不编造缺失指标", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true", help="先从已登录的罗盘后台采集")
    parser.add_argument("--dry-run", action="store_true", help="只校验和预览合并数量，不改工作台数据")
    args = parser.parse_args()
    if args.collect:
        collect()

    path, raw = latest_raw()
    incoming = build_rows(raw)
    source = BASE_SNAPSHOT if BASE_SNAPSHOT.exists() else SNAPSHOT
    base = load_json(source)
    existing = base.get("results")
    if not isinstance(existing, list):
        raise ValueError(f"{source} 不含 results 列表")
    combined = merge_rows(existing, incoming)
    print(f"[sync] {path.name}：采集商品 {len(incoming)} 条；基础数据 {len(existing)} 条；合并后 {len(combined)} 条")
    if args.dry_run:
        print("[sync] dry-run：未修改工作台")
        return
    if not BASE_SNAPSHOT.exists():
        write_json_atomic(BASE_SNAPSHOT, base)
    write_json_atomic(SNAPSHOT, {**base, "results": combined})
    print(f"[sync] 已更新 {SNAPSHOT}；刷新 http://127.0.0.1:4174/ 可查看")


if __name__ == "__main__":
    main()
