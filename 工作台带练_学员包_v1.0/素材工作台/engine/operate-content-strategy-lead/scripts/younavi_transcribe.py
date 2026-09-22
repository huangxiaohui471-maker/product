from __future__ import annotations
import json,os,re,shutil,subprocess
from pathlib import Path

def cli_path()->Path:
    override=os.environ.get("YOUNAVI_AGENT_CLI","").strip()
    candidates=[
        Path(override) if override else None,
        Path("/Applications/YouNavi.app/Contents/Resources/backend/agent-cli"),
        Path.home()/"AppData/Local/Programs/YouNavi/resources/backend/agent-cli.exe",
        Path.home()/"AppData/Local/YouNavi/resources/backend/agent-cli.exe",
        Path(shutil.which("agent-cli") or ""),
    ]
    return next((path for path in candidates if path and path.is_file()),Path("agent-cli"))
LINE=re.compile(r"^\[(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})\]\s*(?:([^:]+):\s*)?(.*)$")

def _sec(minutes:str,seconds:str)->int:return int(minutes)*60+int(seconds)

def parse_text(text:str)->list[dict]:
    segments=[]
    for line in text.splitlines():
        match=LINE.match(line.strip())
        if match:segments.append({"start":_sec(match[1],match[2]),"end":_sec(match[3],match[4]),"speaker":(match[5] or "").strip() or None,"text":match[6].strip()})
    if not segments and text.strip():segments=[{"start":None,"end":None,"speaker":None,"text":text.strip()}]
    return segments

def transcribe(audio:Path)->tuple[list[dict],dict]:
    cli=cli_path()
    if not cli.is_file():raise RuntimeError("没有找到 YouNavi；请先打开并登录 YouNavi")
    result=subprocess.run([str(cli),"-f","json","audio","transcribe",str(audio)],capture_output=True,text=True,timeout=1800)
    try:payload=json.loads(result.stdout)
    except Exception as error:raise RuntimeError((result.stderr or result.stdout or "YouNavi 返回非 JSON")[-1000:]) from error
    if result.returncode or not payload.get("success"):raise RuntimeError(str(payload.get("error") or payload.get("message") or "YouNavi 转写失败"))
    data=payload.get("data") or {};text=str(data.get("text") or "");segments=parse_text(text)
    return segments,{"provider":"younavi","output_path":data.get("output_path"),"has_timestamps":all(x["start"] is not None for x in segments)}
