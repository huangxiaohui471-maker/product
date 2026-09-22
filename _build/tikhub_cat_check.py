#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 TikHub 拿到的**官方三级类目 cid** 反向校验本库「三级类目」映射是否正确。

原理：
  TikHub 详情接口的 category_info.recommended_categories 给的是 TikTok 官方 cid 路径
  （一级/二级/三级），与 FastMoss 的 cid 同源。
  本库每条记录的「三级类目」是中文名 —— 如果这个名字能在 fm_cat_zh.json 的三级表里
  唯一对上，就取它的 cid，与 TikHub 官方 cid 对比：
    agree    = cid 一致 → 映射可信
    differ   = cid 不一致 → 需要人工复核（打印两边路径）
    unnamed  = 本库类目名不在官方三级表里（罗盘/Kimi 自拟名）→ 无法用 cid 校验
    no_data  = 没拉到 TikHub 详情

用法：
  python3 tikhub_cat_check.py
  python3 tikhub_cat_check.py --write    # 写 data/tikhub_cat_check.json
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

D = Path(__file__).parent
DATA = D / 'data'


def build_l3_index():
    """cid -> (l1, l2, l3) 官方路径；l3 中文名 -> [cid...]"""
    tree = json.load(open(DATA / 'fm_cat_zh.json', encoding='utf-8'))['tree']
    by_cid, name_to_cid = {}, collections.defaultdict(list)
    for l1 in tree:
        for l2 in l1.get('children') or []:
            for l3 in l2.get('children') or []:
                cid = str(l3.get('cid'))
                by_cid[cid] = (l1.get('zh'), l2.get('zh'), l3.get('zh'))
                if l3.get('zh'):
                    name_to_cid[l3['zh']].append(cid)
    return by_cid, name_to_cid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()

    recs = json.load(open(DATA / 'records_cat_400.json', encoding='utf-8'))['records']
    det = json.load(open(DATA / 'tikhub_details.json', encoding='utf-8'))
    by_cid, name_to_cid = build_l3_index()

    stat = collections.Counter()
    differs, agrees = [], []
    for r in recs:
        pid = str(r.get('商品ID') or '')
        d = det.get(pid) or {}
        official = [str(c) for c in (d.get('cat_ids') or [])]
        has_off = len(official) >= 3
        ours_name = r.get('三级类目') or ''

        if not d.get('ok'):
            stat['no_data'] += 1
            continue
        if not has_off:
            stat['no_official_cid'] += 1
            continue
        cands = name_to_cid.get(ours_name) or []
        if len(cands) != 1:
            stat['unnamed'] += 1
            continue
        ours_cid = cands[0]
        o_l3 = official[2]
        if ours_cid == o_l3:
            stat['agree'] += 1
            agrees.append({'pid': pid, '名称': str(r.get('商品名称'))[:40],
                           '本库': ours_name, '官方路径': by_cid.get(o_l3, ('?', '?', '?'))})
        else:
            stat['differ'] += 1
            differs.append({
                'pid': pid, '名称': str(r.get('商品名称'))[:48],
                '国家': r.get('国家/地区'), '数据来源': r.get('数据来源'),
                '本库三级': ours_name, '本库cid': ours_cid,
                '本库cid官方路径': by_cid.get(ours_cid, ('?', '?', '?')),
                'TikHub三级cid': o_l3,
                'TikHub官方路径': by_cid.get(o_l3, ('?', '?', '?')),
                'TikHub原始名': (d.get('cat_names') or [None] * 3)[2],
            })

    checked = stat['agree'] + stat['differ']
    print('可校验 %d 条 ｜ 一致 %d ｜ 不一致 %d ｜ 一致率 %s' % (
        checked, stat['agree'], stat['differ'],
        ('%.1f%%' % (100.0 * stat['agree'] / checked)) if checked else '—'))
    print('不可校验：未拉到详情 %d｜官方无三级 cid %d｜本库自拟名 %d' % (
        stat['no_data'], stat['no_official_cid'], stat['unnamed']))
    print()
    if differs:
        print('=== 不一致明细（按本库三级类目聚合）===')
        grp = collections.Counter((x['本库三级'], x['TikHub官方路径'][2]) for x in differs)
        for (ours, off), n in grp.most_common(20):
            print('  %-22s → 官方 %-22s  %d 条' % (ours, off or '—', n))
        print()
        print('样例 3 条：')
        for x in differs[:3]:
            print('  · %s' % x['名称'])
            print('      本库 %s (%s) %s' % (x['本库三级'], x['本库cid'], x['本库cid官方路径']))
            print('      官方 %s %s 原名=%s' % (x['TikHub三级cid'], x['TikHub官方路径'], x['TikHub原始名']))
    if agrees[:3]:
        print()
        print('一致样例 3 条：')
        for x in agrees[:3]:
            print('  · %-40s %s = %s' % (x['名称'], x['本库'], '/'.join(str(v) for v in x['官方路径'])))

    if args.write:
        json.dump({'stat': dict(stat), 'differ': differs,
                   'sample_agree': agrees[:200]},
                  open(DATA / 'tikhub_cat_check.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('\n已写 data/tikhub_cat_check.json')


if __name__ == '__main__':
    main()
