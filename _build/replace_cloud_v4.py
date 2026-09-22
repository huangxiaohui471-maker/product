#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""替换云表真实数据：删除旧「数据标记=真实」记录，写入 records_v4 生成的载荷。"""
import json
import os
import subprocess
import sys

LIB = '/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library'
DB = 'Hu5q2PAyW17BmdP5JPQ9os'
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ''
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def run(script, args):
    p = subprocess.run(['python3', os.path.join(LIB, 'database', script)] + args,
                       input=TOKEN, capture_output=True, text=True)
    return p.stdout or '', p.stderr or ''


def query_all():
    rows, cur = [], ''
    for _ in range(15):
        args = ['--token-stdin', '--database-id', DB, '--page-size', '200']
        if cur:
            args += ['--start-cursor', cur]
        out, _e = run('query_database_record.py', args)
        try:
            d = json.loads(out)
        except Exception:
            print('query parse fail:', out[:200])
            break
        rows += d.get('results', [])
        cur = d.get('next_cursor') or ''
        if not d.get('has_more'):
            break
    return rows


before = query_all()
json.dump(before, open(os.path.join(D, 'cloud_before_v4.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('云表现有 %d 条' % len(before))
real_ids = [r['record_id'] for r in before if r.get('数据标记') == '真实']
print('待删除真实记录 %d 条' % len(real_ids))

for i in range(0, len(real_ids), 100):
    chunk = real_ids[i:i + 100]
    out, err = run('batch_delete_database_records.py',
                   ['--token-stdin', '--database-id', DB, '--record-ids', json.dumps(chunk)])
    ok = out.count('"success": true')
    print('删除批次 %d：%d 条，成功标记 %d，rc-out %s' % (i // 100 + 1, len(chunk), ok, out[:120].replace('\n', ' ')))

for n in (1, 2, 3, 4):
    path = os.path.join(D, 'payload_v4_%d.json' % n)
    body = open(path, encoding='utf-8').read()
    p = subprocess.run(['python3', os.path.join(LIB, 'database', 'batch_add_database_records.py'),
                        '--token-stdin', '--stdin'],
                       input=TOKEN + '\n' + body, capture_output=True, text=True)
    out = p.stdout or ''
    print('写入批次 %d：成功 %d 条 | %s' % (n, out.count('"success": true'), out[:150].replace('\n', ' ')))

after = query_all()
json.dump(after, open(os.path.join(D, 'cloud_after_v4.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('回查：云表 %d 条' % len(after))
import collections
print('  数据标记:', dict(collections.Counter(r.get('数据标记') for r in after)))
real = [r for r in after if r.get('数据标记') == '真实']
print('  真实 %d 条 | 按来源 %s' % (len(real), dict(collections.Counter(r.get('数据来源') for r in real))))
print('  按市场:', dict(collections.Counter(r.get('所属市场') for r in real)))
print('  有关联达人数:', sum(1 for r in real if r.get('关联达人数') is not None),
      '| 有环比:', sum(1 for r in real if r.get('环比增速') is not None))
