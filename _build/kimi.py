#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kimi 接口客户端（OpenAI 兼容）。

key 存在 secrets/kimi.json（chmod 600），**绝不允许写进任何会发布的 HTML 页面**。
用法:
    from kimi import chat, chat_json
    chat('你好')
    chat_json(system, user)   # 要求模型返回 JSON，自动剥离 ```json 围栏
"""
import json
import os
import re
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE, 'secrets', 'kimi.json')


def load_cfg():
    with open(CFG_PATH, encoding='utf-8') as f:
        return json.load(f)


def _post(url, payload, key, timeout=180):
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
        method='POST')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        # 把服务端返回的具体原因带出来，否则只能看到「400 Bad Request」
        try:
            body = e.read().decode('utf-8')[:300]
        except Exception:                                # noqa: BLE001
            body = ''
        raise RuntimeError('HTTP %s %s' % (e.code, body)) from None


def chat(messages, model=None, max_tokens=4000, retries=3, timeout=180, **_ignored):
    cfg = load_cfg()
    base = cfg['base_url'].rstrip('/')
    key = cfg['api_key']
    models = [model or cfg['model']]
    fb = cfg.get('fallback_model')
    if fb and fb not in models:
        models.append(fb)
    last = None
    for attempt in range(retries):
        for m in models:
            try:
                d = _post(base + '/chat/completions', {
                    'model': m, 'messages': messages, 'max_tokens': max_tokens,
                }, key, timeout=timeout)
                if 'choices' in d:
                    return d['choices'][0]['message'].get('content') or ''
                last = d.get('error', {}).get('message') or str(d)[:200]
            except Exception as e:                       # noqa: BLE001
                last = '%s: %s' % (type(e).__name__, str(e)[:160])
        time.sleep(2 + attempt * 3)
    raise RuntimeError('Kimi 调用失败：%s' % last)


def chat_json(system, user, **kw):
    """要求返回 JSON 数组/对象；模型加了 ``` 围栏也能剥掉。"""
    msgs = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    txt = chat(msgs, **kw)
    return parse_json(txt)


def parse_json(txt):
    t = (txt or '').strip()
    t = re.sub(r'^```[a-zA-Z]*\s*', '', t)
    t = re.sub(r'\s*```$', '', t).strip()
    try:
        return json.loads(t)
    except Exception:                                    # noqa: BLE001
        pass
    # 从自由文本里抠出第一个完整 JSON 数组/对象
    for open_c, close_c in (('[', ']'), ('{', '}')):
        i, j = t.find(open_c), t.rfind(close_c)
        if i >= 0 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:                            # noqa: BLE001
                continue
    raise ValueError('无法从模型输出解析 JSON：%s' % t[:300])


if __name__ == '__main__':
    cfg = load_cfg()
    print('端点:', cfg['base_url'], '| 模型:', cfg['model'])
    print('回答:', chat([{'role': 'user', 'content': '只回三个字：接通了'}], max_tokens=60))
