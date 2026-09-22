#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 webbridge 浏览器里探测评价源登录态。"""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from wb import call, unwrap  # noqa: E402

SITES = [
    ('淘宝', 'https://www.taobao.com/', """(function(){var t=document.body?document.body.innerText:'';
      return JSON.stringify({url:location.href,needLogin:/亲，请登录|请登录/.test(t),logged:/我的淘宝|退出|千牛/.test(t),len:t.length});})()"""),
    ('天猫', 'https://www.tmall.com/', """(function(){var t=document.body?document.body.innerText:'';
      return JSON.stringify({url:location.href,needLogin:/请登录/.test(t),logged:/我的淘宝|退出/.test(t),len:t.length});})()"""),
    ('小红书', 'https://www.xiaohongshu.com/explore', """(function(){var t=document.body?document.body.innerText:'';
      return JSON.stringify({url:location.href,needLogin:/扫码登录|登录/.test(t),logged:/发布|创作中心/.test(t),len:t.length});})()"""),
    ('抖音', 'https://www.douyin.com/', """(function(){var t=document.body?document.body.innerText:'';
      return JSON.stringify({url:location.href,needLogin:/登录|扫码/.test(t),logged:/我的|发布/.test(t),len:t.length});})()"""),
    ('蝉妈妈', 'https://www.chanmama.com/', """(function(){var t=document.body?document.body.innerText:'';
      return JSON.stringify({url:location.href,needLogin:/登录|注册/.test(t),logged:/会员|退出/.test(t),len:t.length});})()"""),
    ('罗盘', 'https://compass.jinritemai.com/shop', """(function(){var t=document.body?document.body.innerText:'';
      return JSON.stringify({url:location.href,len:t.length,head:t.slice(0,80)});})()"""),
]

for name, url, code in SITES:
    r = call('navigate', {'url': url, 'newTab': True, 'group_title': '选品·评价源探测'})
    if not r.get('success'):
        print(name, ':: 打开失败', json.dumps(r, ensure_ascii=False)[:160])
        continue
    time.sleep(4)
    v = call('evaluate', {'code': code})
    print(name, '::', json.dumps(unwrap(v), ensure_ascii=False))
