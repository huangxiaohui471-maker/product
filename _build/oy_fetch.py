#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 Olive Young 韩国站「판매랭킹」(Best Selling) 榜单。

前置：浏览器已打开 https://www.oliveyoung.co.kr/store/main/getBestList.do
      （webbridge daemon 在 127.0.0.1:10086，会话 sourcing-v9）

做法：榜单页每个 <li> 的商品节点自带
  data-ref-goodsno         商品号 A000000xxxxxx
  data-ref-goodsnm/brand   品名 / 品牌
  data-ref-goodscategory   三级类目路径  "01 > 마스크팩 > 시트팩"
  data-ref-goodstrackingno 榜单排名
  .prd_price .tx_cur .tx_num  现价（韩元）
分片 evaluate 取回（单次返回体量受限），合并落盘 data/oliveyoung_rank.json。

用法: python3 oy_fetch.py [--pages 100]
"""
import json
import sys
import urllib.request

ENDPOINT = 'http://127.0.0.1:10086/command'
SESSION = 'sourcing-v9'
OUT = 'data/oliveyoung_rank.json'

JS_TMPL = """(()=>{{
const lis=[...document.querySelectorAll('li')].filter(x=>x.querySelector('[data-ref-goodsno]'));
const F=(x,i)=>{{
  const g=x.querySelector('[data-ref-goodstrackingno]');
  const c=x.querySelector('[data-ref-goodscategory]');
  const n=x.querySelector('.tx_name');
  const b=x.querySelector('.tx_brand');
  const p=x.querySelector('.prd_price .tx_cur .tx_num')||x.querySelector('.prd_price .tx_num');
  return {{r:g?+g.getAttribute('data-ref-goodstrackingno'):i+1,
    no:g?g.getAttribute('data-ref-goodsno'):'',
    b:(b?b.innerText:'').trim(),
    n:(n?n.innerText:'').trim(),
    c:c?c.getAttribute('data-ref-goodscategory'):'',
    p:p?(p.innerText||'').replace(/[^0-9]/g,''):''}};
}};
return JSON.stringify({{total:lis.length,rows:lis.slice({a},{b}).map((x,i)=>F(x,{a}+i))}});
}})()"""


def call(action, args):
    body = json.dumps({'action': action, 'args': args, 'session': SESSION}).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def evaluate(code):
    d = call('evaluate', {'code': code})
    if not d.get('ok'):
        raise RuntimeError(str(d.get('error'))[:300])
    return d['data']['value']


def main():
    total = int(sys.argv[sys.argv.index('--pages') + 1]) if '--pages' in sys.argv else 100
    rows, got = [], 0
    while got < total:
        v = json.loads(evaluate(JS_TMPL.format(a=got, b=min(got + 25, total))))
        page = v['rows']
        if not page:
            break
        rows += page
        got += len(page)
        print('  已取 %d/%d（页面共 %d 个商品节点）' % (got, total, v['total']))
        if got >= v['total']:
            break
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    import collections
    print('落盘 %s：%d 条' % (OUT, len(rows)))
    l2 = collections.Counter((x['c'].split(' > ') or [''])[1] if ' > ' in x['c'] else '(无类目)' for x in rows)
    print('中类目分布:', dict(l2))
    print('前 8 条:')
    for x in rows[:8]:
        print('  #%-3d %-12s %-42s %7s원  %s' % (x['r'], x['b'][:11], x['n'][:40], x['p'], x['c']))


if __name__ == '__main__':
    main()
