#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 records.json 转成 batch_add_database_records 的载荷（每批 <=100 条）。"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
DB = 'Hu5q2PAyW17BmdP5JPQ9os'
NUM = {'价格', '销量', '销售额', '环比增速', '关联达人数', '评分', '评价数', '预估成本'}
DATE = {'上市日期'}
TEXT = {'商品名称', '品牌', '商品ID', '细分品类', '榜单排名', '核心功效成分', '概念标签',
        '质地描述', '功效宣称', '差评关键词', '选品笔记'}

recs = json.load(open(os.path.join(D, 'records.json'), encoding='utf-8'))['records']
out = []
for r in recs:
    p = {}
    for k, v in r.items():
        if v is None or v == '':
            continue
        if k in NUM:
            p[k] = {'number': v}
        elif k in DATE:
            p[k] = {'date': v}
        elif k in TEXT:
            p[k] = {'text': v}
        else:
            p[k] = {'select': v}
    out.append({'database_id': DB, 'records': [p]})

# 按 100 条/批切分
batches = []
CH = 100
flat = [x['records'][0] for x in out]
for i in range(0, len(flat), CH):
    batches.append({'database_id': DB, 'records': flat[i:i + CH]})

for i, b in enumerate(batches, 1):
    p = os.path.join(D, 'payload_%d.json' % i)
    json.dump(b, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    print('批次%d：%d 条 -> %s' % (i, len(b['records']), p))
print('合计', len(flat), '条')
print('样例:', json.dumps(batches[0]['records'][0], ensure_ascii=False)[:400])
