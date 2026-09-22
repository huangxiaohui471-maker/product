#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 AI 增强结果与 FastMoss 评分回填进云表「全球新品库」（原位更新，保留 record_id）。

为什么用 update 而不是「删了重写」：
  删重写会换掉 record_id，页面上人工填过的「决策状态」等字段会一起丢。
  这里按 商品ID 对齐，只写确实变化的字段。

用法:
    python3 update_cloud_ai.py <token> [--write]
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

CATS = {'护肤', '彩妆', '个护', '身体', '香氛', '工具'}


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
    ai = json.load(open(os.path.join(D, 'records_ai.json'), encoding='utf-8'))
    ai = ai['records'] if isinstance(ai, dict) else ai
    rating = {}
    rp = os.path.join(D, 'fastmoss_rating.json')
    if os.path.exists(rp):
        rating = json.load(open(rp, encoding='utf-8'))
    print('AI 记录 %d 条 | 评分数据 %d 条' % (len(ai), len(rating)))

    by_id = {}
    for r in ai:
        pid = str(r.get('商品ID') or '')
        if pid:
            by_id[pid] = r

    cloud = query_all()
    json.dump(cloud, open(os.path.join(D, 'cloud_before_ai.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('云表 %d 条' % len(cloud))

    updates, stat = [], {'笔记': 0, '品类': 0, '评分': 0, '评价数': 0, '未匹配': 0}
    for row in cloud:
        pid = str(row.get('商品ID') or '')
        src = by_id.get(pid)
        props = {}
        if src:
            note = src.get('选品笔记')
            if note and note != (row.get('选品笔记') or ''):
                props['选品笔记'] = {'text': note}
                stat['笔记'] += 1
            cat = src.get('品类')
            if cat in CATS and cat != (row.get('品类') or ''):
                props['品类'] = {'select': cat}
                stat['品类'] += 1
            sub = src.get('细分品类')
            if sub and sub != (row.get('细分品类') or ''):
                props['细分品类'] = {'text': sub}
        elif row.get('数据标记') == '真实':
            stat['未匹配'] += 1

        rt = rating.get(pid)
        if rt and rt.get('rating') is not None:
            if rt['rating'] != row.get('评分'):
                props['评分'] = {'number': rt['rating']}
                stat['评分'] += 1
            if rt.get('reviews') is not None and rt['reviews'] != row.get('评价数'):
                props['评价数'] = {'number': rt['reviews']}
                stat['评价数'] += 1

        if props:
            updates.append({'record_id': row['record_id'], 'properties': props})

    print('待更新 %d 条：%s' % (len(updates), json.dumps(stat, ensure_ascii=False)))
    json.dump({'database_id': DB, 'count': len(updates), 'records': updates},
              open(os.path.join(D, 'payload_ai_update.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)

    if not WRITE:
        print('（dry-run；加 --write 实际写入）')
        return
    ok = 0
    for i in range(0, len(updates), 100):
        chunk = updates[i:i + 100]
        body = json.dumps({'database_id': DB, 'records': chunk}, ensure_ascii=False)
        out, err = run('batch_update_database_records.py', ['--token-stdin', '--stdin'],
                       TOKEN + '\n' + body)
        n = out.count('"success": true')
        ok += n
        print('批次 %d：%d 条，成功 %d | %s' % (i // 100 + 1, len(chunk), n,
                                              (out or err)[:140].replace('\n', ' ')))
    print('合计写入成功 %d / %d' % (ok, len(updates)))


if __name__ == '__main__':
    main()
