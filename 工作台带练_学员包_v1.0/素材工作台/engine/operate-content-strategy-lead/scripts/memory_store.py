from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import json
from common import append_jsonl, atomic_write_json, atomic_write_text, now, read_json, read_jsonl, stable_id
from video_extract import signature_distance
from clustering import mechanism_key as normalized_mechanism_key

EVIDENCE_RANK={"user_supplied_unverified":0,"public_content_only":1,"commercial_like_proxy":2,"third_party_ad_library":3,"authorized_top_ad":4,"verified_paid_platform_library":5,"verified_paid_owned_account":6}


class MemoryStore:
    def __init__(self, workspace: Path):
        self.root = workspace / "memory"
        self.root.mkdir(parents=True, exist_ok=True)
        self.seen_path = self.root / "seen_creatives.jsonl"
        self.decisions_path = self.root / "decisions.jsonl"
        self.patterns_path = self.root / "pattern_history.jsonl"
        self.cooldowns_path = self.root / "cooldowns.json"
        self.run_path = self.root / "run_history.jsonl"

    def seen_index(self) -> dict[str, dict[str, Any]]:
        return {row["creative_id"]: row for row in read_jsonl(self.seen_path)}

    def match_seen(self, creative:dict[str,Any])->dict[str,Any]|None:
        cid=creative["creative_id"];media=(creative.get("media") or {}).get("sha256");visual=(creative.get("media") or {}).get("visual_fingerprint");signature=(creative.get("media") or {}).get("visual_signature")
        for row in self.seen_index().values():
            if row.get("creative_id")==cid or (media and row.get("media_sha256")==media) or (visual and row.get("visual_fingerprint")==visual):return row
            if signature and row.get("visual_signature") and signature_distance(signature,row["visual_signature"])<=.08:return row
        return None

    def mark_seen(self, creative: dict[str, Any], run_id: str) -> bool:
        creative_id = creative["creative_id"]
        index = self.seen_index()
        media_hash = (creative.get("media") or {}).get("sha256")
        visual=(creative.get("media") or {}).get("visual_fingerprint")
        signature=(creative.get("media") or {}).get("visual_signature")
        matched=self.match_seen(creative)
        if matched:
            old_rank=EVIDENCE_RANK.get(matched.get("evidence_class"),-1);new_rank=EVIDENCE_RANK.get(creative.get("evidence_class"),0)
            if new_rank>old_rank:
                rows=read_jsonl(self.seen_path)
                for row in rows:
                    if row.get("creative_id")==matched.get("creative_id"):
                        row.update({"latest_run_id":run_id,"evidence_class":creative.get("evidence_class"),
                            "paid_evidence_level":(creative.get("paid_evidence") or {}).get("level"),
                            "adapter":(creative.get("provenance") or {}).get("adapter"),"evidence_upgraded_at":now()})
                atomic_write_text(self.seen_path,"".join(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n" for row in rows))
            return False
        append_jsonl(self.seen_path, {
            "creative_id": creative_id,
            "first_seen_at": now(),
            "run_id": run_id,
            "canonical_url": creative.get("canonical_url"),
            "media_sha256": media_hash,
            "visual_fingerprint": visual,
            "visual_signature": signature,
            "adapter":(creative.get("provenance") or {}).get("adapter"),
            "evidence_class":creative.get("evidence_class"),
            "paid_evidence_level":(creative.get("paid_evidence") or {}).get("level"),
        })
        return True

    def cooldowns(self) -> dict[str, str]:
        return read_json(self.cooldowns_path, {}) or {}

    def is_cooled(self, key: str, at: datetime | None = None) -> bool:
        until = self.cooldowns().get(key)
        if not until:
            return False
        return datetime.fromisoformat(until) > (at or datetime.now().astimezone())

    def set_cooldown(self, key: str, until: str) -> None:
        values = self.cooldowns()
        values[key] = until
        atomic_write_json(self.cooldowns_path, values)

    def add_decision(self, event: dict[str, Any]) -> None:
        if event.get("schema_version") != "decision_event/v1":
            raise ValueError("unsupported decision schema")
        append_jsonl(self.decisions_path, event)
        if event.get("cooldown_until"):
            self.set_cooldown(event["experiment_id"], event["cooldown_until"])
            mechanism=self.mechanism_for_experiment(event["experiment_id"])
            if mechanism:self.set_cooldown(self.mechanism_key(mechanism),event["cooldown_until"])
        self.complete_run_for_experiment(event["experiment_id"], event)

    @staticmethod
    def mechanism_key(mechanism:str)->str:
        normalized=normalized_mechanism_key(mechanism)
        return "mechanism:"+stable_id(normalized)[:20]

    def mechanism_for_experiment(self,experiment_id:str)->str:
        for path in self.root.parent.joinpath("runs").glob("*/experiment.json"):
            task=read_json(path,{})
            if task.get("experiment_id")==experiment_id:return str(task.get("borrow_mechanism") or "")
        return ""

    def is_mechanism_suppressed(self,mechanism:str)->bool:
        if not mechanism:return False
        key=self.mechanism_key(mechanism)
        if self.is_cooled(key):return True
        adopted={row.get("experiment_id") for row in read_jsonl(self.decisions_path) if row.get("decision")=="adopt"}
        wanted=normalized_mechanism_key(mechanism)
        return any(normalized_mechanism_key(self.mechanism_for_experiment(experiment_id))==wanted for experiment_id in adopted)

    def add_run(self, summary: dict[str, Any]) -> None:
        append_jsonl(self.run_path, summary)

    def commit_completed_run(self, creative:dict[str,Any],run_id:str,summary:dict[str,Any])->None:
        """Commit seen-index and run-history together, compensating on failure.

        The two public files remain human-readable JSONL.  Snapshot/restore makes
        a failed second write invisible to tomorrow's dedupe instead of leaving a
        half-committed run that the product can no longer surface.
        """
        before={path:(path.read_bytes() if path.exists() else None) for path in (self.seen_path,self.run_path)}
        try:
            self.mark_seen(creative,run_id)
            self.add_run(summary)
        except Exception:
            for path,data in before.items():
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write_text(path,data.decode("utf-8"))
            raise

    def record_patterns(self, clusters: list[dict[str, Any]], run_id: str) -> None:
        """Append cross-day mechanism observations without replacing source evidence."""
        existing={(row.get("run_id"),row.get("cluster_id")) for row in read_jsonl(self.patterns_path)}
        for cluster in clusters:
            key=(run_id,cluster.get("cluster_id"))
            if key in existing: continue
            append_jsonl(self.patterns_path, {
                "schema_version": "pattern_memory/v1",
                "run_id": run_id,
                "observed_at": now(),
                "cluster_id": cluster.get("cluster_id"),
                "mechanism": cluster.get("mechanism") or cluster.get("label"),
                "creative_ids": cluster.get("member_creative_ids") or cluster.get("creative_ids") or cluster.get("evidence_creative_ids") or [],
                "evidence_count": cluster.get("evidence_count") or len(cluster.get("member_creative_ids") or []),
            })
            existing.add(key)

    def suppressed_creative_ids(self) -> set[str]:
        """Resolve adopted and currently cooled decisions to creative IDs before paid collection."""
        decisions={row.get("experiment_id"):row for row in read_jsonl(self.decisions_path) if row.get("experiment_id")}
        result=set()
        for path in self.root.parent.joinpath("runs").glob("*/experiment.json"):
            task=read_json(path,{})
            decision=decisions.get(task.get("experiment_id"))
            if not decision: continue
            permanent=decision.get("decision")=="adopt"
            cooled=self.is_cooled(task.get("experiment_id",""))
            if permanent or cooled:
                result.update(task.get("evidence_creative_ids") or [])
        return result

    def complete_run_for_experiment(self, experiment_id: str, decision: dict[str, Any]) -> None:
        candidates=[]
        for path in self.root.parent.joinpath("runs").glob("*/experiment.json"):
            if read_json(path,{}).get("experiment_id") != experiment_id: continue
            manifest=read_json(path.parent/"run_manifest.json",{})
            if manifest: candidates.append((manifest.get("current_stage")=="WAIT_DECISION",path.parent.name,path.parent))
        for _,_,run_dir in sorted(candidates,reverse=True):
            manifest_path=run_dir/"run_manifest.json"
            manifest=read_json(manifest_path,{})
            if not manifest or manifest.get("current_stage")=="DONE": continue
            event={"schema_version":"run_event/v1","at":now(),"stage":"DONE","detail":{"decision":decision.get("decision"),"event_id":decision.get("event_id")}}
            append_jsonl(run_dir/"events/state_transitions.jsonl",event)
            manifest["current_stage"]="DONE";manifest.setdefault("stage_history",[]).append({"at":event["at"],"stage":"DONE"})
            atomic_write_json(manifest_path,manifest)
            return
