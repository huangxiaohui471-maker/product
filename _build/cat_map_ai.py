#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给「没有平台类目」的记录（蝉妈妈 50 条）用 Kimi 判一个平台三级类目。

判定边界很硬：只允许从候选清单里挑一个已有类目名，不许自己造词；
挑不出来就给「未定」——宁缺毋滥，避免把品牌品类硬塞进错误的格子里。

用法：python3 cat_map_ai.py [--limit N]
产物：data/cat_ai_map.json  {商品ID: 三级类目名}
"""
import argparse
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kimi  # noqa: E402

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
OUT = os.path.join(D, 'cat_ai_map.json')
BATCH = 10
TASK_VER = 'v1'

SYS = (
    '你是美妆电商类目运营。用户给你一批抖音商品标题，你要为每条挑一个最贴切的平台三级类目。\n'
    '铁律：\n'
    '1. 只能从用户给的「候选类目清单」里原样挑一个，不许自造、不许改写、不许加字。\n'
    '2. 依据只看标题里明说的品类词（洗面奶→洗面乳、唇釉→口红与唇彩、眼霜→眼部护理、沐浴露→沐浴露与香皂）。\n'
    '3. 品牌名、代言人、促销词（如「徐璐同款」「中秋盛典」）一律不作为判类依据。\n'
    '4. 标题里看不出品类，或明显不属于美妆个护，返回「未定」。\n'
    '5. 只输出 JSON 对象：{"序号":"候选类目名 或 未定", ...}，不要解释、不要代码块。\n'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    need = json.load(io.open(os.path.join(D, 'cat_need_ai.json'), encoding='utf-8'))['need']
    if args.limit:
        need = need[:args.limit]
    tree = json.load(io.open(os.path.join(D, 'fm_cat_zh.json'), encoding='utf-8'))['tree']
    bpc = [c for c in tree if c['cid'] == '14'][0]
    cands = [n3['zh'] for n2 in bpc['children'] for n3 in n2['children']]

    try:
        cache = json.load(io.open(OUT, encoding='utf-8'))
    except Exception:                                   # noqa: BLE001
        cache = {}
    if cache.get('_ver') != TASK_VER:
        cache = {'_ver': TASK_VER}

    todo = [x for x in need if x['id'] not in cache]
    print('待判定 %d 条（已缓存 %d）' % (len(todo), len(cache) - 1))

    cl = '候选类目清单（只能从此清单挑）：' + '、'.join(cands)
    for i in range(0, len(todo), BATCH):
        part = todo[i:i + BATCH]
        lines = '\n'.join('%d. %s' % (j + 1, x['标题']) for j, x in enumerate(part))
        user = cl + '\n\n为下面每条标题挑类目，输出 JSON：{"序号":"类目名", ...}\n\n' + lines
        got = None
        for mt in (3500, 5500):
            try:
                got = kimi.chat_json(SYS, user, max_tokens=mt)
            except Exception as e:                      # noqa: BLE001
                print('  第 %d 批失败 %s' % (i // BATCH + 1, str(e)[:100]))
                continue
            if isinstance(got, dict):
                break
        if not isinstance(got, dict):
            continue
        for j, x in enumerate(part):
            v = got.get(str(j + 1)) or got.get(j + 1)
            v = str(v).strip() if v else '未定'
            if v not in cands:
                v = '未定'
            cache[x['id']] = v
        json.dump(cache, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('  第 %d/%d 批完成' % (i // BATCH + 1, (len(todo) + BATCH - 1) // BATCH))
        time.sleep(0.4)

    json.dump(cache, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for k, v in cache.items() if k != '_ver' and v != '未定')
    print('判定完成：%d 条有类目 / %d 条未定' % (ok, len(cache) - 1 - ok))
    for x in need:
        print('  %s  %s  ->  %s' % (x['id'][:12], x['标题'][:34], cache.get(x['id'], '(无)')))


if __name__ == '__main__':
    main()
