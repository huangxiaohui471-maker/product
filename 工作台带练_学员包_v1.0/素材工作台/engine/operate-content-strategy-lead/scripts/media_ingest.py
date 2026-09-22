#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import urllib.request
import ssl, certifi, subprocess
from urllib.error import URLError
from pathlib import Path

from common import atomic_write_json, now, sha256_file, stable_id
from video_extract import probe, visual_fingerprint,visual_signature


def ingest(source: str, out_dir: Path, creative_id: str | None = None,
           max_bytes: int = 250 * 1024 * 1024, canonical_url: str | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "source.mp4"
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=60,context=ssl.create_default_context(cafile=certifi.where())) as response, target.open("wb") as handle:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes: raise ValueError("视频超过下载上限")
                    handle.write(chunk)
        except URLError:
            curl=shutil.which("curl")
            if not curl: raise
            result=subprocess.run([curl,"--fail","--location","--silent","--show-error","--retry","2","--max-time","180",
                "--max-filesize",str(max_bytes),"--user-agent","Mozilla/5.0","--output",str(target),source],capture_output=True,text=True,timeout=240)
            if result.returncode: raise RuntimeError(f"安全下载失败: curl exit {result.returncode}")
    else:
        src = Path(source).expanduser().resolve()
        if not src.is_file() or src.stat().st_size > max_bytes:
            raise ValueError("本地视频不存在或超过上限")
        shutil.copy2(src, target)
    meta = probe(target);meta["visual_fingerprint"]=visual_fingerprint(target);meta["visual_signature"]=visual_signature(target)
    cid = creative_id or f"manual:{stable_id(sha256_file(target))[:20]}"
    evidence = {
        "schema_version": "creative_evidence/v1", "creative_id": cid,
        "platform": "manual", "canonical_url": canonical_url,
        "author": {}, "published_at": None, "collected_at": now(),
        "metrics": {k: None for k in ["plays", "likes", "comments", "shares", "collects"]},
        "paid_evidence": {"level": "unknown", "sources": ["manual"]},
        "evidence_class": "user_supplied_unverified",
        "organic_metrics": {}, "paid_metrics": {}, "estimated_metrics": {},
        "media": {"local_path": str(target), **meta},
        "source_snapshot_path": None,
        "provenance": {"adapter": "manual", "adapter_version": "1.0", "source_locator_hash": stable_id(source)}
    }
    atomic_write_json(out_dir / "evidence.json", evidence)
    return evidence


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("source"); p.add_argument("--out", required=True); p.add_argument("--id")
    a = p.parse_args(); print(ingest(a.source, Path(a.out), a.id)["creative_id"])
