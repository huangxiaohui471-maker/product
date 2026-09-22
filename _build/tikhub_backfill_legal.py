#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 TikHub 顺带带回的法规属性（备案/许可号、法规合规声明）与 SKU 结构回填云表。

新增三个字段：备案/许可号（text）、法规合规声明（text）、SKU 数（number）。
原则：**只照录平台原值，不推测**——平台没给的项留空，不填「无」冒充。

按 商品ID 对齐 record_id 原位更新（不删不建，保住人工决策字段）。

用法（token 从 stdin 首行读入，不落盘、不进 argv）：
  printf '%s' "<token>" | python3 tikhub_backfill_legal.py            # 干跑
  printf '%s' "<token>" | python3 tikhub_backfill_legal.py --write    # 真写
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

D = Path(__file__).parent
LIB = '/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library'
DB = 'Hu5q2PAyW17BmdP5JPQ9os'
DETAILS = D / 'data' / 'tikhub_details.json'

# 平台原字段名 → 可读名（只做名称本地化，值照录）
NAME_ZH = {
    'Nomor Ijin Edar  (BPOM / PIRT)': '印尼 BPOM 备案号',
    'FDA registration no.': 'FDA 注册号',
    'CA prop 65: carcinogens': '美国 CA Prop 65 致癌物',
    'CA prop 65: repro. chems': '美国 CA Prop 65 生殖毒性',
}
# 编号类（进「备案/许可号」）与声明类（进「法规合规声明」）
ID_KEYS = ('Nomor Ijin Edar', 'FDA registration')
DECL_KEYS = ('prop 65',)
# 声明类取值本地化
VAL_ZH = {'No': '否', 'Yes': '是', 'no': '否', 'yes': '是'}


def run(script, args, stdin):
    p = subprocess.run(['python3', os.path.join(LIB, 'database', script)] + args,
                       input=stdin, capture_output=True, text=True)
    return p.stdout or ''


def query_all(token):
    rows, cur = [], ''
    for _ in range(10):
        a = ['--token-stdin', '--database-id', DB, '--page-size', '200']
        if cur:
            a += ['--start-cursor', cur]
        d = json.loads(run('query_database_record.py', a, token + '\n'))
        if d.get('results') is None:
            raise RuntimeError('查询失败: %s' % str(d)[:200])
        rows += d['results']
        cur = d.get('next_cursor') or ''
        if not d.get('has_more'):
            break
    return rows


def split_legal(legal):
    """legal: [{'name':..,'value':..}] → (备案号文本, 法规声明文本)"""
    ids, decls = [], []
    for it in (legal or []):
        nm = str(it.get('name') or '')
        val = str(it.get('value') or '').strip()
        if not val:
            continue
        zh = NAME_ZH.get(nm) or nm
        if any(k in nm for k in ID_KEYS):
            ids.append('%s：%s' % (zh, val))
        elif any(k in nm for k in DECL_KEYS):
            decls.append('%s：%s' % (zh, VAL_ZH.get(val, val)))
    return '；'.join(ids), '；'.join(decls)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()
    tk = sys.stdin.readline().strip()
    if not tk:
        raise SystemExit('未从 stdin 读到 token')

    details = json.load(open(DETAILS, encoding='utf-8'))
    rows = query_all(tk)
    print('云表 %d 条' % len(rows))

    updates = []
    stat = {'备案': 0, '声明': 0, 'SKU': 0, '跳过': 0}
    sample = []
    for r in rows:
        pid = str(r.get('商品ID') or '')
        if not pid:
            stat['跳过'] += 1
            continue
        dt = details.get(pid) or {}
        if not dt.get('ok'):
            stat['跳过'] += 1
            continue
        props = {}

        ids_txt, decl_txt = split_legal(dt.get('legal'))
        if ids_txt:
            props['备案/许可号'] = {'text': ids_txt}
            stat['备案'] += 1
        if decl_txt:
            props['法规合规声明'] = {'text': decl_txt}
            stat['声明'] += 1
        sc = dt.get('sku_count')
        if isinstance(sc, int) and sc > 0:
            props['SKU 数'] = {'number': int(sc)}
            stat['SKU'] += 1

        if props:
            updates.append({'record_id': r['record_id'], 'properties': props,
                            'name': str(r.get('商品名称'))[:32], 'props': props})
            if len(sample) < 6 and ids_txt:
                sample.append((str(r.get('商品名称'))[:32], ids_txt, decl_txt))
        else:
            stat['跳过'] += 1

    print('将更新 %d 条 ｜ 明细: %s' % (len(updates), stat))
    print()
    print('样例（有备案号的前 6 条）:')
    for nm, a, b in sample:
        print('   %-32s 备案[%s] 声明[%s]' % (nm, a, b))

    if not args.write:
        print()
        print('（干跑，未写入。加 --write 执行）')
        return

    print()
    print('开始写入…')
    B = 100
    ok = fail = 0
    for i in range(0, len(updates), B):
        batch = [{'record_id': u['record_id'], 'properties': u['properties']} for u in updates[i:i + B]]
        body = json.dumps({'database_id': DB, 'records': batch}, ensure_ascii=False)
        out = run('batch_update_database_records.py', ['--token-stdin', '--stdin'], tk + '\n' + body)
        try:
            res = json.loads(out)
            n = sum(1 for x in (res.get('results') or []) if x.get('success'))
            ok += n
            fail += len(batch) - n
            print('  批次 %d–%d: 成功 %d' % (i, i + len(batch) - 1, n))
        except Exception:
            print('  批次 %d 解析失败: %s' % (i, out[:200]))
            fail += len(batch)
    print()
    print('写入完成：成功 %d / 失败 %d' % (ok, fail))


if __name__ == '__main__':
    main()
