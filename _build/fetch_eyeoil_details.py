#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓头部商品 haohuo 详情页文本 v2：滚动加载 + 展开更多参数 + 尝试开 SKU 面板。
-> eyeoil/details/<pid>.txt（首行=商品名）"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from wb import call, unwrap  # noqa: E402

SESSION = 'eyeoil-analysis'
N = int(sys.argv[1]) if len(sys.argv) > 1 else 15
OUTDIR = os.path.join(BASE, 'eyeoil', 'details')
os.makedirs(OUTDIR, exist_ok=True)

rows = json.load(open(os.path.join(BASE, 'eyeoil', 'rank_fiber.json'), encoding='utf-8'))['rows']
seen, targets = set(), []
for r in rows:
    pid = str(r.get('product_id') or '')
    if not pid or pid in seen or not r.get('detail_url'):
        continue
    seen.add(pid)
    targets.append(r)
    if len(targets) >= N:
        break

EXPAND = r"""
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // 1) 滚动触发懒加载
  for (let i = 0; i < 6; i++) { window.scrollTo(0, document.body.scrollHeight); await sleep(800); }
  window.scrollTo(0, 0);
  // 2) 点「更多详细参数」
  const more = [...document.querySelectorAll('div,span,p')].find(e => e.childElementCount === 0 && e.innerText && e.innerText.trim() === '更多详细参数');
  if (more) { more.click(); await sleep(1200); }
  // 3) 尝试打开 SKU 面板（点 加入购物车/去抢购 会弹规格）
  const buyBtn = [...document.querySelectorAll('div,span,button')].find(e => e.childElementCount === 0 && e.innerText && (e.innerText.trim() === '加入购物车'));
  let skuText = '';
  if (buyBtn) {
    buyBtn.click(); await sleep(1500);
    skuText = (document.body.innerText || '').length + '';
  }
  const t = (document.body.innerText || '').replace(/ /g, ' ');
  return t.length + '|||' + t.slice(0, 12000);
})()
"""

print('targets: %d' % len(targets))
first = True
ok = 0
for i, r in enumerate(targets):
    pid = str(r['product_id'])
    url = r['detail_url']
    txt = None
    for attempt in range(2):
        call('navigate', {'url': url, 'newTab': first}, session=SESSION)
        first = False
        time.sleep(6)
        out = unwrap(call('evaluate', {'code': EXPAND}, session=SESSION, timeout=120))
        if isinstance(out, str) and '|||' in out:
            n, body = out.split('|||', 1)
            if int(n) > 300 and '安全验证' not in body[:120] and '滑' not in body[:60]:
                txt = body
                break
        time.sleep(3)
    if txt is None:
        print('[%d] pid=%s FAIL' % (i, pid))
        continue
    with open(os.path.join(OUTDIR, pid + '.txt'), 'w', encoding='utf-8') as f:
        f.write((r.get('name') or '') + '\n')
        f.write('价格: %s | 店铺: %s | 榜单排名: %s\n' % (r.get('price_bin'), r.get('shop_name'), r.get('rank')))
        f.write(txt)
    ok += 1
    print('[%d] pid=%s len=%d %s' % (i, pid, len(txt), (r.get('name') or '')[:26]))
print('DONE ok=%d/%d' % (ok, len(targets)))
