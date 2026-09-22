#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本轮规则改造补丁打到线上 index.html（保留平台 pnid 锚点与 inject.js）。"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, '.page_tmp', 'index.html')

PATCHES = [
    # ---- 1. 新增常量 ----
    ("/* 洞察规则：从数据里提炼四类机会 */\nfunction insightsOf(list) {",
     "/* 差评高危词：命中即提示风险。\n"
     "   替代「退货率」——三个平台的商品榜单都不提供退货率，抓不到的东西不该当规则前提。 */\n"
     "var HIGH_RISK_WORD = /过敏|致敏|烂脸|爆脸|爆痘|闷痘|闭口|红肿|刺痛|刺激|泛红|发痒|瘙痒|脱皮|掉皮|熏眼|辣眼|廉价感|假滑/;\n"
     "/* 窗口期门槛：只看增速。达人数与销售额不再作为门槛（真实数据里三者不可兼得，\n"
     "   设限只会让规则永远打不中），改为展示用的「达人渗透度」参考。 */\n"
     "var WIN_MIN_GROWTH = 60;\n\n"
     "/* 洞察规则：从数据里提炼四类机会 */\nfunction insightsOf(list) {"),

    # ---- 2. 变量声明 ----
    ("    var g = numField(r, '环比增速'), k = numField(r, '关联达人数');\n"
     "    var rf = numField(r, '退货率'), sd = numField(r, '销量');\n"
     "    var sales = numField(r, '销售额');",
     "    var g = numField(r, '环比增速'), k = numField(r, '关联达人数');\n"
     "    var sd = numField(r, '销量');\n"
     "    var bad = txtOf(r, '差评关键词');"),

    # ---- 3. 窗口期 / 改良机会判定 ----
    ("    if (g !== null && g >= 60 && k !== null && k <= 15 && (sales === null || sales >= 1000000)) win.push(r);\n"
     "    if (rf !== null && rf >= 10 && sd !== null && sd >= 30000) fix.push(r);",
     "    if (g !== null && g >= WIN_MIN_GROWTH) win.push(r);\n"
     "    if (bad !== '') fix.push(r);"),

    # ---- 4. 风险提醒判定 ----
    ("    if ((rf !== null && rf >= 12) || (g !== null && g < 0)) risk.push(r);",
     "    if ((g !== null && g < 0) || HIGH_RISK_WORD.test(bad)) risk.push(r);"),

    # ---- 5. 改良机会排序 ----
    ("  fix.sort(function (a, b) { return (numField(b, '退货率') || 0) - (numField(a, '退货率') || 0); });",
     "  fix.sort(function (a, b) { return (numField(b, '销量') || 0) - (numField(a, '销量') || 0); });"),

    # ---- 6. 规则前提 ----
    ("var RULES_NEED = {\n"
     "  win: { name: '窗口期', need: ['环比增速', '关联达人数', '销售额'] },\n"
     "  fix: { name: '改良机会', need: ['退货率', '销量'] },\n"
     "  blank: { name: '空白赛道', need: ['与我方 SKU 重合度', '环比增速'] },\n"
     "  ready: { name: '可落地', need: ['备案路径', '宣称支撑难度', '预估成本', '价格'] },\n"
     "  risk: { name: '风险提醒', need: ['退货率', '环比增速'] }\n"
     "};",
     "var RULES_NEED = {\n"
     "  win: { name: '窗口期', need: ['环比增速'] },\n"
     "  fix: { name: '改良机会', need: ['差评关键词'] },\n"
     "  blank: { name: '空白赛道', need: ['与我方 SKU 重合度', '环比增速'] },\n"
     "  ready: { name: '可落地', need: ['备案路径', '宣称支撑难度', '预估成本', '价格'] },\n"
     "  risk: { name: '风险提醒', need: ['环比增速', '差评关键词'] }\n"
     "};"),

    # ---- 7. 字段：口碑组 ----
    ("  { n: '评分', t: 'number', g: '口碑', src: 'auto' },\n"
     "  { n: '评价数', t: 'number', g: '口碑', src: 'auto' },\n"
     "  { n: '差评关键词', t: 'text', g: '口碑', src: 'manual' },",
     "  { n: '评分', t: 'number', g: '口碑', src: 'auto' },\n"
     "  { n: '评价数', t: 'number', g: '口碑', src: 'auto' },\n"
     "  { n: '好评关键词', t: 'text', g: '口碑', src: 'manual', hint: '来自真实商品评价，如「好推开、不搓泥、淡香」' },\n"
     "  { n: '差评关键词', t: 'text', g: '口碑', src: 'manual', hint: '改良机会的前提：填了就会自动进「改良机会」' },\n"
     "  { n: '评价来源', t: 'select', g: '口碑', src: 'manual', opts: ['抖音评价', '天猫评价', '小红书', 'TikTok', '其他'] },"),

    # ---- 8. 退货率 hint ----
    ("  { n: '退货率', t: 'number', g: '平台数据', src: 'half', hint: '只有部分类目/平台提供，FastMoss 不提供' },",
     "  { n: '退货率', t: 'number', g: '平台数据', src: 'half', hint: '三平台商品榜都不提供；不参与任何规则，仅备查' },"),

    # ---- 9. 窗口期卡片 ----
    ("  var wg = avgOf(ins.win, '环比增速'), wk = avgOf(ins.win, '关联达人数');\n"
     "  h += card({\n"
     "    cls: '', title: '窗口期商品', desc: '增速已经起来，但还没被达人推爆',\n"
     "    icon: ICON.search,\n"
     "    ev: '命中 <b>' + ins.win.length + '</b> 个　·　平均增速 <b>' + (wg === null ? '—' : Math.round(wg) + '%') + '</b>　·　平均关联达人 <b>' + (wk === null ? '—' : Math.round(wk)) + ' 个</b>',\n"
     "    rows: rowsHtml(ins.win, 'growth', 4),\n"
     "    warn: warnFor('win') || partWarn('win'),\n"
     "    rule: '规则：环比增速 ≥ 60% 且 关联达人数 ≤ 15 且 销售额 ≥ 100 万。达人数少意味着还没被批量投放，是介入成本最低的时候。'\n"
     "  });",
     "  var wg = avgOf(ins.win, '环比增速'), wk = avgOf(ins.win, '关联达人数');\n"
     "  var kLow = 0, kMid = 0, kHigh = 0, kNone = 0;\n"
     "  for (var ki = 0; ki < ins.win.length; ki++) {\n"
     "    var kv = numField(ins.win[ki], '关联达人数');\n"
     "    if (kv === null) kNone++; else if (kv <= 50) kLow++; else if (kv <= 150) kMid++; else kHigh++;\n"
     "  }\n"
     "  h += card({\n"
     "    cls: '', title: '窗口期商品', desc: '增速已经起来，达人还没铺开——现在介入成本最低',\n"
     "    icon: ICON.search,\n"
     "    ev: '命中 <b>' + ins.win.length + '</b> 个　·　平均增速 <b>' + (wg === null ? '—' : Math.round(wg) + '%') + '</b>　·　达人渗透度：未铺开 <b>' + kLow + '</b> / 起量 <b>' + kMid + '</b> / 已铺开 <b>' + kHigh + '</b>'\n"
     "      + (kNone ? '（' + kNone + ' 条无达人数据）' : ''),\n"
     "    rows: rowsHtml(ins.win, 'growth', 4),\n"
     "    warn: warnFor('win') || partWarn('win'),\n"
     "    rule: '规则：环比增速 ≥ ' + WIN_MIN_GROWTH + '%，达人数与销售额不设门槛。达人数只作「达人渗透度」参考——未铺开（≤50）说明还没被批量投放，介入成本最低；已铺开（>150）说明需求已被验证但竞争激烈。'\n"
     "  });"),

    # ---- 10. 改良机会卡片 ----
    ("  var fr = avgOf(ins.fix, '退货率');\n"
     "  h += card({\n"
     "    cls: 'r', title: '改良机会', desc: '卖得好但在退货，差评指向明确',\n"
     "    icon: ICON.tool,\n"
     "    ev: '命中 <b>' + ins.fix.length + '</b> 个　·　平均退货率 <b>' + (fr === null ? '—' : Math.round(fr * 10) / 10 + '%') + '</b>',\n"
     "    rows: rowsHtml(ins.fix, 'refund', 4),\n"
     "    warn: warnFor('fix') || partWarn('fix'),\n"
     "    rule: '规则：退货率 ≥ 10% 且 销量 ≥ 3 万。销量说明需求真实存在，退货说明产品没解决好——差评关键词就是你的改良方向。'\n"
     "  });",
     "  h += card({\n"
     "    cls: 'r', title: '改良机会', desc: '需求已被榜单验证，差评指出了没做好的地方',\n"
     "    icon: ICON.tool,\n"
     "    ev: '命中 <b>' + ins.fix.length + '</b> 个　·　均有差评关键词　·　按销量排序',\n"
     "    rows: rowsHtml(ins.fix, 'sales', 4),\n"
     "    warn: warnFor('fix') || partWarn('fix'),\n"
     "    rule: '规则：差评关键词非空即命中。门槛不再是退货率（三平台榜单都不给），而是真实评价里反复出现的抱怨——差评关键词不是缺点清单，是改良清单。'\n"
     "  });"),

    # ---- 11. 风险提醒卡片 ----
    ("      cls: 'r', title: '风险提醒', desc: '退货偏高或已在负增长，别急着跟',\n"
     "      icon: ICON.warn,\n"
     "      ev: '命中 <b>' + ins.risk.length + '</b> 个',\n"
     "      rows: rowsHtml(ins.risk, 'risk', 4),\n"
     "      warn: warnFor('risk') || partWarn('risk'),\n"
     "      rule: '规则：退货率 ≥ 12% 或 环比增速 < 0。这类品不是不能做，而是必须先搞清楚负增长和高退货的原因再决定。'\n"
     "    });",
     "      cls: 'r', title: '风险提醒', desc: '已在负增长，或差评里出现过敏、刺激这类硬伤',\n"
     "      icon: ICON.warn,\n"
     "      ev: '命中 <b>' + ins.risk.length + '</b> 个',\n"
     "      rows: rowsHtml(ins.risk, 'risk', 4),\n"
     "      warn: warnFor('risk') || partWarn('risk'),\n"
     "      rule: '规则：环比增速 < 0 或 差评关键词含高危词（过敏/刺激/烂脸/闷痘…）。这类品不是不能做，而是必须先搞清楚负增长和差评的原因再决定。'\n"
     "    });"),
]


def main():
    src = io.open(TARGET, encoding='utf-8').read()
    dry = '--apply' not in sys.argv

    # 先做命中检查
    bad = []
    for i, (old, _new) in enumerate(PATCHES, 1):
        n = src.count(old)
        if n != 1:
            bad.append((i, n, old.splitlines()[0][:80]))
    if bad:
        print('!! 以下补丁未唯一命中，中止：')
        for i, n, head in bad:
            print('   #%d 命中 %d 次 | %s' % (i, n, head))
        return 1
    print('11 处补丁全部唯一命中')

    if dry:
        print('（dry-run，未写入；加 --apply 执行）')
        return 0

    out = src
    for old, new in PATCHES:
        out = out.replace(old, new, 1)
    io.open(TARGET, 'w', encoding='utf-8').write(out)
    print('已写入 %s（%d -> %d 字节）' % (TARGET, len(src), len(out)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
