#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「国家/地区 + 三级品类体系 + 成分」写进云表「全球新品库」（原位 update）。

步骤：
  1. 加 4 个字段：二级类目 / 三级类目 / 类目ID（text）、国家/地区（select，21 国）
  2. 按 商品ID 对齐 record_id，batch_update 回填

用法:
    python3 update_cloud_cat.py <token> [--write]
"""
import json
import os
import subprocess
import sys

LIB = '/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library'
DB = 'Hu5q2PAyW17BmdP5JPQ9os'
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ''
WRITE = '--write' in sys.argv

COUNTRIES = ['中国', '美国', '印度尼西亚', '泰国', '越南', '菲律宾', '马来西亚', '新加坡', '日本',
             '英国', '德国', '法国', '意大利', '西班牙', '巴西', '墨西哥',
             '奥地利', '比利时', '荷兰', '波兰', '葡萄牙']

NEW_FIELDS = [
    {'name': '二级类目', 'config': {'text': ''}},
    {'name': '三级类目', 'config': {'text': ''}},
    {'name': '类目ID', 'config': {'text': ''}},
    {'name': '国家/地区', 'config': {'select': {'options': [{'name': c} for c in COUNTRIES]}}},
]


def run(script, args, stdin):
    p = subprocess.run(['python3', os.path.join(LIB, 'database', script)] + args,
                       input=stdin, capture_output=True, text=True)
    return p.stdout or '', p.stderr or ''


def query_all():
    rows, cur = [], ''
    for _ in range(20):
        args = ['--token-stdin', '--database-id', DB, '--page-size', '200']
        if cur:
            args += ['--start-cursor', cur]
        out, _e = run('query_database_record.py', args, TOKEN + '\n')
        try:
            d = json.loads(out)
        except Exception:                                # noqa: BLE001
            print('查询解析失败：%s' % out[:200])
            break
        rows += d.get('results', [])
        cur = d.get('next_cursor') or ''
        if not d.get('has_more'):
            break
    return rows


def main():
    src = json.load(open(os.path.join(D, 'records_cat.json'), encoding='utf-8'))
    recs = src['records'] if isinstance(src, dict) else src
    by_id = {str(r.get('商品ID') or ''): r for r in recs if r.get('商品ID')}
    print('本地记录 %d 条' % len(by_id))

    # ---- 1. 加字段（已存在会报错，忽略即可）----
    if WRITE:
        for f in NEW_FIELDS:
            out, err = run('add_database_field.py',
                           ['--token-stdin', '--database-id', DB,
                            '--property', json.dumps(f, ensure_ascii=False)], TOKEN + '\n')
            try:
                d = json.loads(out)
                ok = not d.get('error')
                msg = d.get('error') or ('已存在/创建:' + d.get('property', {}).get('name', ''))
            except Exception:                            # noqa: BLE001
                ok, msg = False, (out or err)[:150]
            print('  加字段 %-10s %s %s' % (f['name'], 'OK' if ok else 'SKIP', msg if not ok else ''))
    else:
        print('（dry-run）将加字段：%s' % ', '.join(f['name'] for f in NEW_FIELDS))

    # ---- 2. 回填 ----
    cloud = query_all()
    print('云表 %d 条' % len(cloud))
    updates, stat, unm = [], {'二级': 0, '三级': 0, 'cid': 0, '国家': 0, '成分': 0}, 0
    for row in cloud:
        pid = str(row.get('商品ID') or '')
        s = by_id.get(pid)
        if not s:
            if row.get('数据标记') == '真实':
                unm += 1
            continue
        props = {}
        for fld, key, tag in (('二级类目', '二级类目', '二级'), ('三级类目', '三级类目', '三级'),
                              ('类目ID', '类目ID', 'cid')):
            v = s.get(key)
            if v and v != (row.get(fld) or ''):
                props[fld] = {'text': v}
                stat[tag] += 1
        cty = s.get('国家/地区')
        if cty and cty != (row.get('国家/地区') or ''):
            props['国家/地区'] = {'select': cty}
            stat['国家'] += 1
        ing = s.get('核心功效成分')
        if ing and ing != (row.get('核心功效成分') or ''):
            props['核心功效成分'] = {'text': ing}
            stat['成分'] += 1
        if props:
            updates.append({'record_id': row['record_id'], 'properties': props})

    print('待更新 %d 条：%s | 本地有但云表没对上 %d 条' % (len(updates), json.dumps(stat, ensure_ascii=False), unm))
    json.dump({'database_id': DB, 'count': len(updates), 'records': updates},
              open(os.path.join(D, 'payload_cat_update.json'), 'w', encoding='utf-8'), ensure_ascii=False)

    if not WRITE:
        print('（dry-run；加 --write 实际写入）')
        return
    ok = 0
    for i in range(0, len(updates), 100):
        chunk = updates[i:i + 100]
        body = json.dumps({'database_id': DB, 'records': chunk}, ensure_ascii=False)
        out, err = run('batch_update_database_records.py', ['--token-stdin', '--stdin'], TOKEN + '\n' + body)
        n = out.count('"success": true')
        ok += n
        print('批次 %d：%d 条，成功 %d | %s' % (i // 100 + 1, len(chunk), n, (out or err)[:140].replace('\n', ' ')))
    print('合计写入成功 %d / %d' % (ok, len(updates)))


if __name__ == '__main__':
    main()
