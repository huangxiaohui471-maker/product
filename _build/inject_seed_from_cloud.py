# -*- coding: utf-8 -*-
"""从云表实拉数据，注入 全球选品平台.html 的离线兜底块（SEED_DATA 标记之间）。

为什么改成从云表拉：
  原来的 seed 源自 make_seed_platform.py 的硬编码 ROWS，改云表数据时两处会漂移。
  离线种子必须与云端示例完全一致（尤其「数据来源」与韩国字段的可得性），
  否则离线模式下引擎体检给出的结论与在线模式互相打脸。

用法：
  1) 先拉一份云表快照到 _build/cloud_platform.json（query_database_record.py 的输出）
  2) python3 _build/inject_seed_from_cloud.py
"""
import io
import json
import re

BASE = "/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47"

# 与页面 FIELDS 一致；「数据标记」由页面代码统一置为「示例」，不进种子列
ORDER = ["商品名称", "品牌", "商品ID", "品类", "细分品类", "二级类目", "三级类目", "类目ID",
         "价格", "上市日期", "数据来源", "所属市场", "国家/地区", "销量", "销售额", "环比增速",
         "关联达人数", "退货率", "榜单排名", "核心功效成分", "剂型", "概念标签", "质地描述",
         "功效宣称", "技术壁垒", "评价数", "评分", "差评关键词", "备案路径", "宣称支撑难度",
         "预估成本", "与我方价格带匹配", "与我方客群匹配", "与我方 SKU 重合度", "决策状态", "选品笔记",
         "SKU 数", "备案/许可号", "法规合规声明"]
assert len(ORDER) == 39, len(ORDER)


def load_cloud():
    raw = io.open(BASE + "/_build/cloud_platform.json", encoding="utf-8").read().strip()
    raw = re.sub(r"^KS_\w+ ", "", raw)
    return json.loads(raw)["results"]


def pick(rows, want=17):
    """挑出覆盖全部市场与品类、且含各类洞察样本的种子。

    注意：截断必须放在最后，且要保证「必选」条目不被截掉
    （早先版本就是因为先补品类、后取沐浴，truncate 时把沐浴整条挤没了，
      导致「搜索词打太死」那条诊断在离线模式下永远演示不出来）。
    """
    chosen, seen, must = [], set(), set()

    def take(r, need=False):
        k = r["record_id"]
        if k in seen:
            return
        seen.add(k)
        chosen.append(r)
        if need:
            must.add(k)

    numv = lambda r, k: r.get(k) if isinstance(r.get(k), (int, float)) else None

    # 1) 每个市场先各取 3 条（保证市场全覆盖）
    for mk in ["中国", "韩国", "日本", "欧美", "东南亚"]:
        n = 0
        for r in rows:
            if r.get("所属市场") == mk and n < 3:
                take(r)
                n += 1

    # 2) 必选：一条「沐浴」类商品。
    #    既补上东南亚的个护样本，也让「搜索词打太死」这条诊断可复现
    #    （搜「沐浴油」全库没有 → 引擎应给出「沐浴」的近似词建议）
    if not any("沐浴" in (r.get("细分品类") or "") + (r.get("商品名称") or "") for r in chosen):
        for r in rows:
            if "沐浴" in (r.get("细分品类") or "") + (r.get("商品名称") or ""):
                take(r, need=True)
                break

    # 3) 必选：补足缺失品类
    for cat in ["护肤", "彩妆", "个护", "身体", "香氛", "工具"]:
        if not any(r.get("品类") == cat for r in chosen):
            for r in rows:
                if r.get("品类") == cat:
                    take(r, need=True)
                    break

    # 4) 必选：各类洞察样本（窗口期 / 改良 / 空白 / 可落地 / 风险）
    tests = [
        lambda r: (numv(r, "环比增速") or 0) >= 60 and (numv(r, "关联达人数") or 999) <= 15,
        lambda r: (numv(r, "退货率") or 0) >= 10,
        lambda r: r.get("与我方 SKU 重合度") == "全新",
        lambda r: r.get("备案路径") == "普通化妆品备案" and r.get("宣称支撑难度") == "无需评价",
        lambda r: (numv(r, "环比增速") or 0) < 0 or (numv(r, "退货率") or 0) >= 12,
    ]
    for t in tests:
        if not any(t(r) for r in chosen):
            for r in rows:
                if t(r):
                    take(r, need=True)
                    break

    # 4b) 必选：带官方备案号的品。
    #     否则离线模式下 Hero 的「已备案」计数恒为 0、档案里也看不到法规字段
    if not any(r.get("备案/许可号") for r in chosen):
        for r in rows:
            if r.get("备案/许可号"):
                take(r, need=True)
                break

    # 5) 截断，但保证必选条目不被挤出
    if len(chosen) > want:
        keep = chosen[:want]
        keep_ids = set(r["record_id"] for r in keep)
        missing = [r for r in chosen if r["record_id"] in must and r["record_id"] not in keep_ids]
        if missing:
            # 从尾部剔除「非必选」条目，给必选条目让位
            tail = [r for r in reversed(keep) if r["record_id"] not in must]
            for m in missing:
                if tail:
                    drop = tail.pop(0)
                    keep = [r for r in keep if r["record_id"] != drop["record_id"]]
                    keep.append(m)
            # 恢复原始顺序
            order = {r["record_id"]: i for i, r in enumerate(chosen)}
            keep.sort(key=lambda r: order[r["record_id"]])
        chosen = keep
    return chosen


def row_values(r):
    out = []
    for k in ORDER:
        v = r.get(k)
        if v is None:
            v = ""
        out.append(v)
    return out


rows = load_cloud()
sel = pick(rows)

block = ("/*==SEED_DATA_START==*/\n"
         + "var SEED_ORDER = " + json.dumps(ORDER, ensure_ascii=False) + ";\n"
         + "var SEED_ROWS = [\n"
         + ",\n".join(json.dumps(row_values(r), ensure_ascii=False) for r in sel)
         + "\n];\n"
         + "/*==SEED_DATA_END==*/")

path = BASE + "/全球选品平台.html"
html = io.open(path, encoding="utf-8").read()
start = html.index("/*==SEED_DATA_START==*/")
end = html.index("/*==SEED_DATA_END==*/") + len("/*==SEED_DATA_END==*/")
html = html[:start] + block + html[end:]
io.open(path, "w", encoding="utf-8").write(html)

print("注入条数:", len(sel))
mk, cat, src = {}, {}, {}
for r in sel:
    mk[r.get("所属市场")] = mk.get(r.get("所属市场"), 0) + 1
    cat[r.get("品类")] = cat.get(r.get("品类"), 0) + 1
    src[r.get("数据来源")] = src.get(r.get("数据来源"), 0) + 1
print("市场:", mk)
print("品类:", cat)
print("来源:", src)
print("HTML 字符数:", len(html))
