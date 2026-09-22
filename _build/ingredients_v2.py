#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成分库 v2：在标题之外并入 TikHub 拉到的**商品描述全文**，重抽显性成分词。

口径说明（重要）：
  仍然只做「事实抽取」——商家在标题或描述里**自己写出来的**成分词才算，
  不做任何推测，也不把「描述没提」当成「没有这个成分」。
  与 v1 的差别只有一个：文本源从「标题」扩到「标题 + 描述全文」。

用法：
  python3 ingredients_v2.py            # 干跑，打印对比
  python3 ingredients_v2.py --write    # 写 data/ingredients_v2.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

D = Path(__file__).parent
sys.path.insert(0, str(D))
import ingredients as v1  # noqa: E402  复用 LEX / build_matchers / find_ings

RECS = D / 'data' / 'records_cat_400.json'
DETAILS = D / 'data' / 'tikhub_details.json'
OUT = D / 'data' / 'ingredients_v2.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()

    recs = json.load(open(RECS, encoding='utf-8'))['records']
    details = json.load(open(DETAILS, encoding='utf-8')) if DETAILS.is_file() else {}
    matchers = v1.build_matchers()
    fam = {m['canon']: m['family'] for m in matchers}

    n_title = n_both = 0
    n_title_real = n_both_real = n_real = 0
    # 「有 TikTok 描述的那批」单独比 —— 这才是口径升级真正作用到的样本
    d_tot = d_t_title = d_t_both = 0
    newly = []          # 标题没写、描述写了 → 这次新增命中
    per = {}
    out_rec = {}

    for r in recs:
        pid = str(r.get('商品ID') or '')
        title = '%s %s' % (r.get('商品名称') or '', r.get('名称中文') or '')
        dt = details.get(pid) or {}
        desc = dt.get('description') or ''
        is_real = r.get('数据标记') == '真实'
        has_desc = (dt.get('desc_len') or 0) > 50

        hit_t = v1.find_ings(title, matchers)
        hit_d = v1.find_ings(desc, matchers)
        hits = dict(hit_t)
        for k, v in hit_d.items():
            hits.setdefault(k, v)

        if hit_t:
            n_title += 1
        if hits:
            n_both += 1
        if is_real:
            n_real += 1
            if hit_t:
                n_title_real += 1
            if hits:
                n_both_real += 1
        if has_desc:
            d_tot += 1
            if hit_t:
                d_t_title += 1
            if hits:
                d_t_both += 1
        only_desc = sorted(set(hit_d) - set(hit_t))
        if only_desc:
            newly.append({'商品ID': pid, '商品名称': str(r.get('商品名称'))[:44],
                          '国家': r.get('国家/地区'), '来源': r.get('数据来源'),
                          '仅描述命中': only_desc,
                          '描述长度': dt.get('desc_len') or 0})

        out_rec[pid] = {
            '成分': sorted(hits.keys()),
            '标题命中': sorted(hit_t.keys()),
            '仅描述命中': only_desc,
            '描述长度': dt.get('desc_len') or 0,
        }

        for canon in hits:
            a = per.setdefault(canon, {
                '成分': canon, '成分族': fam[canon], '商品数': 0, '仅描述新增': 0,
                '二级类目': collections.Counter(), '国家': collections.Counter(),
                '增速': [], '样例': [],
            })
            a['商品数'] += 1
            if canon in only_desc:
                a['仅描述新增'] += 1
            if r.get('二级类目'):
                a['二级类目'][r['二级类目']] += 1
            if r.get('国家/地区'):
                a['国家'][r['国家/地区']] += 1
            g = r.get('环比增速')
            if isinstance(g, (int, float)):
                a['增速'].append(float(g))
            if len(a['样例']) < 3:
                a['样例'].append('%s（%s）' % (str(r.get('商品名称'))[:32], r.get('国家/地区') or '—'))

    rows = []
    for canon, a in per.items():
        g = sorted(a['增速'])
        rows.append({
            '成分': canon, '成分族': a['成分族'], '商品数': a['商品数'],
            '仅描述新增': a['仅描述新增'],
            '主要二级类目': a['二级类目'].most_common(1)[0][0] if a['二级类目'] else '—',
            '覆盖类目数': len(a['二级类目']),
            '中位环比': (g[len(g) // 2] if g else None),
            '代表商品': a['样例'],
            '来源分布': dict(a['国家'].most_common(4)),
        })
    rows.sort(key=lambda x: -x['商品数'])

    total = len(recs)
    with_desc = sum(1 for v in details.values() if v.get('ok') and (v.get('desc_len') or 0) > 50)
    print('记录 %d 条（真实 %d）｜拉到描述的记录 %d 条' % (total, n_real, d_tot))
    print()
    print('覆盖率对比 A · 分母 = 全部 %d 条（含示例）' % total)
    print('  标题口径（现状）  : %3d 条 = %.0f%%' % (n_title, 100.0 * n_title / total))
    print('  标题+描述（v2）   : %3d 条 = %.0f%%  (+%d 条)' % (n_both, 100.0 * n_both / total, n_both - n_title))
    print()
    print('覆盖率对比 B · 分母 = 真实 %d 条（口径文档用的就是这个）' % n_real)
    print('  标题口径（现状）  : %3d 条 = %.0f%%' % (n_title_real, 100.0 * n_title_real / max(n_real, 1)))
    print('  标题+描述（v2）   : %3d 条 = %.0f%%  (+%d 条)' % (
        n_both_real, 100.0 * n_both_real / max(n_real, 1), n_both_real - n_title_real))
    print()
    print('覆盖率对比 C · 分母 = 真有 TikTok 描述的 %d 条（升级真正作用到的样本）' % d_tot)
    print('  标题口径          : %3d 条 = %.0f%%' % (d_t_title, 100.0 * d_t_title / max(d_tot, 1)))
    print('  标题+描述         : %3d 条 = %.0f%%  (+%d 条)' % (
        d_t_both, 100.0 * d_t_both / max(d_tot, 1), d_t_both - d_t_title))
    print()
    print('成分种类：v1 有 %d 种 → v2 有 %d 种' % (
        len({x for r in recs for x in v1.find_ings('%s %s' % (r.get('商品名称') or '', r.get('名称中文') or ''), matchers)}),
        len(per)))
    print()
    print('TOP 20（按商品数）')
    for x in rows[:20]:
        print('   %-10s %-12s 商品%3d  其中仅描述新增%3d  覆盖类目%2d  %s' % (
            x['成分'], x['成分族'], x['商品数'], x['仅描述新增'], x['覆盖类目数'],
            str(x['代表商品'][0])[:30] if x['代表商品'] else ''))
    print()
    print('描述带来的新增命中（前 15 条商品）')
    for n in newly[:15]:
        print('   %-42s %-6s %s' % (n['商品名称'][:40], n['国家'], '、'.join(n['仅描述命中'][:6])))
    print('   …共 %d 条商品因描述新增了命中' % len(newly))

    if args.write:
        json.dump({
            '口径': '标题 + TikHub 商品描述全文；只抽显性成分词，不推测',
            '统计': {'总记录': total, '真实记录': n_real, '有描述': with_desc,
                     '标题口径命中': n_title, '标题加描述命中': n_both,
                     '真实_标题口径命中': n_title_real, '真实_标题加描述命中': n_both_real,
                     '有描述样本': d_tot, '有描述_标题命中': d_t_title, '有描述_标题加描述命中': d_t_both,
                     '因描述新增商品数': len(newly)},
            '排行': rows,
            '记录': out_rec,
        }, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print()
        print('已写出 %s' % OUT)


if __name__ == '__main__':
    main()
