from __future__ import annotations

import json
import shutil
import subprocess
import re
import hashlib
from pathlib import Path

from common import atomic_write_json, sha256_file


def require_ffmpeg() -> tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("需要 FFmpeg/ffprobe 才能处理视频")
    return ffmpeg, ffprobe


def probe(video: Path) -> dict:
    _, ffprobe = require_ffmpeg()
    result = subprocess.run([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)
    ], capture_output=True, text=True, timeout=60, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or "ffprobe failed")[-500:])
    payload = json.loads(result.stdout)
    video_stream = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in payload.get("streams", []) if s.get("codec_type") == "audio"), {})
    return {
        "duration_sec": float((payload.get("format") or {}).get("duration") or 0),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "sha256": sha256_file(video),
    }

def visual_signature(video: Path, max_frames:int=12)->str:
    """Return a normalized-time perceptual timeline signature.

    The centre safe area deliberately ignores the outer 12% where reposted ads
    commonly add title/subtitle bands. Sampling by *relative* duration keeps the
    same story beats aligned after a small speed change. Each frame is a 256-bit
    average hash; keeping the frames separate lets ``signature_distance`` align
    nearby story beats instead of requiring byte-for-byte timeline equality.
    """
    ffmpeg,_=require_ffmpeg()
    duration=max(probe(video).get("duration_sec") or 0,.001)
    sample_rate=max_frames/duration
    vf=(f"fps={sample_rate:.8f},"
        "crop=iw:trunc(ih*0.76/2)*2:0:trunc(ih*0.12/2)*2,"
        "scale=16:16,format=gray")
    result=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-i",str(video),"-vf",vf,
        "-frames:v",str(max_frames),"-f","rawvideo","-"],capture_output=True,timeout=180)
    if result.returncode or not result.stdout:return ""
    bits=bytearray();data=result.stdout
    for start in range(0,len(data),256):
        frame=data[start:start+256]
        if len(frame)<256:break
        mean=sum(frame)/len(frame);value=0
        for i,pixel in enumerate(frame):
            value=(value<<1)|(pixel>=mean)
            if i%8==7:bits.append(value&255);value=0
    return bits.hex() if bits else ""

def visual_fingerprint(video: Path, max_frames:int=12)->str:
    """Stable exact key for the perceptual signature."""
    signature=visual_signature(video,max_frames)
    return hashlib.sha256(bytes.fromhex(signature)).hexdigest() if signature else ""

def signature_distance(left:str,right:str)->float:
    """Perceptual distance with local temporal alignment; 0 means identical.

    Dynamic programming permits a one-frame insertion/deletion, which absorbs
    encoder rounding and mild speed edits. A non-zero gap cost prevents unrelated
    sequences from becoming similar merely by skipping most of their frames.
    """
    try:a,b=bytes.fromhex(left),bytes.fromhex(right)
    except ValueError:return 1.0
    frame_bytes=32
    aa=[a[i:i+frame_bytes] for i in range(0,len(a),frame_bytes) if len(a[i:i+frame_bytes])==frame_bytes]
    bb=[b[i:i+frame_bytes] for i in range(0,len(b),frame_bytes) if len(b[i:i+frame_bytes])==frame_bytes]
    if not aa or not bb:return 1.0
    def frame_distance(x:bytes,y:bytes)->float:
        return sum((p^q).bit_count() for p,q in zip(x,y))/(frame_bytes*8)
    gap=.18
    previous=[j*gap for j in range(len(bb)+1)]
    for i,x in enumerate(aa,1):
        current=[i*gap]
        for j,y in enumerate(bb,1):
            current.append(min(previous[j-1]+frame_distance(x,y),previous[j]+gap,current[j-1]+gap))
        previous=current
    return round(min(1.0,previous[-1]/max(len(aa),len(bb))),6)


