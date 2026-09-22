#!/usr/bin/env python3
"""webbridge 调用助手：python3 wb.py <action> ['<json args>'] [session]"""
import json
import sys
import urllib.request

ENDPOINT = 'http://127.0.0.1:10086/command'
SESSION = 'sourcing-v9'


def evaljs(code, session=SESSION, timeout=180):
    """执行 JS 并返回已解包的值；失败抛异常。写脚本时优先用它，别拼 shell。"""
    d = call('evaluate', {'code': code}, session=session, timeout=timeout)
    if isinstance(d, dict) and d.get('ok') is False:
        raise RuntimeError(str(d.get('error'))[:400])
    return unwrap(d)


def evaljson(code, session=SESSION, timeout=180):
    return json.loads(evaljs(code, session=session, timeout=timeout))


def gosleep(sec):
    import time
    time.sleep(sec)


def call(action, args, session=SESSION, timeout=180):
    body = json.dumps({'action': action, 'args': args, 'session': session}).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        raw = r.read().decode('utf-8')
    try:
        d = json.loads(raw)
    except Exception:
        return raw
    return d.get('data', d)


def unwrap(v):
    """evaluate 返回 {type,value}，字符串再解一层 JSON"""
    if isinstance(v, dict) and 'value' in v and 'type' in v:
        v = v['value']
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def main():
    if len(sys.argv) < 2:
        print('usage: wb.py <action> [json-args] [session]')
        return
    action = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else {}
    session = sys.argv[3] if len(sys.argv) > 3 else SESSION
    out = call(action, args, session)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
