#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""眼油竞品分析：从抖音罗盘「商品榜单-眼部精华」翻页抽取 fiber 数据。
用法: python3 fetch_eyeoil_rank.py [pages]   # 默认 10 页 = 100 条
输出: eyeoil/rank_fiber.json
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from wb import call, unwrap  # noqa: E402

CODE = open(os.path.join(BASE, 'js', 'dp_fiber_rows.js'), encoding='utf-8').read()
CLICK = "document.querySelector('.aurora-pagination-next').click(); 'clicked'"
SESSION = 'eyeoil-analysis'

PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 10
OUT = os.path.join(BASE, 'eyeoil', 'rank_fiber.json')

call('find_tab', {'url': 'compass.jinritemai.com'}, session=SESSION)

all_rows, meta = [], {}
for n in range(1, PAGES + 1):
    got = None
    for _ in range(3):
        time.sleep(2.5)
        out = unwrap(call('evaluate', {'code': CODE}, session=SESSION))
        if isinstance(out, dict) and out.get('ok') and out.get('rows'):
            got = out
            break
    if not got:
        print('page %d -> empty, stop' % n)
        break
    meta = {'range': got.get('range', ''), 'catText': got.get('catText', '')}
    for r in got['rows']:
        r['page'] = n
        all_rows.append(r)
    print('page %d -> %d rows (first: %s)' % (n, len(got['rows']), (got['rows'][0].get('name') or '')[:24]))
    if n < PAGES:
        call('evaluate', {'code': CLICK}, session=SESSION)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({'source': '抖音罗盘', 'list': '商品榜单-眼部精华', 'meta': meta,
           'fetchedAt': time.strftime('%Y-%m-%dT%H:%M:%S'), 'count': len(all_rows),
           'rows': all_rows}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('SAVED %s total %d' % (OUT, len(all_rows)))
print('range:', meta.get('range'), '| cat:', (meta.get('catText') or '')[:50])
