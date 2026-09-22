#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在已登录的抖音电商罗盘里找「评价 / 体验」入口。"""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from wb import call, unwrap  # noqa: E402

call('navigate', {'url': 'https://compass.jinritemai.com/shop', 'newTab': True,
                  'group_title': '选品·罗盘评价'})
time.sleep(6)
v = call('evaluate', {'code': """(function(){
  var out=[];
  document.querySelectorAll('a[href]').forEach(function(a){
    var h=a.getAttribute('href')||''; var t=(a.innerText||'').trim();
    if(t && t.length<14) out.push(t+' -> '+h);
  });
  // 菜单里可能有非 a 标签
  document.querySelectorAll('[class*="menu"] [class*="item"],[class*="Menu"] [class*="Item"]').forEach(function(e){
    var t=(e.innerText||'').trim(); if(t && t.length<14) out.push('[menu] '+t);
  });
  return JSON.stringify({url:location.href, links:Array.from(new Set(out)).slice(0,150)});
})()"""})
d = unwrap(v)
print(json.dumps(d, ensure_ascii=False, indent=1)[:4000])
