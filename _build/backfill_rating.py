#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 FastMoss 详情页抓到的「评分 / 评价数」按商品ID 回填到云表。

用法: python3 backfill_rating.py <token>
数据: data/fastmoss_rating.json（fm_rating_fetch.js 产出）
      data/cloud_after_v4.json（云表快照，需先查询刷新）
"""
import json
import os
import subprocess
import sys

LIB = '/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library'
DB = 'Hu5q2PAyW17BmdP5JPQ9os'
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ''

rating = json.load(open(os.path.join(D, 'fastmoss_rating.json'), encoding='utf-8'))
cloud = json.load(open(os.path.join(D, 'cloud_after_v4.json'), encoding='utf-8'))
rows = cloud if isinstance(cloud, list) else cloud.get('results', [])
print('云表快照 %d 条 | 评分数据 %d 条' % (len(rows), len(rating)))

updates = []
hit = miss = 0
for r in rows:
    if r.get('数据来源') != 'FastMoss':
        continue
    pid = str(r.get('商品ID') or '')
    rt = rating.get(pid)
    if not rt or rt.get('rating') is None:
        miss += 1
        continue
    props = {'评分': {'number': rt['rating']}}
    if rt.get('reviews') is not None:
        props['评价数'] = {'number': rt['reviews']}
    updates.append({'record_id': r['record_id'], 'properties': props})
    hit += 1

print('命中 %d 条 / FastMoss 未命中 %d 条' % (hit, miss))
json.dump({'database_id': DB, 'records': updates},
          open(os.path.join(D, 'payload_rating.json'), 'w', encoding='utf-8'), ensure_ascii=False)

if '--write' not in sys.argv:
    print('（dry-run；加 --write 实际写入）')
    sys.exit(0)

for i in range(0, len(updates), 100):
    chunk = updates[i:i + 100]
    body = json.dumps({'database_id': DB, 'records': chunk}, ensure_ascii=False)
    p = subprocess.run(['python3', os.path.join(LIB, 'database', 'batch_update_database_records.py'),
                        '--token-stdin', '--stdin'],
                       input=TOKEN + '\n' + body, capture_output=True, text=True)
    out = p.stdout or ''
    print('批次 %d：%d 条，成功 %d | %s' % (i // 100 + 1, len(chunk), out.count('"success": true'), out[:120].replace('\n', ' ')))
