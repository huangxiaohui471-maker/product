#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from tikhub_adapter import token
from younavi_transcribe import cli_path


def check() -> dict:
    younavi=cli_path()
    try:
        import openpyxl  # noqa: F401
        xlsx=True
    except ImportError:
        xlsx=False
    checks={
        "python_3_10_plus":sys.version_info >= (3,10),
        "ffmpeg":bool(shutil.which("ffmpeg")),
        "ffprobe":bool(shutil.which("ffprobe")),
        "tikhub_configured":bool(token()),
        "younavi_cli":younavi.is_file(),
        "xlsx_import":xlsx,
    }
    required=("python_3_10_plus","ffmpeg","ffprobe")
    return {"schema_version":"preflight/v1","ready":all(checks[key] for key in required),"checks":checks,
        "notes":{"tikhub_configured":"公开视频发现需要；本地/供应商视频可不需要","younavi_cli":"时间戳转写需要；缺失时明确降级","xlsx_import":"缺失时可改用 UTF-8 CSV"}}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--strict",action="store_true");args=parser.parse_args()
    result=check();print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(1 if args.strict and not result["ready"] else 0)
