#!/usr/bin/env python3
"""Low-volume TikHub readiness probe. Never prints credentials or raw rows."""
import json
from tikhub_adapter import search_douyin
try:
    rows=search_douyin("投放素材",1,1)
    print(json.dumps({"ok":True,"returned":len(rows)},ensure_ascii=False))
except Exception as error:
    print(json.dumps({"ok":False,"code":getattr(error,"code",type(error).__name__)},ensure_ascii=False))
    raise SystemExit(1)
