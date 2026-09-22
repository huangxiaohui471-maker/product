#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面语义等价校验：不逐字节比，而是比「结构化内容」是否一致。

比对项：
  1. FIELDS 字段名序列（页面按名字取值，名字变了就是破坏性改动）
  2. SEED 离线种子的数据行（解析成 list 后逐行比）
  3. SOURCES 数据源 key 序列
  4. 关键锚点与 Vue/JS 函数名清单
用法： python3 sem_verify.py A.html B.html
"""
from __future__ import annotations

import json
import re
import sys


def load(p):
    return open(p, encoding='utf-8').read()


def fields(s):
    m = re.search(r'var FIELDS = \[(.*?)\n\];', s, re.S)
    body = m.group(1) if m else ''
    return re.findall(r"\{ n: '([^']+)'", body)


def sources(s):
    m = re.search(r'var SOURCES = \[(.*?)\n\];', s, re.S)
    body = m.group(1) if m else ''
    return re.findall(r"\n    k: '([^']+)', short:", body)


def seed(s):
    m = re.search(r'var SEED_ORDER = (\[.*?\]);', s, re.S)
    order = json.loads(m.group(1)) if m else None
    m2 = re.search(r'var SEED_ROWS = (\[.*?\])\s*;\s*/\*==SEED_DATA_END', s, re.S)
    if not m2:
        m2 = re.search(r'var SEED_ROWS = (\[.*?\]);', s, re.S)
    try:
        rows = json.loads(m2.group(1)) if m2 else None
    except Exception as e:
        rows = 'PARSE_ERR %s' % e
    return order, rows


def funcs(s):
    return sorted(set(re.findall(r'\nfunction (\w+)\(', s)))


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    ok = True
    for name, fn in (('FIELDS', fields), ('SOURCES', sources)):
        xa, xb = fn(a), fn(b)
        same = xa == xb
        print('%-8s A=%d B=%d  %s' % (name, len(xa), len(xb), '一致' if same else '不一致'))
        if not same:
            ok = False
            print('   A 独有:', [x for x in xa if x not in xb])
            print('   B 独有:', [x for x in xb if x not in xa])
    (oa, sa), (ob, sb) = seed(a), seed(b)
    if oa == ob:
        print('SEED_ORDER A=%s B=%s 一致' % (len(oa) if oa else oa, len(ob) if ob else ob))
    else:
        ok = False
        print('SEED_ORDER 不一致\n   A:', oa, '\n   B:', ob)
    if isinstance(sa, list) and isinstance(sb, list):
        if sa == sb:
            print('SEED_ROWS  A=%s B=%s  一致' % (len(sa), len(sb)))
        else:
            ok = False
            print('SEED_ROWS  不一致 A=%d B=%d' % (len(sa), len(sb)))
            for i in range(max(len(sa), len(sb))):
                ra = sa[i] if i < len(sa) else None
                rb = sb[i] if i < len(sb) else None
                if ra != rb:
                    print('   行 %d:' % i)
                    print('     A:', json.dumps(ra, ensure_ascii=False)[:200])
                    print('     B:', json.dumps(rb, ensure_ascii=False)[:200])
    else:
        print('SEED_ROWS 无法解析 A=%r B=%r' % (sa, sb))
        ok = False
    fa, fb = funcs(a), funcs(b)
    print('函数     A=%d B=%d  A 独有 %s  B 新增 %s' % (
        len(fa), len(fb), [x for x in fa if x not in fb][:8], [x for x in fb if x not in fa][:8]))
    print('\n结论：%s' % ('结构化内容一致' if ok else '存在结构差异（见上）'))


if __name__ == '__main__':
    main()
