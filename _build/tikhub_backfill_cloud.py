#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 TikHub 拉到的评分 / 评价数 / 升级后的成分回填到云表「全球新品库」。

按 商品ID 对齐 record_id **原位更新**（不删不建，保住人工填的决策字段）。

用法（token 从 stdin 首行读入，不落盘、不进 argv）：
  printf '%s' "<token>" | python3 tikhub_backfill_cloud.py            # 干跑
  printf '%s' "<token>" | python3 tikhub_backfill_cloud.py --write    # 真写
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
ING_V2 = D / 'data' / 'ingredients_v2.json'


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()
    tk = sys.stdin.readline().strip()
    if not tk:
        raise SystemExit('未从 stdin 读到 token')

    details = json.load(open(DETAILS, encoding='utf-8'))
    ing = json.load(open(ING_V2, encoding='utf-8')) if ING_V2.is_file() else {}
    rec_ing = ing.get('记录') or {}

    rows = query_all(tk)
    print('云表 %d 条' % len(rows))

    updates = []
    stat = {'评分': 0, '评价数': 0, '成分': 0, '成分变动': 0, '跳过': 0}
    fb, native = 0, 0
    for r in rows:
        pid = str(r.get('商品ID') or '')
        if not pid:
            continue
        dt = details.get(pid) or {}
        props = {}

        if dt.get('ok'):
            if dt.get('fallback'):
                fb += 1
            else:
                native += 1
            sc = dt.get('score')
            rc = dt.get('review_count')
            if isinstance(sc, (int, float)) and sc:
                props['评分'] = {'number': float(sc)}
                stat['评分'] += 1
            if isinstance(rc, (int, float)) and rc:
                props['评价数'] = {'number': int(rc)}
                stat['评价数'] += 1

        iv = rec_ing.get(pid)
        if iv and iv.get('成分'):
            new_txt = '、'.join(iv['成分'])
            old_txt = r.get('核心功效成分') or ''
            if new_txt != old_txt:
                props['核心功效成分'] = {'text': new_txt}
                if old_txt:
                    stat['成分变动'] += 1
                else:
                    stat['成分'] += 1

        if props:
            updates.append({'record_id': r['record_id'], 'properties': props,
                            'name': str(r.get('商品名称'))[:34], 'props': props})
        else:
            stat['跳过'] += 1

    print('将更新 %d 条 ｜ 明细: %s' % (len(updates), stat))
    print('取数站点：本区直取 %d 条，经站点回退（ID/US）取得 %d 条' % (native, fb))
    print()
    print('样例（前 8 条）:')
    for u in updates[:8]:
        keys = {k: (v.get('number') if 'number' in v else v.get('text')) for k, v in u['props'].items()}
        print('   %-36s %s' % (u['name'], json.dumps(keys, ensure_ascii=False)[:110]))

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
