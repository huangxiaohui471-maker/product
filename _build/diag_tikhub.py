#!/usr/bin/env python3
"""诊断：单条商品详情返回结构到底是什么。"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tikhub

D = Path(__file__).parent
recs = json.load(open(D / 'data' / 'records_cat_400.json', encoding='utf-8'))['records']
REGION = {'美国': 'US', '印度尼西亚': 'ID', '泰国': 'TH', '越南': 'VN',
          '菲律宾': 'PH', '马来西亚': 'MY', '新加坡': 'SG', '日本': 'JP'}
targets = []
for r in recs:
    if r.get('数据标记') != '真实' or r.get('数据来源') != 'FastMoss':
        continue
    rg = REGION.get(r.get('国家/地区'))
    if rg:
        targets.append((str(r.get('商品ID')), rg, r.get('商品名称'), r.get('国家/地区')))

EP = '/api/v1/tiktok/shop/web/fetch_product_detail_v3'
pid, region, name, country = targets[0]
print('测试商品:', pid, region, country, name)
raw = tikhub.get(EP, {'product_id': pid, 'region': region}, retry=1, timeout=50)
out = D / 'data' / 'diag_raw.json'
json.dump(raw, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('原始响应已存:', out, '字节', (out).stat().st_size)

print('\n顶层键:', list(raw.keys()))
for k in ('code', 'message', 'msg', 'detail', 'router', 'params', 'cache_message'):
    if k in raw:
        print('  %s = %r' % (k, raw[k]))
pd = raw.get('data')
print('\ndata 类型:', type(pd).__name__)
if isinstance(pd, dict):
    print('data 键:', list(pd.keys()))
    pc = pd.get('page_config') or {}
    print('page_config 键:', list(pc.keys()) if isinstance(pc, dict) else type(pc))
    cm = pc.get('components_map') if isinstance(pc, dict) else None
    print('components_map 条数:', len(cm) if cm else cm)
    if cm:
        for c in cm:
            cd = c.get('component_data') or {}
            print('  - ct=%-28s name=%-24s data_keys=%s' % (
                c.get('component_type'), c.get('component_name'),
                list(cd.keys())[:6] if isinstance(cd, dict) else type(cd).__name__))
    # 打印 data 下其它可能承载错误信息的键
    for k, v in pd.items():
        if k != 'page_config' and not isinstance(v, (dict, list)):
            print('  data.%s = %r' % (k, v))
