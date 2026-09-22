#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测各评价渠道的登录态与可抓性。每个渠道新开标签，探测后保留供用户查看。"""
import json
import sys
import time
import urllib.parse

sys.path.insert(0, '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build')
from wb import call, unwrap  # noqa: E402

SESSION = 'review-probe'

PROBE_JS = r'''
(function(){
  var t = document.body ? document.body.innerText.replace(/\s+/g,' ').slice(0,1400) : '';
  var needLogin = /登录|扫码|登陆|Sign in|Log in|请先登录/.test(t);
  return JSON.stringify({url: location.href, title: document.title, needLogin: needLogin, sample: t.slice(0,420)});
})()
'''

TARGETS = [
    ('xiaohongshu', 'https://www.xiaohongshu.com/search_result?keyword=' + urllib.parse.quote('防晒霜')),
    ('douyin', 'https://www.douyin.com/'),
    ('taobao', 'https://www.taobao.com/'),
]

out = {}
for name, url in TARGETS:
    try:
        r = call('navigate', {'url': url, 'newTab': True, 'group_title': '评价源探测'}, SESSION)
        time.sleep(5)
        got = unwrap(call('evaluate', {'code': PROBE_JS}, SESSION))
        if isinstance(got, str):
            got = json.loads(got)
        out[name] = got
        print('== %s ==' % name)
        print('   needLogin:', got.get('needLogin'), '| title:', (got.get('title') or '')[:50])
        print('   sample:', (got.get('sample') or '')[:260])
    except Exception as e:
        print('== %s == ERR %s' % (name, str(e)[:180]))

json.dump(out, open('/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/data/review_probe.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
