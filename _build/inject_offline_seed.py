# -*- coding: utf-8 -*-
"""把 16 条精简示例数据注入 全球选品平台.html 的离线兜底块（SEED_DATA 标记之间）。

复用 make_seed_platform.py 的 ROWS，避免两处数据不一致。
"""
import io
import json
import importlib.util

BASE = "/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47"

spec = importlib.util.spec_from_file_location("msp", BASE + "/_build/make_seed_platform.py")
msp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(msp)
ROWS = msp.ROWS

# 覆盖全部 5 个市场 / 6 个品类，并包含四类洞察样本
PICK = [0, 2, 5, 6, 7, 8, 10, 13, 17, 21, 22, 23, 26, 28, 32, 35]

ORDER = ["商品名称", "品牌", "商品ID", "品类", "细分品类", "价格", "上市日期", "数据来源",
         "所属市场", "销量", "销售额", "环比增速", "关联达人数", "退货率", "榜单排名",
         "核心功效成分", "剂型", "概念标签", "质地描述", "功效宣称", "技术壁垒",
         "评价数", "评分", "差评关键词", "备案路径", "宣称支撑难度", "预估成本",
         "与我方价格带匹配", "与我方客群匹配", "与我方 SKU 重合度", "决策状态", "选品笔记"]


def row_values(r):
    (name, brand, cat, sub, price, launch, source, market, sold, growth, kol, refund,
     rank, ing, form, concept, texture, claim, barrier, reviews, rating, bad,
     filing, hardness, cost, priceFit, crowdFit, overlap, status, note) = r
    return [name, brand, "", cat, sub, price, launch, source, market, sold,
            int(round(sold * price * 0.85)), growth, kol, refund, rank, ing, form,
            concept, texture, claim, barrier, reviews, rating, bad, filing,
            hardness, cost, priceFit, crowdFit, overlap, status, note]


assert len(ORDER) == 32, len(ORDER)

rows = [row_values(ROWS[i]) for i in PICK]
for r in rows:
    assert len(r) == 32, len(r)

block = ("/*==SEED_DATA_START==*/\n"
         + "var SEED_ORDER = " + json.dumps(ORDER, ensure_ascii=False) + ";\n"
         + "var SEED_ROWS = [\n"
         + ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
         + "\n];\n"
         + "/*==SEED_DATA_END==*/")

path = BASE + "/全球选品平台.html"
html = io.open(path, encoding="utf-8").read()
start = html.index("/*==SEED_DATA_START==*/")
end = html.index("/*==SEED_DATA_END==*/") + len("/*==SEED_DATA_END==*/")
html = html[:start] + block + html[end:]
io.open(path, "w", encoding="utf-8").write(html)

print("注入条数:", len(rows))
mk = {}
for r in rows:
    mk[r[8]] = mk.get(r[8], 0) + 1
cat = {}
for r in rows:
    cat[r[3]] = cat.get(r[3], 0) + 1
print("市场:", mk)
print("品类:", cat)
print("HTML 字符数:", len(html))
