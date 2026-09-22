#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""records_v4.json -> batch_add_database_records 载荷（每批 <=100 条）。"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
DB = 'Hu5q2PAyW17BmdP5JPQ9os'

NUM = {'价格', '销量', '销售额', '环比增速', '关联达人数', '评分', '评价数', '预估成本', '退货率'}
DATE = {'上市日期'}
TEXT = {'商品名称', '品牌', '商品ID', '细分品类', '榜单排名', '核心功效成分', '概念标签',
        '质地描述', '功效宣称', '差评关键词', '选品笔记'}
SELECT = {'数据来源', '所属市场', '品类', '数据标记', '决策状态', '与我方 SKU 重合度',
          '与我方价格带匹配', '与我方客群匹配', '备案路径', '宣称支撑难度', '技术壁垒', '剂型'}


def wrap(k, v):
    if k in NUM:
        return {'number': v}
    if k in DATE:
        return {'date': v}
    if k in TEXT or k not in SELECT:
        return {'text': v}
    return {'select': v}


recs = json.load(open(os.path.join(D, 'records_v4.json'), encoding='utf-8'))['records']
flat = []
for r in recs:
    p = {}
    for k, v in r.items():
        if v is None or v == '':
            continue
        p[k] = wrap(k, v)
    flat.append(p)

CH = 100
batches = []
for i in range(0, len(flat), CH):
    batches.append({'database_id': DB, 'records': flat[i:i + CH]})

for i, b in enumerate(batches, 1):
    p = os.path.join(D, 'payload_v4_%d.json' % i)
    json.dump(b, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    print('批次%d：%d 条 -> %s' % (i, len(b['records']), p))
print('合计', len(flat), '条')
