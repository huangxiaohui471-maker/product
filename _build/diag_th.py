#!/usr/bin/env python3
"""诊断 TH/PH 全 400 的根因：是商品 ID 不在该区，还是 ID 形态不对。"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tikhub

D = Path(__file__).parent
EP = '/api/v1/tiktok/shop/web/fetch_product_detail_v3'
SEARCH = '/api/v1/tiktok/shop/web/fetch_search_products_list'

recs = json.load(open(D / 'data' / 'records_cat_400.json', encoding='utf-8'))['records']
th = [r for r in recs if r.get('数据标记') == '真实' and r.get('国家/地区') == '泰国'][:2]
ph = [r for r in recs if r.get('数据标记') == '真实' and r.get('国家/地区') == '菲律宾'][:1]

def probe(pid, region, label):
    r = tikhub.get(EP, {'product_id': pid, 'region': region}, retry=1, timeout=45)
    if r.get('_error'):
        return '%s region=%-2s → ERR %s' % (label, region, str(r['_error'])[:60])
    d = r.get('data') or {}
    rt = d.get('region_supported')
    cm = ((d.get('product_data') or {}).get('page_config') or {}).get('components_map') or []
    pi = [c for c in cm if c.get('component_type') == 'product_info']
    nm = ''
    if pi:
        cd = pi[0].get('component_data') or {}
        nm = ((cd.get('product_info') or {}).get('product_model') or {}).get('name') or ''
    return '%s region=%-2s → code=%s region_supported=%s 组件=%d 名称=%s' % (
        label, region, r.get('code'), rt, len(cm), nm[:30])

for r in th:
    pid, name = str(r.get('商品ID')), str(r.get('商品名称'))[:26]
    print('【TH 记录】%s  id=%s' % (name, pid))
    for rg in ('TH', 'MY', 'ID', 'SG'):
        print('   ', probe(pid, rg, name))
    # 用搜索反查该商品真正的 id
    sr = tikhub.get(SEARCH, {'keyword': name.split('|')[0].strip()[:24], 'region': 'TH', 'page': 1}, retry=1, timeout=45)
    print('    搜索 TH 是否可用:', 'ERR ' + str(sr.get('_error'))[:60] if sr.get('_error') else 'code=%s' % sr.get('code'))
print()
for r in ph:
    pid, name = str(r.get('商品ID')), str(r.get('商品名称'))[:26]
    print('【PH 记录】%s  id=%s' % (name, pid))
    for rg in ('PH', 'MY', 'ID', 'US'):
        print('   ', probe(pid, rg, name))
