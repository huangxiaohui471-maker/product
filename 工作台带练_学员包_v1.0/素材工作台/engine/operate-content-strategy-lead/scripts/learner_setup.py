#!/usr/bin/env python3
"""One-time learner configuration. Keep credentials in user config, never in the Skill."""
from __future__ import annotations
import argparse,getpass,json,os,stat
from pathlib import Path
from common import atomic_write_json

CONFIG=Path.home()/".config/content-creative-intelligence/tikhub.json"

def configure(value:str)->Path:
    token=value.strip()
    if not token:raise ValueError("TikHub Token 不能为空")
    CONFIG.parent.mkdir(parents=True,exist_ok=True)
    atomic_write_json(CONFIG,{"api_token":token})
    try:CONFIG.chmod(stat.S_IRUSR|stat.S_IWUSR)
    except OSError:pass
    return CONFIG

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="第一次使用只需保存 TikHub Token")
    parser.add_argument("--tikhub-token",default=os.environ.get("TIKHUB_API_TOKEN",""))
    args=parser.parse_args();value=args.tikhub_token
    if not value:value=getpass.getpass("请粘贴 TikHub Token（输入不会显示）：")
    configure(value)
    print(json.dumps({"ok":True,"message":"素材库已接好。以后直接说：开工。"},ensure_ascii=False))
