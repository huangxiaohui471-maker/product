#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 webbridge 从蝉妈妈「商品销量榜」翻页取数（Vue 实例取明文值）。

前提：webbridge 守护进程在 127.0.0.1:10086，且宿主机浏览器已登录蝉妈妈、
      已把类目切到「美妆护肤」（multi_category_id=8）。
用法: python3 cm_wb_fetch.py [pages]      # 默认 5 页 ≈ 50-100 条
输出: data/chanmama_beauty.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wb import call, unwrap  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
CODE = open(os.path.join(BASE, 'js', 'cm_beauty.js'), encoding='utf-8').read()
OUT = os.path.join(D, 'chanmama_beauty.json')
PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 5

CLICK_NEXT = r"""(() => {
  const cands = [
    '.ant-pagination-next:not(.ant-pagination-disabled)',
    'li.ant-pagination-next:not([aria-disabled="true"])',
    '.ant-pagination-next button',
    '.el-pagination .btn-next'
  ];
  for (const sel of cands) {
    const el = document.querySelector(sel);
    if (el) { el.click(); return 'clicked:' + sel; }
  }
  const items = [...document.querySelectorAll('li[title="下一页"],a[title="下一页"],[aria-label="下一页"]')];
  if (items.length) { items[0].click(); return 'clicked:title'; }
  return 'no-pager';
})()"""


def main():
    r = call('find_tab', {'url': 'chanmama.com'})
    if not r or not r.get('tabId'):
        print('FAIL 没找到蝉妈妈标签页（webbridge 未连接或标签已关）')
        sys.exit(2)

    all_rows = []
    meta = {}
    for n in range(1, PAGES + 1):
        got = None
        for _ in range(3):
            time.sleep(2.5)
            try:
                out = unwrap(call('evaluate', {'code': CODE}))
            except Exception as e:                       # noqa: BLE001
                print('page %d evaluate 异常 %s' % (n, str(e)[:80]))
                out = None
            if isinstance(out, dict) and out.get('ok') and out.get('rows'):
                got = out
                break
        if not got:
            print('page %d -> 空（可能已到末页或需要重新切类目）' % n)
            break
        meta = got.get('filters', {})
        for row in got['rows']:
            row['page'] = n
            all_rows.append(row)
        print('page %d -> %d 行（首个：%s）' % (n, len(got['rows']), (got['rows'][0].get('title') or '')[:26]))
        if n < PAGES:
            print('  翻页:', str(unwrap(call('evaluate', {'code': CLICK_NEXT})))[:40])

    os.makedirs(D, exist_ok=True)
    json.dump({'source': '蝉妈妈', 'list': '商品销量榜（美妆护肤）', 'meta': meta,
               'fetchedAt': time.strftime('%Y-%m-%dT%H:%M:%S'),
               'count': len(all_rows), 'rows': all_rows},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ids = {x['product_id'] for x in all_rows if x.get('product_id')}
    print('SAVED %s 共 %d 条（唯一 %d）' % (OUT, len(all_rows), len(ids)))


if __name__ == '__main__':
    main()
