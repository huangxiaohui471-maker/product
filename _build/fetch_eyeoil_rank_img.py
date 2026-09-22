#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重抓眼部精华榜 10 页（含 image_url / rank_change）-> eyeoil/rank_fiber_img.json"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from wb import call, unwrap  # noqa: E402

CODE = open(os.path.join(BASE, 'js', 'dp_fiber_rows_img.js'), encoding='utf-8').read()
CLICK = "document.querySelector('.aurora-pagination-next').click(); 'clicked'"
SESSION = 'eyeoil-analysis'
OUT = os.path.join(BASE, 'eyeoil', sys.argv[1] if len(sys.argv) > 1 else 'rank_fiber_img.json')
PAGES = 10

call('find_tab', {'url': 'compass.jinritemai.com'}, session=SESSION)
all_rows, meta = [], {}
prev_first = None
for n in range(1, PAGES + 1):
    got = None
    for _ in range(5):
        time.sleep(3)
        out = unwrap(call('evaluate', {'code': CODE}, session=SESSION))
        if isinstance(out, dict) and out.get('ok') and out.get('rows'):
            # 防串页：本页首行 rank 与上一页相同说明表格还没刷新，继续等
            if prev_first is not None and out['rows'][0].get('rank') == prev_first:
                continue
            got = out
            break
    if not got:
        print('page %d -> empty/stuck, stop' % n)
        break
    prev_first = got['rows'][0].get('rank')
    meta = {'range': got.get('range', ''), 'catText': got.get('catText', '')}
    for r in got['rows']:
        r['page'] = n
        all_rows.append(r)
    print('page %d -> %d rows (first rank %s)' % (n, len(got['rows']), got['rows'][0].get('rank')))
    if n < PAGES:
        call('evaluate', {'code': CLICK}, session=SESSION)

json.dump({'source': '抖音罗盘', 'list': '商品榜单-眼部精华', 'meta': meta,
           'fetchedAt': time.strftime('%Y-%m-%dT%H:%M:%S'), 'count': len(all_rows),
           'rows': all_rows}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('SAVED %s total %d | range %s' % (OUT, len(all_rows), meta.get('range')))
