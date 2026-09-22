#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐条打开 Olive Young 商品页，读「평점(评分) / 리뷰 건수(评价数) / 리뷰 텍스트 여부」。

榜单页不给评分与评价数，只有商品详情页渲染后才出现（异步接口，无公开 JSON）。
因此用 webbridge 在同一标签页里轮换导航、读 DOM，结果落盘并可断点续跑。

输入: data/oliveyoung_rank.json
输出: data/oy_detail.json   {goodsNo: {star, reviews, soldout}}
用法: python3 oy_detail.py [--limit 100] [--resume]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
sys.path.insert(0, HERE)
import wb  # noqa: E402

DETAIL = 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=%s'

READ_JS = r'''(()=>{
const t=document.body.innerText||'';
const star=(t.match(/평점[\s\S]{0,20}?([0-5]\.\d)/)||[])[1]||null;
const rev=(t.match(/리뷰\s*([0-9,]+)\s*건/)||[])[1]||null;
const soldout=/일시품절|품절/.test(t.slice(0,1500));
return JSON.stringify({star:star, rev:rev, soldout:soldout, len:t.length,
  title:(document.title||'').slice(0,60)})})()'''


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    out_path = os.path.join(D, 'oy_detail.json')
    done = {}
    if '--resume' in sys.argv and os.path.exists(out_path):
        done = json.load(open(out_path, encoding='utf-8'))
        print('续跑：已有 %d 条' % len(done))

    rows = json.load(open(os.path.join(D, 'oliveyoung_rank.json'), encoding='utf-8'))
    todo = [x for x in rows if x['no'] not in done][:limit]
    print('待抓 %d 条' % len(todo))

    for i, x in enumerate(todo, 1):
        no = x['no']
        try:
            wb.call('navigate', {'url': DETAIL % no, 'newTab': False}, timeout=60)
            time.sleep(5.5)
            wb.call('evaluate', {'code': 'window.scrollBy(0,600)'}, timeout=30)
            time.sleep(1.2)
            d = wb.evaljs(READ_JS)
            done[no] = d
            print('  %3d/%d %s 평점=%s 리뷰=%s' % (i, len(todo), no, d.get('star'), d.get('rev')))
        except Exception as e:  # noqa: BLE001
            print('  %3d/%d %s 失败: %s' % (i, len(todo), no, str(e)[:110]))
            done[no] = {'error': str(e)[:160]}
        if i % 10 == 0:
            json.dump(done, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(done, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for v in done.values() if v.get('star'))
    print('完成：%d 条有评分 / 共 %d 条 -> %s' % (ok, len(done), out_path))


if __name__ == '__main__':
    main()
