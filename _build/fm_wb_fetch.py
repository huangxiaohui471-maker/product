#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 webbridge 从 FastMoss 取全字段数据（游客态即可拿到 React fiber 全字段，
含 author_count / total_author_count / launch_time / commission_rate / 类目树）。

用法: python3 fm_wb_fetch.py <sales|new> <startPage> <endPage> [l1cid]
输出: data/fastmoss_<kind>_fiber.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wb import call, unwrap  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
CODE = open(os.path.join(BASE, 'js', 'fm_fiber_rows.js'), encoding='utf-8').read()

KIND = sys.argv[1] if len(sys.argv) > 1 else 'sales'
START = int(sys.argv[2]) if len(sys.argv) > 2 else 1
END = int(sys.argv[3]) if len(sys.argv) > 3 else 4
CID = sys.argv[4] if len(sys.argv) > 4 else '14'

PATH = 'newProducts' if KIND == 'new' else 'saleslist'
URL = 'https://www.fastmoss.com/zh/e-commerce/%s?page=%d&l1_cid=%s'
OUT = os.path.join(BASE, 'data', 'fastmoss_%s_fiber.json' % KIND)

call('find_tab', {'url': 'fastmoss.com'})

all_rows = []
for n in range(START, END + 1):
    url = URL % (PATH, n, CID)
    call('navigate', {'url': url})
    got = None
    for _ in range(4):
        time.sleep(4)
        out = unwrap(call('evaluate', {'code': CODE}))
        if isinstance(out, dict) and out.get('ok') and out.get('rows'):
            got = out
            break
    if not got:
        print('page %d -> 空' % n)
        continue
    for r in got['rows']:
        r['page'] = n
        all_rows.append(r)
    print('page %d -> %d 行' % (n, len(got['rows'])))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({'source': 'FastMoss', 'kind': KIND, 'l1_cid': CID,
           'fetchedAt': time.strftime('%Y-%m-%dT%H:%M:%S'), 'count': len(all_rows),
           'rows': all_rows}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

wa = sum(1 for r in all_rows if r.get('author_count') is not None)
print('SAVED %s 共 %d 条，含关联达人数 %d 条' % (OUT, len(all_rows), wa))
countries = {}
for r in all_rows:
    countries[r.get('region')] = countries.get(r.get('region'), 0) + 1
print('国家分布:', countries)
