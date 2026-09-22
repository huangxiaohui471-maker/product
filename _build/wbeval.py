#!/usr/bin/env python3
"""从 .js 文件读代码执行 evaluate：python3 wbeval.py <code.js> [session]"""
import json
import sys

sys.path.insert(0, '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build')
from wb import call, unwrap  # noqa: E402


def main():
    path = sys.argv[1]
    session = sys.argv[2] if len(sys.argv) > 2 else 'xuanpin-fetch'
    code = open(path, 'r', encoding='utf-8').read()
    out = call('evaluate', {'code': code}, session)
    print(json.dumps(unwrap(out), ensure_ascii=False))


if __name__ == '__main__':
    main()
