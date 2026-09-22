#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语义对比两个页面：剥离平台注入属性 + 属性排序 + 折叠空白后，列出真正的改动片段。

用法： python3 sem_diff.py <文件A> <文件B> [--max 12]
"""
from __future__ import annotations

import difflib
import re
import sys


def norm(path: str) -> str:
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'\sdata-page-node-id="[^"]*"', '', s)
    s = re.sub(r'\sdata-pnid-children="[^"]*"', '', s)
    s = re.sub(r'<!--pnid:[^>]*-->', '', s)
    s = re.sub(r'<script[^>]*src="/page/page_comm/inject\.js"[^>]*></script>', '', s)

    def sort_attrs(m):
        tag, inner = m.group(1), m.group(2)
        if not inner or inner.startswith('/'):
            return m.group(0)
        parts = re.findall(r'[\w:.-]+(?:="[^"]*")?', inner)
        return '<%s %s>' % (tag, ' '.join(sorted(parts)))

    s = re.sub(r'<(\w[\w-]*)((?:\s+[\w:.-]+(?:="[^"]*")?)*)\s*/?>', sort_attrs, s)
    s = re.sub(r'\s+', ' ', s)
    return s


def main():
    a, b = sys.argv[1], sys.argv[2]
    mx = 12
    if '--max' in sys.argv:
        mx = int(sys.argv[sys.argv.index('--max') + 1])
    sa, sb = norm(a), norm(b)
    print('A %d 字符 ｜ B %d 字符' % (len(sa), len(sb)))
    sm = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    print('改动片段数: %d' % len(ops))
    for tag, i1, i2, j1, j2 in ops[:mx]:
        print('\n--- %s  A[%d:%d] B[%d:%d]' % (tag, i1, i2, j1, j2))
        print('  A: %s' % repr(sa[i1:i2])[:400])
        print('  B: %s' % repr(sb[j1:j2])[:400])
    if len(ops) > mx:
        print('\n…还有 %d 个片段' % (len(ops) - mx))


if __name__ == '__main__':
    main()
