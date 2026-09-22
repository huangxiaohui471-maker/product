#!/usr/bin/env python3
"""决定性测试：TH 的详情接口到底能不能用（用 TH 原生商品 ID 验证）。"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tikhub

D = Path(__file__).parent
B = '/api/v1/tiktok/shop/web/'
recs = json.load(open(D / 'data' / 'records_cat_400.json', encoding='utf-8'))['records']
th_pid = next(str(r['商品ID']) for r in recs
              if r.get('数据标记') == '真实' and r.get('国家/地区') == '泰国')

print('=== 1) TH 热销榜 ===')
hs = tikhub.get(B + 'fetch_hot_selling_products_list', {'region': 'TH', 'count': 5}, retry=1, timeout=60)
if hs.get('_error'):
    print('  ERR', str(hs['_error'])[:160])
else:
    d = hs.get('data') or {}
    print('  code=%s region_supported=%s data键=%s' % (hs.get('code'), d.get('region_supported'), list(d.keys())[:8]))
    prods = d.get('products') or d.get('product_list') or []
    print('  商品数:', len(prods))
    if prods:
        p0 = prods[0]
        print('  product[0] 键:', list(p0.keys())[:14])
        print('  id=%s' % (p0.get('product_id') or p0.get('id')))
        print('  json 前 600:', json.dumps(p0, ensure_ascii=False)[:600])

print('\n=== 2) TH 搜索接口 ===')
sr = tikhub.get(B + 'fetch_search_products_list', {'search_word': 'serum', 'region': 'TH'}, retry=1, timeout=60)
if sr.get('_error'):
    print('  ERR', str(sr['_error'])[:160])
else:
    d = sr.get('data') or {}
    print('  code=%s region_supported=%s 键=%s' % (sr.get('code'), d.get('region_supported'), list(d.keys())[:8]))
    prods = d.get('products') or []
    print('  商品数:', len(prods))
    if prods:
        p0 = prods[0]
        npid = str(p0.get('product_id') or '')
        print('  首个 id=%s  title=%s' % (npid, str(p0.get('title'))[:40]))
        print('\n=== 3) 用 TH 原生 ID 取详情（region=TH / MY / ID）===')
        for rg in ('TH', 'MY', 'ID'):
            r = tikhub.get(B + 'fetch_product_detail_v3', {'product_id': npid, 'region': rg}, retry=1, timeout=45)
            if r.get('_error'):
                print('  region=%-2s ERR %s' % (rg, str(r['_error'])[:90]))
            else:
                cm = ((r.get('data') or {}).get('product_data') or {}).get('page_config', {}).get('components_map') or []
                print('  region=%-2s code=%s 组件=%d %s' % (rg, r.get('code'), len(cm),
                      '有 product_info' if any(c.get('component_type') == 'product_info' for c in cm) else '无 product_info'))

print('\n=== 4) 我们库里的 TH 商品走 v2 详情 ===')
for rg in ('TH', 'ID'):
    r = tikhub.get(B + 'fetch_product_detail_v2', {'product_id': th_pid, 'region': rg}, retry=1, timeout=45)
    if r.get('_error'):
        print('  v2 region=%-2s ERR %s' % (rg, str(r['_error'])[:90]))
    else:
        d = r.get('data') or {}
        print('  v2 region=%-2s code=%s 键=%s' % (rg, r.get('code'), list(d.keys())[:10]))