def extract_fixed_frames(video: Path, output: Path, interval_sec: float = 2.0, max_frames: int = 18) -> list[dict]:
    ffmpeg, _ = require_ffmpeg()
    output.mkdir(parents=True, exist_ok=True)
    pattern = output / "frame_%03d.jpg"
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vf", f"fps=1/{interval_sec},scale='min(720,iw)':-2", "-frames:v", str(max_frames),
        "-q:v", "3", str(pattern)
    ], capture_output=True, text=True, timeout=180, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or "frame extraction failed")[-500:])
    frames = []
    for index, path in enumerate(sorted(output.glob("frame_*.jpg"))):
        frames.append({"path": str(path), "timestamp_sec": round(index * interval_sec, 3), "sha256": sha256_file(path)})
    if not frames:
        raise RuntimeError("视频没有产生可用帧")
    atomic_write_json(output / "frames.json", frames)
    return frames


def extract_audio(video: Path, output: Path) -> Path | None:
    ffmpeg, _ = require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(output)
    ], capture_output=True, text=True, timeout=180, check=False)
    if result.returncode:
        return None
    return output if output.is_file() and output.stat().st_size else None


def extract_scene_frames(video: Path, output: Path, threshold: float = 0.28,
                         max_frames: int = 24) -> list[dict]:
    """Extract visual change points. Falls back to fixed sampling if cuts are scarce."""
    ffmpeg, _ = require_ffmpeg()
    output.mkdir(parents=True, exist_ok=True)
    pattern = output / "scene_%03d.jpg"
    vf = f"select='gt(scene,{threshold})',showinfo,scale='min(720,iw)':-2"
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-i", str(video), "-vf", vf, "-vsync", "vfr",
        "-frames:v", str(max_frames), "-q:v", "3", str(pattern)
    ], capture_output=True, text=True, timeout=240, check=False)
    if result.returncode:
        return extract_fixed_frames(video, output / "fallback", interval_sec=2.0, max_frames=max_frames)
    timestamps = [float(v) for v in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    paths = sorted(output.glob("scene_*.jpg"))
    if len(paths) < 2:
        return extract_fixed_frames(video, output / "fallback", interval_sec=2.0, max_frames=max_frames)
    frames = [{"path": str(path), "timestamp_sec": round(timestamps[i] if i < len(timestamps) else 0, 3),
               "sha256": sha256_file(path)} for i, path in enumerate(paths)]
    atomic_write_json(output / "frames.json", frames)
    return frames


def extract_strategy_frames(video: Path, output: Path, max_frames: int = 24) -> list[dict]:
    """Ad-oriented sampler: opening density + scene cuts + uniform floor + ending CTA."""
    meta = probe(video); duration = meta["duration_sec"]
    opening = [t for t in (0, .25, .5, .75, 1, 1.5, 2, 3) if t <= duration]
    ending = [max(0, duration - delta) for delta in (3, 2.5, 2, 1.5, 1, .5, .1)]
    uniform = [duration * i / 6 for i in range(1, 6)] if duration else []
    ffmpeg, _ = require_ffmpeg(); output.mkdir(parents=True, exist_ok=True)
    frames=[]
    for i, timestamp in enumerate(sorted(set(round(t, 3) for t in opening + uniform + ending))[:max_frames]):
        path=output/f"key_{i:03d}.jpg"
        result=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-ss",str(timestamp),"-i",str(video),
            "-frames:v","1","-vf","scale='min(720,iw)':-2","-q:v","3",str(path)],capture_output=True,text=True,timeout=60)
        if result.returncode == 0 and path.exists(): frames.append({"path":str(path),"timestamp_sec":timestamp,"sha256":sha256_file(path),"sampling":"opening_uniform_ending"})
    scene=extract_scene_frames(video,output/"scenes",max_frames=max(0,max_frames-len(frames))) if len(frames)<max_frames else []
    known={f["sha256"] for f in frames}
    frames.extend({**f,"sampling":"scene"} for f in scene if f["sha256"] not in known)
    frames=sorted(frames,key=lambda x:x["timestamp_sec"])[:max_frames]
    atomic_write_json(output/"frames.json",frames); return frames
