#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建「自有店铺口碑库」云表，并写入抖音罗盘「用户原声」的 37 个本店商品口碑。

用法:
    python3 make_review_table.py <token> [--write]
"""
import json
import os
import subprocess
import sys

LIB = '/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library'
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ''
WRITE = '--write' in sys.argv

SCHEMA = {
    'title': '自有店铺口碑库',
    'properties': [
        {'name': '商品名称', 'config': {'text': ''}},
        {'name': '商品ID', 'config': {'text': ''}},
        {'name': '店铺类目', 'config': {'text': ''}},
        {'name': '评价数', 'config': {'number': ''}},
        {'name': '好评数', 'config': {'number': ''}},
        {'name': '好评率', 'config': {'number': ''}},
        {'name': '差评订单数', 'config': {'number': ''}},
        {'name': '差评率', 'config': {'number': ''}},
        {'name': '评价差评率', 'config': {'number': ''}},
        {'name': '好评关键词', 'config': {'text': ''}},
        {'name': '差评关键词', 'config': {'text': ''}},
        {'name': '差评原因', 'config': {'text': ''}},
        {'name': '差评原声', 'config': {'text': ''}},
        {'name': '品质退货数', 'config': {'number': ''}},
        {'name': '品质退货率', 'config': {'number': ''}},
        {'name': '投诉数', 'config': {'number': ''}},
        {'name': '投诉率', 'config': {'number': ''}},
        {'name': '采集周期', 'config': {'text': ''}},
        {'name': '数据来源', 'config': {'select': {'options': [{'text': '抖音罗盘'}]}}},
        {'name': '评价来源', 'config': {'select': {'options': [{'text': '抖音评价'}]}}},
        {'name': '备注', 'config': {'text': ''}},
    ],
}


def run(script, args, stdin):
    p = subprocess.run(['python3', os.path.join(LIB, 'database', script)] + args,
                       input=stdin, capture_output=True, text=True)
    return (p.stdout or ''), (p.stderr or '')


NUM = {'评价数', '好评数', '好评率', '差评订单数', '差评率', '评价差评率',
       '品质退货数', '品质退货率', '投诉数', '投诉率'}
SELECT = {'数据来源', '评价来源'}


def wrap(k, v):
    """云表写入必须包装：{number:..} / {select:..} / {text:..}，写扁平值会报「校验后为空」。"""
    if k in NUM:
        return {'number': v}
    if k in SELECT:
        return {'select': v}
    return {'text': v}


def pct(x, nd=2):
    return None if x is None else round(float(x) * 100, nd)


def main():
    us = json.load(open(os.path.join(D, 'douyin_usersound.json'), encoding='utf-8'))
    prods = us['products']
    print('抖音用户原声：%d 个商品，周期 %s' % (len(prods), us['range']))

    rows = []
    for p in prods:
        reason_txt = ' / '.join('%s %s' % (x['label'], x['n']) for x in (p.get('reason') or []))
        voice = ' | '.join((x.get('sample') or '') for x in (p.get('reason') or [])
                           if x.get('sample'))
        good_kw = ' / '.join(x['label'] for x in (p.get('good') or []))
        bad_kw = ' / '.join(x['label'] for x in (p.get('bad') or []))
        rec = {
            '商品名称': p['name'], '商品ID': p['id'], '店铺类目': p.get('cat') or '',
            '评价数': p.get('eval_cnt'), '好评数': p.get('good_cnt'),
            '好评率': pct(p.get('good_ratio')),
            '差评订单数': p.get('bad_cnt'), '差评率': pct(p.get('bad_ratio')),
            '评价差评率': pct(p.get('bad_eval_ratio')),
            '好评关键词': good_kw, '差评关键词': bad_kw,
            '差评原因': reason_txt, '差评原声': voice[:900],
            '品质退货数': p.get('qreturn_cnt'), '品质退货率': pct(p.get('qreturn_ratio')),
            '投诉数': p.get('complaint_cnt'), '投诉率': pct(p.get('complaint_ratio')),
            '采集周期': us['range'],
            '数据来源': '抖音罗盘', '评价来源': '抖音评价',
            '备注': '抖音电商罗盘·体验·用户原声（本店）',
        }
        rows.append({k: wrap(k, v) for k, v in rec.items() if v not in (None, '')})

    if not WRITE:
        print('（dry-run）将建表并写入 %d 条。样例：' % len(rows))
        print(json.dumps(rows[0], ensure_ascii=False, indent=1)[:800])
        return

    if '--db-id' in sys.argv:
        dbid = sys.argv[sys.argv.index('--db-id') + 1]
        print('复用已有表：%s' % dbid)
    else:
        out, err = run('create_database.py', ['--token-stdin', '--stdin'],
                       TOKEN + '\n' + json.dumps(SCHEMA, ensure_ascii=False))
        try:
            d = json.loads(out)
        except Exception:                                # noqa: BLE001
            print('建表失败：%s %s' % (out[:300], err[:200]))
            return
        if d.get('error'):
            print('建表失败：%s' % d['error'])
            return
        dbid = d['database_id']
        print('新表 ID：%s（字段 %s 个）' % (dbid, d.get('property_count')))

    payload = {'database_id': dbid, 'records': rows}
    out2, err2 = run('batch_add_database_records.py', ['--token-stdin', '--stdin'],
                     TOKEN + '\n' + json.dumps(payload, ensure_ascii=False))
    print('写入结果：成功 %d 条 | %s' % (out2.count('"success": true'),
                                        (out2 or err2)[:200].replace('\n', ' ')))
    json.dump({'database_id': dbid, 'title': SCHEMA['title']},
              open(os.path.join(D, 'review_table.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
