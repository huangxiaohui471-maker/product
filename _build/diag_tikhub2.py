#!/usr/bin/env python3
"""诊断 2：对已知成功样本 + 失败样本各打一次，看原始结构差异。"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tikhub

D = Path(__file__).parent
EP = '/api/v1/tiktok/shop/web/fetch_product_detail_v3'

CASES = [
    ('1732052189676081387', 'US', '已知成功：medicube US'),
    ('1735304940106318937', 'ID', '已知成功：JJ Glow ID'),
]

raws = {}
for pid, rg, label in CASES:
    r = tikhub.get(EP, {'product_id': pid, 'region': rg}, retry=1, timeout=50)
    raws[label] = r
    print('===', label, rg)
    if r.get('_error'):
        print('  _error:', str(r['_error'])[:220])
        continue
    print('  顶层键:', list(r.keys()))
    print('  code=', r.get('code'), 'message=', str(r.get('message'))[:80])
    pd = r.get('data') or {}
    print('  data 键:', list(pd.keys()) if isinstance(pd, dict) else type(pd).__name__)
    pc = (pd.get('page_config') or {}) if isinstance(pd, dict) else {}
    print('  page_config 类型:', type(pc).__name__)
    if isinstance(pc, dict):
        print('  page_config 键:', list(pc.keys()))
        cm = pc.get('components_map')
        print('  components_map 条数:', len(cm) if cm else cm)
        if cm:
            for c in cm[:25]:
                cd = c.get('component_data')
                k = list(cd.keys())[:5] if isinstance(cd, dict) else type(cd).__name__
                print('    ct=%-26s name=%-22s %s' % (c.get('component_type'), c.get('component_name'), k))
    # 整个 raw 里的任何字符串型 message 类字段
    def walk(o, path=''):
        if isinstance(o, dict):
            for kk, vv in o.items():
                if kk in ('message', 'msg', 'detail', 'error', 'error_message', 'toast') and isinstance(vv, str):
                    print('  ⚑ %s.%s = %s' % (path, kk, vv[:180]))
                walk(vv, path + '.' + kk)
        elif isinstance(o, list):
            for i, vv in enumerate(o[:5]):
                walk(vv, path + '[%d]' % i)
    walk(r)

json.dump(raws, open(D / 'data' / 'diag_raw2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n已存 data/diag_raw2.json')
