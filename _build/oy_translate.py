#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Olive Young 榜单的韩文品牌/商品名译成简体中文（Kimi 批量，带缓存）。

输入:  data/oliveyoung_rank.json
输出:  data/oy_zh.json   [{no, brand_ko, name_ko, brand_zh, name_zh}]
缓存:  data/oy_zh_cache.json（按 goodsNo 缓存，改 prompt 请升 TASK_VER）

用法: python3 oy_translate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kimi  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
TASK_VER = 1
BATCH = 8
MAXTOK = 2600

SYS = """你是韩中化妆品本地化译名专家，把韩国 Olive Young 榜单商品的品牌与商品名译成简体中文。

规则：
1. 品牌名优先用中文市场通行译名（메디힐→美迪惠尔、라운드랩→Round Lab、라로슈포제→理肤泉、에스트라→爱丝翠、달바→d'Alba、식물나라→植物王国、파티온→Phation、메디큐브→美迪惠尔…）；确无通行译名时按韩语音译。
2. 商品名逐词直译，**保留规格与数量**（50ml、10매→10片、100ml、7종→7款），保留促销信息（1+1、기획→企划装、리필→替换装、더블기획→双份企划）。
3. 方括号里的活动标签也要译：[9월 올영픽]→[9月OliveYoung精选]、[1등썬]→[防晒第1名]、[15년 연속 1위]→[连续15年第1名]、[산리오캐릭터즈 에디션]→[三丽鸥联名版]。
4. 不添加原文没有的营销词，不省略原文信息，不做意译润色。
5. 品牌与商品名都只输出简体中文（英文品牌名可保留英文）。

严格只输出 JSON，不要任何解释：{"rows":[{"i":0,"brand":"中文品牌","name":"中文商品名"}]}"""


def main():
    rows = json.load(open(os.path.join(D, 'oliveyoung_rank.json'), encoding='utf-8'))
    cache_path = os.path.join(D, 'oy_zh_cache.json')
    cache = {}
    if os.path.exists(cache_path):
        c = json.load(open(cache_path, encoding='utf-8'))
        if c.get('ver') == TASK_VER:
            cache = c.get('items', {})
        else:
            print('缓存版本不同，弃用')
    todo = [x for x in rows if x['no'] not in cache]
    print('共 %d 条，待译 %d 条（缓存命中 %d）' % (len(rows), len(todo), len(rows) - len(todo)))

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        lines = ['%d|%s|%s' % (k, x['b'], x['n']) for k, x in enumerate(chunk)]
        try:
            out = kimi.chat_json(SYS, '\n'.join(lines), max_tokens=MAXTOK)
        except Exception as e:  # noqa: BLE001
            print('  批次 %d 失败: %s' % (i // BATCH + 1, str(e)[:160]))
            continue
        got = 0
        for r in (out.get('rows') or []):
            try:
                src = chunk[int(r['i'])]
            except Exception:  # noqa: BLE001
                continue
            cache[src['no']] = {'brand_zh': (r.get('brand') or '').strip(),
                                'name_zh': (r.get('name') or '').strip()}
            got += 1
        print('  批次 %d：%d 条 -> 译出 %d' % (i // BATCH + 1, len(chunk), got))
        json.dump({'ver': TASK_VER, 'items': cache}, open(cache_path, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)

    merged = []
    for x in rows:
        c = cache.get(x['no']) or {}
        merged.append({'no': x['no'], 'r': x['r'], 'c': x['c'], 'p': x['p'],
                       'brand_ko': x['b'], 'name_ko': x['n'],
                       'brand_zh': c.get('brand_zh') or '', 'name_zh': c.get('name_zh') or ''})
    json.dump(merged, open(os.path.join(D, 'oy_zh.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    miss = [m['no'] for m in merged if not m['name_zh']]
    print('写出 data/oy_zh.json：%d 条，未译 %d 条 %s' % (len(merged), len(miss), miss[:6]))
    print('样例:')
    for m in merged[:5]:
        print('  %s | %s -> %s | %s' % (m['no'], m['brand_ko'], m['brand_zh'], m['name_zh'][:44]))


if __name__ == '__main__':
    main()
