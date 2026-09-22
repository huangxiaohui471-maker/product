#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 webbridge 从抖音罗盘「商品榜单」翻页抽取（fiber 版，含精确数值/商品ID/真实价格）。

用法: python3 dp_wb_fetch.py [pages]   # 默认 6 页 = 60 条
输出: data/douyin_compass_fiber.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wb import call, unwrap  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
CODE = open(os.path.join(BASE, 'js', 'dp_fiber_rows.js'), encoding='utf-8').read()
CLICK = "document.querySelector('.aurora-pagination-next').click(); 'clicked'"

PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 6
OUT = os.path.join(BASE, 'data', 'douyin_compass_fiber.json')

call('find_tab', {'url': 'compass.jinritemai.com'})

all_rows = []
meta = {}
for n in range(1, PAGES + 1):
    got = None
    for _ in range(3):
        time.sleep(2.5)
        out = unwrap(call('evaluate', {'code': CODE}))
        if isinstance(out, dict) and out.get('ok') and out.get('rows'):
            got = out
            break
    if not got:
        print('page %d -> 空' % n)
        break
    meta = {'range': got.get('range', ''), 'catText': got.get('catText', '')}
    for r in got['rows']:
        r['page'] = n
        all_rows.append(r)
    print('page %d -> %d 行 (首个: %s)' % (n, len(got['rows']), (got['rows'][0].get('name') or '')[:24]))
    if n < PAGES:
        call('evaluate', {'code': CLICK})

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({'source': '抖音罗盘', 'list': '商品榜单', 'meta': meta,
           'fetchedAt': time.strftime('%Y-%m-%dT%H:%M:%S'), 'count': len(all_rows),
           'rows': all_rows}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('SAVED %s 共 %d 条' % (OUT, len(all_rows)))
print('统计周期:', meta.get('range'), '| 类目:', (meta.get('catText') or '')[:40])
