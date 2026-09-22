"""Workbench operations over the course's existing evidence and handoff formats."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {} if default is None else default


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def load_engine(role, name):
    path = ROOT / "engine" / role / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location("workbench_" + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class Workspace:
    def __init__(self, project):
        self.project = Path(project).resolve()
        self.engine = self.project / ".content-flywheel"
        self.engine.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def _inside(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.engine):
            raise ValueError("文件不属于当前工作台")
        return path

    def context(self):
        return read(self.engine / "config/enterprise_context.json")

    def context_revision(self):
        return hashlib.sha256(json.dumps(self.context(), ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    def materials(self):
        rows = []
        for path in sorted((self.engine / "runs").glob("*/experiment.json"), reverse=True):
            task = read(path)
            evidence = read(path.parent / "creative/evidence.json")
            analysis = read(path.parent / "analysis/analysis.json")
            material_id = path.parent.name
            original = evidence.get("canonical_url") or ""
            if not original.startswith(("https://", "http://")):
                original = ""
            review = analysis.get("model_review") or {}
            whitebox = analysis.get("whitebox_analysis") or review.get("whitebox_analysis") or {}
            frames = []
            for shot in (analysis.get("observations") or {}).get("shots", []):
                source = Path(shot.get("path") or "")
                if source.is_file() and source.resolve().is_relative_to(self.engine):
                    frames.append({"path": str(source.relative_to(self.engine)), "time": shot.get("timestamp_sec")})
            rows.append({
                "id": material_id, "creative_id": evidence.get("creative_id"),
                "title": evidence.get("title") or (review.get("content_summary") or {}).get("title") or
                         (analysis.get("interpretations") or {}).get("opening_hook") or "待拆解素材",
                "author": (evidence.get("author") or {}).get("display_name") or "来源未记录",
                "source_url": original, "collected_at": evidence.get("collected_at"),
                "source_kind": evidence.get("evidence_class", "user_supplied_unverified"),
                "organic_metrics": evidence.get("organic_metrics") or evidence.get("metrics") or {},
                "paid_metrics": evidence.get("paid_metrics") or {},
                "estimated_metrics": evidence.get("estimated_metrics") or {},
                "video": str((path.parent / "creative/source.mp4").relative_to(self.engine)) if (path.parent / "creative/source.mp4").is_file() else None,
                "frames": frames, "whitebox": whitebox,
                "interpretations": analysis.get("interpretations") or {},
                "strategy": {k: task.get(k) for k in ("borrow_mechanism", "context_fit_reason", "do_not_copy", "claim_boundaries", "single_variable", "constants", "draft_brief", "target_customer", "customer_situation")},
                "reviewed": bool(whitebox and review.get("schema_version") == "model_review/v2"),
                "adoptable": bool(task.get("adoptable")),
                "hold_reasons": task.get("hold_reasons") or [],
            })
        return rows

    def material(self, material_id):
        for item in self.materials():
            if item["id"] == material_id:
                return item
        raise ValueError("没有找到这条素材，请刷新后重试")

    def productions(self):
        return [read(p) for p in sorted((self.engine / "handoffs").glob("production_run_*.json"))]

    def production(self, task_id):
        for bundle in self.productions():
            if bundle.get("task_id") == task_id:
                return bundle
        raise ValueError("这项内容任务不存在")

    def _bundle_path(self, task_id):
        if not task_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in task_id):
            raise ValueError("任务编号无效")
        return self.engine / "handoffs" / ("production_run_" + task_id + ".json")

    def overview(self):
        shared = read(self.engine / "context/shared_enterprise_context.json")
        sources = []
        for source in shared.get("sources") or []:
            if not isinstance(source, dict):
                continue
            locator = source.get("locator") or ""
            local = (self.project / locator).resolve()
            sources.append({"name": Path(locator).name or "已记录的业务资料", "observed_at": source.get("observed_at"),
                            "available": local.is_relative_to(self.project) and local.is_file()})
        return {"context": self.context(), "context_revision": self.context_revision(),
                "project_key": hashlib.sha256(str(self.project).encode()).hexdigest()[:16],
                "resume_prompt": "请读取并继续这个工作台：" + str(self.project),
                "business_sources": sources,
                "growth": __import__("growth").state(self),
                "materials": self.materials(), "productions": self.productions(),
                "ledger": read(self.engine / "growth/content_ledger.json", {"items": []}),
                "learning": read(self.engine / "growth/workbench_learning.json", {"items": []}),
                "requests": [read(p) for p in sorted((self.engine / "requests").glob("*.json"))],
                "history_sample": (self.project / "来源与复制记录.json").is_file()}

    def set_business(self, body):
        with self.lock:
            old = self.context()
            values = {k: str(body.get(k, "")).strip() for k in ("name", "products", "target_customer", "business_goal", "claim_boundaries")}
            if not all(values[k] for k in ("name", "products", "target_customer", "business_goal")):
                raise ValueError("请说明业务、产品、客户和这一轮目标")
            if old:
                write(self.engine / "history/context" / (uuid.uuid4().hex + ".json"), old)
            current = {**old, "schema_version": "enterprise_context/v2", "context_id": old.get("context_id") or uuid.uuid4().hex,
                       **values, "products": values["products"].splitlines(), "claim_boundaries": values["claim_boundaries"].splitlines(),
                       "updated_at": now(), "source": "owner-workbench-correction"}
            write(self.engine / "config/enterprise_context.json", current)
            for path in (self.engine / "requests").glob("*.json"):
                previous = read(path)
                if previous.get("status") == "queued":
                    previous.update({"status": "needs_review", "reason": "业务理解已更新，需按新背景重新接续"})
                    write(path, previous)
            # New business understanding must not silently adopt old judgments.
            request = self.request("context_review", "按更新后的业务重新核对素材适配与搜索方向")
            return {"saved": True, "request": request}

    def request(self, kind, message, material_id=None, task_id=None):
        if not isinstance(message, str) or not message.strip():
            raise ValueError("请说一句要改什么")
        if material_id:
            self.material(material_id)
        if task_id:
            self.production(task_id)
        request = {"id": uuid.uuid4().hex, "kind": kind, "message": str(message).strip(),
                   "material_id": material_id, "task_id": task_id, "status": "queued",
                   "created_at": now(), "context_revision": self.context_revision()}
        write(self.engine / "requests" / (request["id"] + ".json"), request)
        return request

    def start_content(self, material_id):
        with self.lock:
            material = self.material(material_id)
            if not material["reviewed"] or not material["adoptable"]:
                raise ValueError("这条素材的适配判断还没通过，请先让 AI 完成拆解或校正")
            context = self.context()
            if not context:
                raise ValueError("先说明你的业务，再决定怎样使用这条素材")
            pending = [read(p) for p in (self.engine / "requests").glob("*.json")]
            if any(r.get("kind") == "context_review" and r.get("status") == "queued" for r in pending):
                raise ValueError("业务刚更新，先让 AI 重新核对适配，旧推荐不能直接沿用")
            for bundle in self.productions():
                if bundle.get("workbench_source") == material_id and bundle.get("context_revision") == self.context_revision():
                    return bundle
            task = read(self.engine / "runs" / material_id / "experiment.json")
            shared = read(self.engine / "context/shared_enterprise_context.json")
            if not shared:
                raise ValueError("企业资料还没整理好，请让 AI 先完成企业理解")
            task_id = "content-" + uuid.uuid4().hex[:16]
            direction = {"task_id": task_id, "touch_destination": {"channel": "douyin", "position": "短视频", "owner": "用户"},
                         "desired_action": context.get("business_goal"), "belief_change": task.get("hypothesis")}
            strategy = load_engine("operate-content-strategy-lead", "export_production_handoff").export_handoff(task, shared, direction)
            bundle = load_engine("operate-content-production-lead", "init_production_run").initialize(strategy)
            bundle.update({"workbench_source": material_id, "context_revision": self.context_revision(), "workbench_versions": []})
            write(self.engine / "handoffs" / ("strategy_to_production_" + task_id + ".json"), strategy)
            write(self._bundle_path(task_id), bundle)
            event = {"schema_version": "decision_event/v1", "event_id": task_id,
                     "experiment_id": task["experiment_id"], "decision": "adopt", "reason": None,
                     "decided_by": "workbench_operator", "decided_at": now(), "cooldown_until": None}
            decision_path = self.engine / "memory/decisions.jsonl"
            decision_path.parent.mkdir(parents=True, exist_ok=True)
            with decision_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            self.request("production", "根据已选素材的可借用机制和企业事实，产出本企业第一版脚本；不要照抄原片", material_id, task_id)
            return bundle

    def save_version(self, body):
        with self.lock:
            bundle = self.production(body.get("task_id"))
            if bundle.get("context_revision") != self.context_revision():
                raise ValueError("这项任务属于更新前的业务。请先重新核对方向，再从素材建立当前业务任务；你的输入仍保留在页面")
            raw_text = body.get("text")
            text = raw_text.strip() if isinstance(raw_text, str) else ""
            if not text:
                raise ValueError("内容不能为空")
            versions = bundle.setdefault("workbench_versions", [])
            latest = versions[-1]["version_id"] if versions else None
            if body.get("base_version") != latest:
                raise ValueError("已有更新的版本，请刷新后再保存；你的输入仍保留在页面")
            version = {"version_id": "v" + str(len(versions) + 1), "text": text,
                       "created_at": now(), "author": "user", "adopted": False,
                       "context_revision": self.context_revision()}
            versions.append(version)
            bundle["status"] = "AWAITING_REVIEW"
            artifact_path = self.engine / "artifacts" / bundle["task_id"] / (version["version_id"] + ".md")
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(text + "\n", encoding="utf-8")
            version["locator"] = str(artifact_path)
            candidate_id = bundle["task_id"] + "-" + version["version_id"]
            bundle.setdefault("script_candidates", []).append({"candidate_id": candidate_id, "format": "short_video_script",
                 "body": text, "output_path": str(artifact_path), "strategy_trace": dict(bundle["locked_strategy"])})
            bundle["selected_script"] = candidate_id
            bundle["current_artifact"] = {"artifact_id": bundle["task_id"], "version_id": version["version_id"], "type": "script",
                 "locator": str(artifact_path), "path": str(artifact_path), "source_refs": bundle["locked_strategy"].get("material_refs") or [],
                 "channel_variants": [{**bundle["locked_strategy"].get("touch_destination", {}), "locator": str(artifact_path)}]}
            write(self._bundle_path(bundle["task_id"]), bundle)
            return bundle

    def adopt_version(self, body):
        with self.lock:
            bundle = self.production(body.get("task_id"))
            versions = bundle.get("workbench_versions") or []
            if not versions or versions[-1]["version_id"] != body.get("version_id"):
                raise ValueError("请选择当前内容版本")
            if versions[-1].get("context_revision") != self.context_revision():
                raise ValueError("业务已经变化，请重新核对内容后保存新版本")
            versions[-1]["adopted"] = True
            bundle["status"] = "READY_FOR_TOUCH"
            bundle["adopted_artifact"] = dict(bundle["current_artifact"])
            handoff = load_engine("operate-content-production-lead", "export_growth_handoff").export(bundle)
            write(self.engine / "handoffs" / ("production_to_growth_" + bundle["task_id"] + "_" + body["version_id"] + ".json"), handoff)
            write(self._bundle_path(bundle["task_id"]), bundle)
            return bundle

    def record_result(self, body):
        with self.lock:
            bundle = self.production(body.get("task_id"))
            version = next((v for v in bundle.get("workbench_versions", []) if v["version_id"] == body.get("version_id")), None)
            if not version or not version.get("adopted"):
                raise ValueError("请先采用实际使用的内容版本")
            if not body.get("source") or not body.get("observed_at"):
                raise ValueError("请填写数据来源和观察日期")
            metrics = {}
            for key in ("spend", "impressions", "clicks", "conversions", "revenue"):
                raw = body.get(key)
                if raw in (None, ""):
                    metrics[key] = None
                else:
                    value = float(raw)
                    if value < 0 or not value < float("inf"):
                        raise ValueError("数据需为非负数，未知请留空")
                    metrics[key] = value
            row = {"channel": (bundle.get("locked_strategy", {}).get("touch_destination") or {}).get("channel") or "unknown",
                   "published_at": body.get("published_at"), "content_id": bundle["task_id"] + ":" + version["version_id"],
                   "title": version["text"].splitlines()[0][:80], "artifact_id": bundle["task_id"], "version_id": version["version_id"],
                   "production_ref": bundle["task_id"], "source_refs": [str(body["source"])], "observed_at": body["observed_at"],
                   "data_through": body.get("data_through") or body["observed_at"], "internal_metrics": metrics,
                   "business_results": {"note": str(body.get("note") or "")},
                   "missing_fields": [k for k, v in metrics.items() if v is None]}
            path = self.engine / "growth/content_ledger.json"
            ledger = load_engine("operate-content-growth-lead", "update_content_ledger").update(read(path), {"items": [row]})
            write(path, ledger)
            bundle["status"] = "RESULT_RECORDED"
            write(self._bundle_path(bundle["task_id"]), bundle)
            return ledger

    def learn(self, body):
        # Compatibility for old pages: user remarks are input to AI review, never a finished diagnosis.
        bundle = self.production(body.get("task_id"))
        version = body.get("version_id")
        message = "用户对 " + bundle["task_id"] + ":" + str(version) + " 的反馈：" + str(body.get("observation") or "")
        if body.get("hypothesis"):
            message += "；用户认为可能原因：" + str(body["hypothesis"])
        if body.get("next_action"):
            message += "；用户希望：" + str(body["next_action"])
        return __import__("growth").request_review(self, message)
