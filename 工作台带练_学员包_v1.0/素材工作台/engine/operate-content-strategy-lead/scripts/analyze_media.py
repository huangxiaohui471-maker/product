#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import atomic_write_json
from video_extract import extract_audio, extract_strategy_frames
from younavi_transcribe import transcribe as younavi_transcribe


def transcribe(audio: Path | None) -> tuple[list[dict], list[str], dict]:
    if not audio:return [],["audio_unavailable"],{"provider":"none"}
    if os.environ.get("ASR_PROVIDER","younavi")=="none":return [],["asr_disabled_for_test"],{"provider":"none"}
    try:
        segments,meta=younavi_transcribe(audio);return segments,[],meta
    except Exception as error:return [],[f"younavi_asr_failed:{type(error).__name__}"],{"provider":"younavi","error":str(error)[:500]}


def analyze(evidence_path: Path, out_dir: Path) -> dict:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")); video = Path(evidence["media"]["local_path"])
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = extract_strategy_frames(video, out_dir / "frames")
    transcript, degradations, asr_meta = transcribe(extract_audio(video, out_dir / "audio.wav"))
    spoken_chars=sum(len(row.get("text") or "") for row in transcript)
    timed=sum(max(0,(row.get("end") or 0)-(row.get("start") or 0)) for row in transcript if row.get("start") is not None)
    duration=float(evidence.get("media",{}).get("duration_sec") or 0)
    transcript_confidence=round(min(.9,.5*min(1,spoken_chars/80)+.5*min(1,timed/max(1,duration))),3)
    result = {
        "schema_version": "creative_analysis/v1", "creative_id": evidence["creative_id"],
        "route": "scene_fusion", "route_version": "1.0",
        "observations": {"transcript": transcript, "onscreen_text": [], "shots": frames,
                         "people": [], "settings": [], "products": [], "audio": []},
        "interpretations": {"opening_hook": "待多模态模型/人工判读", "target_situation": "",
            "customer_tension": "", "action_answer": "", "proof_devices": [], "offer": "",
            "cta": "", "narrative_structure": [], "production_pattern": ""},
        "confidence": {"transcript": transcript_confidence, "transcript_coverage":round(timed/max(1,duration),3), "interpretations": 0.0},
        "evidence_refs": [f["path"] for f in frames], "model": {"provider": "local", "name": "ffmpeg+younavi", "prompt_version": "none", "asr":asr_meta},
        "degradations": degradations + ["visual_interpretation_pending"]
    }
    atomic_write_json(out_dir / "analysis.json", result); return result


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("evidence"); p.add_argument("--out", required=True)
    a=p.parse_args(); print(analyze(Path(a.evidence), Path(a.out))["route"])
