#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并并行的分片缓存 → data/tikhub_details.json。

规则：同一 pid 出现多次时，成功的条目优先；都成功则取 tries 更少的。
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

D = Path(__file__).parent
OUT = D / 'data' / 'tikhub_details.json'

files = sorted(glob.glob(str(D / 'data' / 'tk_shard_*.json'))) \
    + sorted(glob.glob(str(D / 'data' / 'tk_s[0-9]_*.json'))) \
    + sorted(glob.glob(str(D / 'data' / 'tk_mop_*.json')))
merged = {}
for f in files:
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception as e:
        print('跳过 %s：%s' % (Path(f).name, e))
        continue
    if not isinstance(d, dict):
        continue
    new = 0
    for pid, v in d.items():
        cur = merged.get(pid)
        if cur is None:
            merged[pid] = v
            new += 1
        elif v.get('ok') and not cur.get('ok'):
            merged[pid] = v
            new += 1
        elif v.get('ok') and cur.get('ok') and (v.get('tries') or 9) < (cur.get('tries') or 9):
            merged[pid] = v
    print('%-24s 读入 %-4d 条，新增/更新 %d' % (Path(f).name, len(d), new))

json.dump(merged, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ok = [v for v in merged.values() if v.get('ok')]
fb = [v for v in ok if v.get('fallback')]
print('\n合并后 %d 条，成功 %d 条（其中经站点回退取得 %d 条）' % (len(merged), len(ok), len(fb)))
print('有评分 %d｜有评价数 %d｜描述>50字 %d｜有店铺名 %d｜有法规属性 %d' % (
    sum(1 for v in ok if v.get('score') is not None),
    sum(1 for v in ok if v.get('review_count') is not None),
    sum(1 for v in ok if (v.get('desc_len') or 0) > 50),
    sum(1 for v in ok if v.get('shop_name')),
    sum(1 for v in ok if v.get('legal'))))
print('→ %s' % OUT)
