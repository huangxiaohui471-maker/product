#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8 → v9 页面补丁：数据源地图补 TikHub（互补源）+ 字段口径更新。

每个 old_string 必须**唯一命中**，否则直接抛错，绝不静默改错。

用法：
  python3 patch_page_v9.py --in ../../全球选品平台.html --out .page_v9/index.html
"""
from __future__ import annotations

import argparse
from pathlib import Path

TIKHUB_ENTRY = """  {
    k: 'TikHub', short: 'TikHub', kind: 'tk',
    markets: ['东南亚', '欧美', '日本'],
    path: 'api.tikhub.io → /api/v1/tiktok/shop/web/fetch_product_detail_v3（传 product_id + region）',
    chan: '服务端直连，不依赖浏览器登录态',
    quota: '按次计费约 $0.002；实测间隔 1.5 秒可连续拉取，无频率限制',
    full: ['销量', '评分', '评价数', '店铺品牌', 'TikTok 官方三级类目', '商品描述全文'],
    miss: ['销售额', '环比增速', '关联达人数', '退货率', '备案与成本'],
    regions: 'US / ID / VN / TH / MY / PH / SG / JP / MX（英国不支持，巴西返回空组件）',
    note: '定位是互补源，不是榜单源——它只给单个商品的销量、评分、评价数与官方类目、描述全文，'
      + '不给销售额与环比增速，也不给关联达人数，所以出榜单仍靠 FastMoss。'
      + '越南 / 泰国 / 菲律宾站点偶发取不到，脚本会自动换到 ID / US 站点重试，并记录实际取数站点。韩国不在覆盖内。'
  },
"""

PATCHES = [
    # 1) 新增 TikHub 数据源条目（插在 FastMoss 与 Hwahae 之间）
    (
        "  {\n    k: 'Hwahae', short: '화해', kind: 'kr',\n",
        TIKHUB_ENTRY + "  {\n    k: 'Hwahae', short: '화해', kind: 'kr',\n",
    ),
    # 2) srcCov 支持 tik 类源（只供成分/口碑，算不出销量类机会）
    (
        "  if (d.kind === 'kr' || d.kind === 'cn' && srcKey === 'KEV美妆圈') return 'part';",
        "  if (d.kind === 'kr' || d.kind === 'tk' || d.kind === 'cn' && srcKey === 'KEV美妆圈') return 'part';",
    ),
    # 3) 成分口径：标题 → 标题 + TikTok 描述全文
    (
        "hint: '从商品标题抽出的显性成分词——标题没写就留空，不做推测' },",
        "hint: '从商品标题与 TikTok 商品描述全文抽出的显性成分词——商家没写就留空，不做推测' },",
    ),
    # 4) 评分 / 评价数 标注真实来源
    (
        "  { n: '评分', t: 'number', g: '口碑', src: 'auto' },\n"
        "  { n: '评价数', t: 'number', g: '口碑', src: 'auto' },",
        "  { n: '评分', t: 'number', g: '口碑', src: 'auto', hint: '来自 TikTok Shop 商品详情（TikHub 接口）——商品榜单本身不给这个字段' },\n"
        "  { n: '评价数', t: 'number', g: '口碑', src: 'auto', hint: '来自 TikTok Shop 商品详情（TikHub 接口）——商品榜单本身不给这个字段' },",
    ),
    # 5) 日本市场：口碑字段已有补齐通道
    (
        "'日本': { lv: 'thin', note: 'FastMoss 有日本站，但 2025-06 才开站，历史数据浅、环比基数不稳' },",
        "'日本': { lv: 'thin', note: 'FastMoss 有日本站，但 2025-06 才开站，历史数据浅、环比基数不稳；评分与评价数可由 TikHub 补齐' },",
    ),
    # 6) 源地图里补一句 TikHub 的定位，免得被当成榜单源
    (
        "    + '所以韩国的「窗口期」「改良机会」「风险提醒」这三条规则在这套引擎里天然算不出来，只能当成分与口碑情报看。</div>';\n",
        "    + '所以韩国的「窗口期」「改良机会」「风险提醒」这三条规则在这套引擎里天然算不出来，只能当成分与口碑情报看。</div>';\n"
        "  h += '<div class=\"rule-warn\" style=\"margin-top:12px\"><b>TikHub 是互补源，不是榜单源：</b>'\n"
        "    + '它按单个商品给销量、评分、评价数、TikTok 官方三级类目与商品描述全文，把榜单缺的口碑字段补齐；'\n"
        "    + '但它不给销售额与环比增速，也不给关联达人数——所以「哪几个品在涨」仍然只能由 FastMoss 这类榜单源回答。'\n"
        "    + '可取站点：US / ID / VN / TH / MY / PH / SG / JP / MX，<b>英国官方不支持、巴西返回空组件</b>；'\n"
        "    + '越南 / 泰国 / 菲律宾偶发取不到（同一商品换时刻或换站点即可），已在取数脚本里做了自动换站回退并记录实际站点。</div>';\n",
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', required=True)
    ap.add_argument('--out', dest='dst', required=True)
    args = ap.parse_args()

    s = open(args.src, encoding='utf-8').read()
    for i, (old, new) in enumerate(PATCHES, 1):
        n = s.count(old)
        if n != 1:
            raise SystemExit('补丁 %d 命中 %d 次（要求恰好 1 次），中止。片段：%r' % (i, n, old[:70]))
        s = s.replace(old, new)
        print('补丁 %d ✓ 唯一命中' % i)

    out = Path(args.dst)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(s, encoding='utf-8')
    print('\n写出 %s（%d 字节）' % (out, len(s.encode('utf-8'))))


if __name__ == '__main__':
    main()
