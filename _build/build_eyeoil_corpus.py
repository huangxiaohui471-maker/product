#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建抽取语料：100 条榜单（标题+元数据）+ 头部详情页文本合并 -> eyeoil/corpus/<pid>.txt
同时生成 eyeoil/heat.json：pid -> {销量, 销售额, 评价数}"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
EYE = os.path.join(BASE, 'eyeoil')
CORPUS = os.path.join(EYE, 'corpus')
DETAILS = os.path.join(EYE, 'details')
os.makedirs(CORPUS, exist_ok=True)

rows = json.load(open(os.path.join(EYE, 'rank_fiber.json'), encoding='utf-8'))['rows']

def wan(s):
    m = re.search(r'([\d.]+)\s*w', s or '', re.I)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r'([\d.]+)', s or '')
    return int(float(m.group(1))) if m else None

seen = set()
heat = {}
n = 0
for r in rows:
    pid = str(r.get('product_id') or '')
    if not pid or pid in seen:
        continue
    seen.add(pid)
    n += 1
    head = (r.get('name') or '') + '\n'
    meta = '价格: %s | 店铺: %s | 榜单排名: %s | 销售额中值: %s | 销量中值: %s\n' % (
        r.get('price_bin'), r.get('shop_name'), r.get('rank'), r.get('gmv_raw'), r.get('orders_raw'))
    body = ''
    dp = os.path.join(DETAILS, pid + '.txt')
    if os.path.exists(dp):
        lines = open(dp, encoding='utf-8').read().split('\n')
        body = '\n'.join(lines[2:])  # 跳过首行标题与元数据行（避免重复）
        m = re.search(r'商品评价\s*\(([\d.w]+)\)', '\n'.join(lines))
        if m:
            heat.setdefault(pid, {})['评价数'] = wan(m.group(1))
    with open(os.path.join(CORPUS, pid + '.txt'), 'w', encoding='utf-8') as f:
        f.write(head + meta + body)
    h = heat.setdefault(pid, {})
    if r.get('orders_mid'):
        h['销量'] = r['orders_mid']
    if r.get('gmv_mid'):
        h['销售额'] = r['gmv_mid'] / 100.0  # 分 -> 元

json.dump(heat, open(os.path.join(EYE, 'heat.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('corpus files: %d, heat entries: %d (with 评价数: %d)' % (
    n, len(heat), sum(1 for v in heat.values() if v.get('评价数'))))
