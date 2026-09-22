#!/usr/bin/env python3
"""TikHub API 客户端（选品取数通道）

token 读取顺序：环境变量 TIKHUB_API_TOKEN -> ~/.config/content-creative-intelligence/tikhub.json
统一直连（绕开 Clash TUN 代理），失败重试 3 次。
"""
from __future__ import annotations

import json
import os
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

try:
    import certifi
except ImportError:
    certifi = None

BASE = os.environ.get('TIKHUB_BASE_URL', 'https://api.tikhub.io').rstrip('/')
CONF = Path.home() / '.config' / 'content-creative-intelligence' / 'tikhub.json'
_CTX = ssl.create_default_context(cafile=certifi.where() if certifi else None)
_OPENER = build_opener(ProxyHandler({}), HTTPSHandler(context=_CTX))


def token() -> str:
    v = os.environ.get('TIKHUB_API_TOKEN', '').strip()
    if v:
        return v
    if CONF.is_file():
        d = json.loads(CONF.read_text(encoding='utf-8-sig'))
        return str(d.get('api_token') or d.get('tikhub_api_token') or '').strip()
    return ''


def get(path: str, params: dict | None = None, retry: int = 3, timeout: int = 45) -> dict:
    """GET 请求。返回 JSON dict。"""
    url = BASE + path
    if params:
        url += '?' + urlencode({k: v for k, v in params.items() if v is not None})
    req = Request(url, headers={
        'Authorization': f'Bearer {token()}',
        'Accept': 'application/json',
        'User-Agent': 'XuanpinPlatform/1.0',
    })
    last = None
    for i in range(retry):
        try:
            with _OPENER.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except HTTPError as e:
            body = ''
            try:
                body = e.read().decode('utf-8')[:300]
            except Exception:
                pass
            last = f'HTTP {e.code} {body}'
            if e.code in (401, 403, 402):
                break
            time.sleep(2 ** i)
        except (URLError, TimeoutError, OSError) as e:
            last = f'{type(e).__name__}: {e}'
            time.sleep(2 ** i)
    return {'_error': last, '_url': url}


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        p = sys.argv[1]
        q = dict(x.split('=', 1) for x in sys.argv[2:] if '=' in x)
        print(json.dumps(get(p, q), ensure_ascii=False, indent=1)[:4000])
    else:
        print('token:', (token()[:12] + '...') if token() else '(未配置)')
