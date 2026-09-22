#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从已登录的抖音电商罗盘「体验 → 用户原声」取本店好评/差评关键词与差评原因。

通道：kimi-webbridge（10086）→ 用户真实浏览器里的罗盘登录态
      → 同源 fetch compass_api/shop/promise/user_sound/*（实测无需 a_bogus 签名）

产出 data/douyin_usersound.json：
{
  "shop": "白云山创赢个人护理旗舰店",
  "range": "2026/08/20 ~ 2026/09/18",
  "products": [
     {"商品ID": "...", "商品名称": "...", "类目": "...",
      "评价数": 790, "好评数": 735, "好评率": 0.9304, "差评订单数": 20, "差评率": 0.0329,
      "好评关键词": ["物美价廉","推荐",...],
      "差评关键词": ["描述不符","不推荐"],
      "差评原因": [{"标签":"虚假宣传","数量":4,"占比":0.2353,"原声":"没见有效果，…"}]
     }]
}
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wb import call, unwrap  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
API = 'https://compass.jinritemai.com/compass_api/shop/promise/user_sound'

PAGE_JS = """
(async function(){
  var API = '%(api)s';
  var QS = 'date_type=23&end_date=2026%%2F09%%2F18+00%%3A00%%3A00&begin_date=2026%%2F08%%2F20+00%%3A00%%3A00&version=3';
  async function gj(path){
    var r = await fetch(API + path, {credentials:'include'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    return await r.json();
  }
  function mv(m){
    if(!m) return null;
    var v = m.value;
    if(v && typeof v === 'object') return v.value;
    return v;
  }
  // ---- 1. 商品明细 ----
  var products = [], page = 1;
  while(page <= 20){
    var j = await gj('/product_list?'+QS+'&category_id=0&is_asc=false&page_no='+page+'&page_size=100');
    var rows = j.data || [];
    if(!rows.length) break;
    rows.forEach(function(r){
      var b = (r.base_info||{}).product_base_info||{};
      var m = r.metrics||{};
      products.push({
        id: String(b.id||''), name: b.name||'', cat: (b.category||[]).join(' / '),
        eval_cnt: mv(m.eval_cnt), good_cnt: mv(m.good_eval_cnt),
        good_ratio: mv(m.good_eval_ratio), bad_cnt: mv(m.exp_bad_cmt_order_cnt),
        bad_ratio: mv(m.exp_bad_cmt_ratio), bad_eval_ratio: mv(m.bad_eval_ratio),
        qreturn_cnt: mv(m.ext_prod_qreturn_order_cnt),
        qreturn_ratio: mv(m.ext_prod_qreturn_ratio),
        complaint_cnt: mv(m.ext_complaint_cnt), complaint_ratio: mv(m.ext_complaint_ratio)
      });
    });
    if(rows.length < 100) break;
    page++;
  }
  // ---- 2. 每个商品的好评/差评词 ----
  for(var i=0;i<products.length;i++){
    var pid = products[i].id; if(!pid) continue;
    var out = {good:[], bad:[], reason:[]};
    for(var ct=1; ct<=4; ct++){
      try{
        var jj = await gj('/comment_reason_analysis_right?'+QS+
          '&current=1&pageSize=50&page_size=50&dim_type=1&sort_field=impression_words_cnt&is_asc=false&page_no=1'+
          '&content_id='+pid+'&comment_type='+ct);
        (jj.data||[]).forEach(function(x){
          var bi = x.base_info||{}; var ib = bi.identity_base_info||{};
          var ex = (bi.extra_info||{}).comment_detail||{};
          var item = {label: ib.name||'', n: mv((x.metrics||{}).impression_words_cnt)||0,
                      ratio: mv((x.metrics||{}).impression_words_cnt_value_ratio), sample: ex.value_str||''};
          if(ct===1) out.good.push(item);
          else if(ct===2) out.bad.push(item);
          else if(ct===4) out.reason.push(item);
        });
      }catch(e){
        out['err_'+ct] = String(e).slice(0,60);
      }
    }
    products[i].good = out.good; products[i].bad = out.bad; products[i].reason = out.reason;
    if(out.err_1) products[i].err = out.err_1;
  }
  return JSON.stringify({count: products.length, products: products});
})()
"""


def main():
    # 确保罗盘页在前台（同源才能 fetch）
    call('navigate', {'url': 'https://compass.jinritemai.com/shop/service/user-sound',
                      'newTab': False, 'group_title': '选品·抖音用户原声'})
    time.sleep(7)
    cur = unwrap(call('evaluate', {'code': 'location.href'}))
    if 'user-sound' not in str(cur):
        print('当前不在用户原声页：%s' % cur)
        return
    print('页面就绪：%s' % cur)
    v = call('evaluate', {'code': PAGE_JS % {'api': API}}, timeout=600)
    d = unwrap(v)
    if not isinstance(d, dict) or 'products' not in d:
        print('取数失败：%s' % json.dumps(d, ensure_ascii=False)[:400])
        return
    prods = d['products']
    print('商品数 %d' % len(prods))
    with_good = sum(1 for p in prods if p.get('good'))
    with_reason = sum(1 for p in prods if p.get('reason'))
    print('有差评原因的商品 %d | 有好评关键词的商品 %d' % (with_reason, with_good))
    out = {'shop': '白云山创赢个人护理旗舰店',
           'range': '2026/08/20 ~ 2026/09/18',
           'source': '抖音电商罗盘 · 体验 · 用户原声',
           'count': len(prods), 'products': prods}
    path = os.path.join(D, 'douyin_usersound.json')
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写入 %s' % path)
    for p in prods[:5]:
        print('  - %s | 评价%s 好评%s(%s) 差评订单%s 差评率%s | 好评词%s | 差评原因%s'
              % (p['name'][:24], p['eval_cnt'], p['good_cnt'],
                 round(p['good_ratio'] * 100, 1) if p['good_ratio'] else '-',
                 p['bad_cnt'],
                 round(p['bad_ratio'] * 100, 2) if p['bad_ratio'] else '-',
                 ','.join([g['label'] for g in p['good'][:3]]),
                 ','.join([g['label'] for g in p['reason'][:3]])))


if __name__ == '__main__':
    main()
