#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError,URLError
from datetime import datetime, timedelta
from pathlib import Path

from common import atomic_write_json, read_json, stable_id
from memory_store import MemoryStore
from import_decisions import import_events
from clustering import cluster_tasks,cluster_analyses,mechanism_key
from dummy_future_consumer import consume
from strategy_engine import score_candidate
from ingest_feedback import ingest as ingest_feedback,ingest_result
from younavi_transcribe import parse_text
from cost_ledger import CostLedger
from sanitize_workspace import sanitize
from video_extract import extract_fixed_frames, extract_strategy_frames, probe, visual_fingerprint,visual_signature,signature_distance
from validate_contract import validate as validate_contract
from validate_contract import validate_draft202012
from validate_contract import REQUIRED as CONTRACT_REQUIRED
from run_pipeline import _failure_stage
from watch_discovery import update_from_candidates
from discover_douplus import normalize_rows as normalize_douplus_rows
from daily_run import _score as daily_candidate_score,_shortlist_snapshot
from apply_model_review import validate_whitebox
from render_dashboard import plain_topic,whitebox_html,single_variable_copy,team_task_card_html
from gemini_video import parse_response as parse_gemini_response
import tikhub_adapter
import run_today
from export_production_handoff import export_handoff
from scan_enterprise_materials import scan
from build_enterprise_whitepaper import build as build_whitepaper


class CoreTests(unittest.TestCase):
    def test_enterprise_materials_create_versioned_source_bound_context(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/"brief.md").write_text("我们卖午餐冒菜，服务三公里顾客。",encoding="utf-8")
            inventory=scan(root);source_id=inventory["items"][0]["source_id"]
            claims={"company":"夹具门店","people":[{"segment":"午餐顾客","description":"三公里内"}],"offerings":[{"name":"冒菜","description":"午餐"}],"scenes":[{"stage":"午饭前","description":"刷抖音"}],"knowledge":[{"item_id":"k1","kind":"fact","statement":"主营午餐冒菜","status":"observed","source_refs":[source_id]}],"boundaries":[]}
            first=build_whitepaper(inventory,claims);second=build_whitepaper(inventory,claims,first)
            self.assertEqual(2,second["version"]);self.assertEqual(first["context_id"],second["supersedes"])

    def test_confirmed_strategy_exports_without_changing_single_variable(self):
        experiment={"experiment_id":"e1","single_variable":{"name":"opening_hook","from":"先讲品牌","to":"先亮真实出餐"},"constants":["产品","受众"],"claim_boundaries":["不虚构销量"],"evidence_creative_ids":["c1"],"production_handoff":{"claim_checks":[{"what_we_can_confirm":"画面可见真实出餐"}]}}
        context={"schema_version":"shared_enterprise_context/v1","context_id":"ctx-1"}
        confirmation={"owner_confirmed":True,"target_audience":"午餐顾客","customer_scene":"午饭前刷抖音","belief_change":"相信实物可见","desired_action":"查看门店","touch_destination":{"channel":"douyin","position":"草稿","owner":"运营"}}
        whitepaper_confirmation={"owner_confirmed":True,"context_id":"ctx-1"}
        result=export_handoff(experiment,context,confirmation)
        self.assertEqual("ready_for_production",result["status"])
        self.assertEqual(experiment["single_variable"],result["single_variable"])

    def test_automatically_active_whitepaper_can_flow_without_owner_confirmation(self):
        experiment={"experiment_id":"e1","single_variable":{"name":"opening_hook","from":"旧开场","to":"新开场"},"claim_boundaries":["不虚构销量"],"production_handoff":{}}
        context={"schema_version":"shared_enterprise_context/v1","context_id":"ctx-auto"}
        whitepaper={"active_for_use":True,"activation_mode":"automatic_with_correction","context_id":"ctx-auto"}
        direction={"owner_confirmed":True,"target_audience":"顾客","customer_scene":"饭点","belief_change":"相信值得试","desired_action":"到店"}
        self.assertEqual("ready_for_production",export_handoff(experiment,context,direction)["status"])

    def test_incomplete_direction_stops_only_for_missing_work(self):
        with self.assertRaisesRegex(ValueError,"单变量"):
            export_handoff({}, {"schema_version":"shared_enterprise_context/v1","context_id":"ctx"}, {})

    def test_whitepaper_needs_no_separate_confirmation_record(self):
        experiment={"experiment_id":"e1","single_variable":{"name":"开头","from":"旧","to":"新"},"production_handoff":{}}
        result=export_handoff(experiment,{"schema_version":"shared_enterprise_context/v1","context_id":"ctx-new"},{})
        self.assertEqual("ctx-new",result["context_id"])

    def test_daily_natural_language_entry_remembers_workspace_and_routes_optional_feigua(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);workspace=root/"company";(workspace/"config").mkdir(parents=True);(workspace/"runs").mkdir()
            atomic_write_json(workspace/"config/enterprise_context.json",{"name":"企业"})
            active=root/"active.json";atomic_write_json(active,{"workspace":str(workspace)})
            with patch.object(run_today,"ACTIVE",active):
                self.assertEqual(run_today.active_workspace(),workspace.resolve())
            public=root/"public.json";atomic_write_json(public,{"candidates":[{"creative_id":"public:1","title":"公开素材"}],"errors":[]})
            paid={"creative_id":"paid:2","title":"飞瓜素材"}
            with patch.object(run_today,"discover",return_value=public),patch.object(run_today,"feigua_candidates",return_value=[paid]):
                batch,route=run_today.combined_batch(workspace)
            payload=read_json(batch,{})
            self.assertEqual(route,"TikHub+飞瓜")
            self.assertEqual({row["creative_id"] for row in payload["candidates"]},{"public:1","paid:2"})

    def test_daily_shortlist_is_small_explainable_and_business_bound(self):
        candidates=[{"creative_id":str(i),"title":f"冒菜团购套餐{i}","platform":"douyin","search_metrics":{"likes":i}} for i in range(12)]
        rows=_shortlist_snapshot(candidates,{"products":["冒菜"]},{"keywords":["冒菜 团购"]})
        self.assertEqual(len(rows),8)
        self.assertEqual(rows[0]["rank"],1)
        self.assertIn("业务词",rows[0]["reason"])
        self.assertNotIn("score",json.dumps(rows,ensure_ascii=False).lower())

    def test_adopted_direction_becomes_copyable_team_experiment_card(self):
        task={"single_variable":{"name":"opening_hook","to":"结果前置"},"constants":["产品","受众"],"claim_boundaries":["不虚构销量"],"production_handoff":{"goal":"只验证前三秒","shots":[{"time":"0–3秒","visual":"端上招牌锅","text":"真实价格","job":"停住顾客"}],"owner_questions":["真实价格是什么？"]}}
        self.assertEqual(team_task_card_html(task,{},False),"")
        card=team_task_card_html(task,{},True)
        self.assertIn("可直接发给团队的今日实验卡",card)
        self.assertIn("端上招牌锅",card)
        self.assertIn("真实价格是什么",card)
        self.assertIn("不会替你自动生成或发布视频",card)

    def test_frontstage_single_variable_is_one_shootable_opening_change(self):
        task={"single_variable":{"name":"opening_hook","to":"食欲—价格—套餐—门店"},"production_handoff":{"shots":[{"visual":"自有菜品脱骨特写。","text":"先说菜品结果，不讲品牌。"}]}}
        copy=single_variable_copy(task)
        self.assertEqual(copy,"前3秒：自有菜品脱骨特写；先说菜品结果，不讲品牌")
        self.assertNotIn("→",copy)

    def test_recommended_topic_is_a_clean_title_not_a_question_fragment(self):
        task={"production_handoff":{"owner_questions":["你愿意做一条'很多企业的 AI 落地注定失败'的反常识开口版吗？证据用课堂实拍。"]}}
        self.assertEqual("很多企业的 AI 落地注定失败",plain_topic(task))

    def test_static_dashboard_never_claims_a_decision_was_saved(self):
        source=(Path(__file__).parent/"render_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("location.protocol==='file:'",source)
        self.assertIn("这是静态预览，不能保存选择",source)
        self.assertIn("location.pathname.includes('/static-html/')",source)
        self.assertIn("if(!await remember(event))return",source)

    def test_frontstage_doctrine_cannot_regress_to_backstage_language(self):
        renderer=(Path(__file__).parent/"render_dashboard.py").read_text(encoding="utf-8")
        standard=(Path(__file__).parents[2]/"engineering/前台产品验收标准_V1.md").read_text(encoding="utf-8")
        self.assertIn("用户只提供业务事实",standard)
        self.assertIn("新功能先留在后台",standard)
        self.assertNotIn("已复核机制",renderer)
        self.assertNotIn("先看机制",renderer)

    def test_tikhub_http_failures_use_real_adapter_policy(self):
        def failure(code):return HTTPError("https://api.tikhub.io/test",code,"test",None,None)
        with patch.dict("os.environ",{"TIKHUB_API_TOKEN":"test-only"}),patch.object(tikhub_adapter,"urlopen",side_effect=failure(401)):
            with self.assertRaises(tikhub_adapter.ConnectorError) as caught:tikhub_adapter.request("/test")
            self.assertEqual(caught.exception.code,"authorization")
        with patch.dict("os.environ",{"TIKHUB_API_TOKEN":"test-only"}),patch.object(tikhub_adapter,"urlopen",side_effect=failure(402)):
            with self.assertRaises(tikhub_adapter.ConnectorError) as caught:tikhub_adapter.request("/test")
            self.assertEqual(caught.exception.code,"insufficient_balance")
        with patch.dict("os.environ",{"TIKHUB_API_TOKEN":"test-only"}),patch.object(tikhub_adapter,"urlopen",side_effect=failure(429)) as mocked,patch.object(tikhub_adapter.time,"sleep"):
            with self.assertRaises(tikhub_adapter.ConnectorError) as caught:tikhub_adapter.request("/test")
            self.assertEqual(caught.exception.code,"transient_exhausted");self.assertEqual(mocked.call_count,3)

    def test_tikhub_detail_falls_back_from_share_url_to_id_route(self):
        detail={"aweme_id":"7672217396196138874","desc":"素材","statistics":{},"author":{},"video":{"play_addr":{"url_list":["https://media.example/video.mp4"]}}}
        def fake(path,params=None,method="GET",body=None):
            if path.endswith("by_share_url"):raise tikhub_adapter.ConnectorError("http_error","HTTP 400")
            if path.endswith("fetch_one_video_v2"):return {"data":{"aweme_detail":detail}}
            raise AssertionError(path)
        with patch.object(tikhub_adapter,"request",side_effect=fake):
            evidence,raw=tikhub_adapter.detail_by_url("https://www.douyin.com/video/7672217396196138874")
        self.assertEqual(evidence["provenance"]["detail_route"],"web_v2")
        self.assertIn("share_url:http_error",evidence["provenance"]["failed_routes"])
        self.assertEqual(tikhub_adapter.media_urls(raw),["https://media.example/video.mp4"])

    def test_tikhub_dead_local_proxy_falls_back_to_direct_connection(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*_):return False
            def read(self):return b'{"data":{"ok":true}}'
        class Direct:
            def open(self,*_,**__):return Response()
        refused=URLError(ConnectionRefusedError(61,"proxy refused"))
        with patch.dict("os.environ",{"TIKHUB_API_TOKEN":"test-only"}),patch.object(tikhub_adapter,"urlopen",side_effect=refused),patch.object(tikhub_adapter,"build_opener",return_value=Direct()):
            self.assertTrue(tikhub_adapter.request("/test")["data"]["ok"])

    def test_native_video_response_parser_rejects_missing_invalid_and_wrong_schema(self):
        with self.assertRaisesRegex(RuntimeError,"缺少可用内容"):parse_gemini_response({})
        with self.assertRaisesRegex(RuntimeError,"合法 JSON"):parse_gemini_response({"candidates":[{"content":{"parts":[{"text":"not-json"}]}}]})
        with self.assertRaisesRegex(RuntimeError,"不支持的 schema"):parse_gemini_response({"candidates":[{"content":{"parts":[{"text":json.dumps({"schema_version":"other/v1"})}]}}]})
        valid={"schema_version":"creative_analysis/v1","observations":{},"interpretations":{},"confidence":{},"evidence_refs":[],"degradations":[]}
        self.assertEqual(parse_gemini_response({"candidates":[{"content":{"parts":[{"text":json.dumps(valid)}]}}]}),valid)

    def test_machine_schema_bundle_covers_every_runtime_contract(self):
        schema=read_json(Path(__file__).parent.parent/"schemas/phase1-contracts.schema.json",{})
        declared={str(value.get("properties",{}).get("schema_version",{}).get("const")) for value in schema.get("$defs",{}).values()}
        self.assertTrue(set(CONTRACT_REQUIRED)<=declared,sorted(set(CONTRACT_REQUIRED)-declared))

    def test_atomic_json_and_stable_id(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "a.json"
            atomic_write_json(path, {"中文": 1})
            self.assertEqual(read_json(path)["中文"], 1)
            self.assertEqual(stable_id("a", 1), stable_id("a", 1))

    def test_memory_seen_and_cooldown(self):
        with tempfile.TemporaryDirectory() as temp:
            store = MemoryStore(Path(temp))
            evidence = {"creative_id": "douyin:1", "canonical_url": "https://example/1", "media": {"sha256": "abc"}}
            self.assertTrue(store.mark_seen(evidence, "run-1"))
            self.assertFalse(store.mark_seen(evidence, "run-2"))
            same_media = {"creative_id": "other:2", "canonical_url": "https://example/2", "media": {"sha256": "abc"}}
            self.assertFalse(store.mark_seen(same_media, "run-3"))
            upgraded={**evidence,"evidence_class":"third_party_ad_library","paid_evidence":{"level":"strong_signal"},"provenance":{"adapter":"feigua_yitou_export"}}
            self.assertFalse(store.mark_seen(upgraded,"run-upgrade"))
            self.assertEqual(store.seen_index()["douyin:1"]["evidence_class"],"third_party_ad_library")
            self.assertEqual(store.seen_index()["douyin:1"]["latest_run_id"],"run-upgrade")
            until = (datetime.now().astimezone() + timedelta(days=1)).isoformat()
            store.set_cooldown("experiment-1", until)
            self.assertTrue(store.is_cooled("experiment-1"))

    def test_mechanism_memory_suppresses_same_direction_across_creatives(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run=root/"runs/r1";run.mkdir(parents=True)
            atomic_write_json(run/"experiment.json",{"experiment_id":"e1","borrow_mechanism":"结果前置—过程证明"})
            store=MemoryStore(root);store.add_decision({"schema_version":"decision_event/v1","event_id":"d1","experiment_id":"e1","decision":"adopt","decided_at":datetime.now().astimezone().isoformat()})
            self.assertTrue(store.is_mechanism_suppressed("结果前置—过程证明"))
            self.assertTrue(store.is_mechanism_suppressed("先亮出成果，再用步骤佐证"))
            self.assertFalse(store.is_mechanism_suppressed("问题开场"))

    def test_chinese_mechanism_synonyms_normalize_without_collapsing_concepts(self):
        self.assertEqual(mechanism_key("结果前置—过程证明"),mechanism_key("先亮出成果，再用步骤佐证"))
        self.assertEqual(mechanism_key("痛点开头"),mechanism_key("问题开场"))
        self.assertNotEqual(mechanism_key("问题开场"),mechanism_key("结果开场"))
        self.assertNotEqual(mechanism_key("反差对比"),mechanism_key("过程证明"))

    def test_video_fixed_frame_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "fixture.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                "-i", "testsrc=size=360x640:rate=12", "-t", "3", "-pix_fmt", "yuv420p", str(video)
            ], check=True, timeout=60)
            metadata = probe(video)
            frames = extract_fixed_frames(video, root / "frames", interval_sec=1, max_frames=4)
            self.assertEqual(metadata["width"], 360)
            self.assertEqual(metadata["height"], 640)
            self.assertGreaterEqual(len(frames), 3)
            self.assertTrue(all(Path(row["path"]).is_file() for row in frames))

    def test_ad_sampler_keeps_opening_and_ending(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); video = root / "ad.mp4"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                "testsrc=size=360x640:rate=15:duration=5", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
            frames = extract_strategy_frames(video, root / "strategy")
            times = [row["timestamp_sec"] for row in frames]
            self.assertIn(0, times)
            self.assertTrue(any(0 < value <= 1 for value in times))
            self.assertTrue(any(value >= 4 for value in times))

    def test_visual_fingerprint_survives_reencode(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/"a.mp4";b=root/"b.mp4"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","testsrc=size=360x640:rate=15:duration=3","-c:v","libx264","-crf","18","-pix_fmt","yuv420p",str(a)],check=True)
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",str(a),"-c:v","libx264","-crf","32",str(b)],check=True)
            self.assertEqual(visual_fingerprint(a),visual_fingerprint(b))

    def test_near_duplicate_signature_handles_added_caption_band(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=root/"original.mp4";captioned=root/"captioned.mp4";different=root/"different.mp4"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","testsrc=size=360x640:rate=15:duration=3","-c:v","libx264","-pix_fmt","yuv420p",str(original)],check=True)
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",str(original),"-vf","drawbox=x=0:y=0:w=iw:h=50:color=black:t=fill","-c:v","libx264","-crf","28",str(captioned)],check=True)
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=red:size=360x640:rate=15:duration=3","-c:v","libx264","-pix_fmt","yuv420p",str(different)],check=True)
            near=signature_distance(visual_signature(original),visual_signature(captioned));far=signature_distance(visual_signature(original),visual_signature(different))
            self.assertLessEqual(near,.08);self.assertGreater(far,.08)

    def test_near_duplicate_signature_handles_both_bands_and_mild_speed_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=root/"original.mp4";edited=root/"edited.mp4";different=root/"different.mp4"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","testsrc2=size=360x640:rate=24:duration=6","-c:v","libx264","-pix_fmt","yuv420p",str(original)],check=True)
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",str(original),"-vf","setpts=0.95*PTS,drawbox=x=0:y=0:w=iw:h=70:color=black:t=fill,drawbox=x=0:y=ih-90:w=iw:h=90:color=white:t=fill","-an","-c:v","libx264","-crf","30",str(edited)],check=True)
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","smptebars=size=360x640:rate=24:duration=6","-c:v","libx264","-pix_fmt","yuv420p",str(different)],check=True)
            near=signature_distance(visual_signature(original),visual_signature(edited));far=signature_distance(visual_signature(original),visual_signature(different))
            self.assertLessEqual(near,.08,f"near={near}");self.assertGreater(far,.08,f"far={far}")
            store=MemoryStore(root/"workspace")
            self.assertTrue(store.mark_seen({"creative_id":"source:1","media":{"visual_signature":visual_signature(original)}},"r1"))
            self.assertFalse(store.mark_seen({"creative_id":"repost:2","media":{"visual_signature":visual_signature(edited)}},"r2"))
            self.assertTrue(store.mark_seen({"creative_id":"other:3","media":{"visual_signature":visual_signature(different)}},"r3"))

    def test_decision_import_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"decisions.json"
            event={"schema_version":"decision_event/v1","event_id":"e1","experiment_id":"x1",
                "decision":"hold","reason":"需要复核","decided_by":"human",
                "decided_at":datetime.now().astimezone().isoformat(),"cooldown_until":None}
            source.write_text(json.dumps([event],ensure_ascii=False),encoding="utf-8")
            self.assertEqual(import_events(root,source),1)
            self.assertEqual(import_events(root,source),0)
            self.assertEqual(len(MemoryStore(root).decisions_path.read_text().splitlines()),1)

    def test_decision_batch_rejects_atomically(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"decisions.json"
            valid={"schema_version":"decision_event/v1","event_id":"e1","experiment_id":"x1","decision":"hold","reason":"r","decided_by":"human","decided_at":datetime.now().astimezone().isoformat(),"cooldown_until":None}
            source.write_text(json.dumps([valid,{"schema_version":"decision_event/v1"}]),encoding="utf-8")
            with self.assertRaises(ValueError):import_events(root,source)
            self.assertFalse(MemoryStore(root).decisions_path.exists())

    def test_mechanism_cluster_and_future_contract(self):
        tasks=[{"schema_version":"experiment_task/v1","experiment_id":"x1","enterprise_context_id":"c1","target_customer":"老板",
            "hypothesis":"h","evidence_creative_ids":["v1"],"borrow_mechanism":"问题开场","single_variable":{},"constants":[],"claim_boundaries":[],"scorecard":{"evidence_strength":.8}},
            {"schema_version":"experiment_task/v1","experiment_id":"x2","enterprise_context_id":"c1","target_customer":"老板",
            "hypothesis":"h2","evidence_creative_ids":["v2"],"borrow_mechanism":"问题 开场","single_variable":{},"constants":[],"claim_boundaries":[],"scorecard":{"evidence_strength":.6}}]
        clusters=cluster_tasks(tasks);self.assertEqual(len(clusters),1);self.assertEqual(len(clusters[0]["member_creative_ids"]),2)
        self.assertEqual(cluster_tasks([{**tasks[0],"adoptable":False}]),[])
        analyses=[{"creative_id":"v1","interpretations":{"narrative_structure":["问题—证据—行动"]},"model_review":{"decision":"hold"}}, {"creative_id":"v2","interpretations":{"narrative_structure":["问题 证据 行动"]},"model_review":{"decision":"adopt"}}]
        mechanisms=cluster_analyses(analyses);self.assertEqual(len(mechanisms),1);self.assertEqual(len(mechanisms[0]["member_creative_ids"]),2)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"card.json";path.write_text(json.dumps(tasks[0]),encoding="utf-8")
            self.assertEqual(consume(path)["status"],"ACK")

    def test_context_changes_judgment_not_evidence(self):
        evidence={"creative_id":"v1","metrics":{},"paid_evidence":{"level":"weak_signal"}}
        analysis={"interpretations":{"target_situation":"到店吃饭团购套餐","customer_tension":"附近不知道吃什么","action_answer":"到店核销"}}
        local=score_candidate(evidence,analysis,{"target_customer":"三公里到店顾客","business_goal":"团购到店核销","products":["门店套餐"]})
        education=score_candidate(evidence,analysis,{"target_customer":"企业管理者","business_goal":"课程报名学习","products":["培训课程"]})
        self.assertGreater(local["context_fit"],education["context_fit"])
        self.assertEqual(evidence["creative_id"],"v1")

    def test_verified_paid_evidence_uses_highest_weight(self):
        score=score_candidate({"creative_id":"paid:1","metrics":{},"paid_evidence":{"level":"verified_paid"}},{"interpretations":{}},{})
        self.assertEqual(score["evidence_strength"],1.0)
        self.assertIsNone(score["warning"])

    def test_future_feedback_is_archived_without_mutating_decisions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);event={"schema_version":"feedback_event/v1","feedback_id":"f1","experiment_id":"x1","event_type":"metric_snapshot","occurred_at":datetime.now().astimezone().isoformat(),"source":"dummy","metrics":{"ctr":.1},"human_notes":""}
            ingest_feedback(root,event)
            self.assertTrue((root/"memory/future_feedback.jsonl").exists())
            self.assertFalse(MemoryStore(root).decisions_path.exists())
            result={"schema_version":"performance_result/v1","result_id":"r1","experiment_id":"x1","observed_at":datetime.now().astimezone().isoformat(),"source":"future","metrics":{"ctr":.1},"measurement_window":{"start":"a","end":"b"}}
            ingest_result(root,result);ingest_result(root,result)
            self.assertEqual(len((root/"memory/future_performance_results.jsonl").read_text().splitlines()),1)

    def test_younavi_timestamp_parser(self):
        rows=parse_text("[00:00 - 00:02] Speaker_1: 开场\n[01:03 - 01:08] Speaker_2: 行动")
        self.assertEqual([(r["start"],r["end"],r["speaker"]) for r in rows],[(0,2,"Speaker_1"),(63,68,"Speaker_2")])

    def test_cost_ledger_records_without_a_fixed_small_budget_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger=CostLedger(Path(temp));ledger.guard("detail",1,.001,.01);ledger.record("detail",.001,"x")
            ledger.guard("detail",1,.001,.01);self.assertEqual(1,ledger.count("detail"))

    def test_signed_media_url_is_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/"seen.jsonl";p.write_text(json.dumps({"canonical_url":"https://cdn.example/video.mp4?token=secret&expire=1"})+"\n",encoding="utf-8")
            self.assertEqual(sanitize(root),1);text=p.read_text();self.assertNotIn("token=",text);self.assertIn("redacted_hash",text)

    def test_machine_contract_validator(self):
        schema=json.loads((Path(__file__).parent.parent/"schemas/phase1-contracts.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"],"https://json-schema.org/draft/2020-12/schema")
        self.assertIn("performance_result_v1",schema["$defs"])
        valid={"schema_version":"decision_event/v1","event_id":"e1","experiment_id":"x1","decision":"hold","decided_by":"human","decided_at":datetime.now().astimezone().isoformat()}
        self.assertEqual(validate_contract(valid),[])
        self.assertIn("enum:decision",validate_contract({**valid,"decision":"maybe"}))
        evidence={"schema_version":"creative_evidence/v1","creative_id":"x","platform":"douyin","media":{},"evidence_class":"public_content_only","paid_evidence":{},"organic_metrics":{},"paid_metrics":{"spend":1},"estimated_metrics":{"spend":"1-2"}}
        self.assertTrue(any(error.startswith("metric_partition_overlap") for error in validate_contract(evidence)))

    def test_failure_state_classification(self):
        self.assertEqual(_failure_stage(RuntimeError("HTTP 402 余额不足")),"BLOCKED_COST")
        self.assertEqual(_failure_stage(RuntimeError("HTTP 401 invalid token")),"BLOCKED_CREDENTIAL")
        self.assertEqual(_failure_stage(RuntimeError("HTTP 429 timeout")),"FAILED_RETRYABLE")

    def test_counterpart_account_discovery_is_evidence_gated(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/"config").mkdir();atomic_write_json(root/"config/watch_universe.json",{"schema_version":"watch_universe/v1","seed_accounts":[],"keywords":["冒菜"],"excluded_accounts":["排除号"]})
            rows=[{"creative_id":"d:1","author_name":"连锁品牌A","query_keyword":"冒菜","matched_keywords":["冒菜"],"search_metrics":{"likes":"1200"},"search_flags":{}},
                {"creative_id":"d:2","author_name":"连锁品牌A","query_keyword":"团购","matched_keywords":["团购"],"search_metrics":{"likes":"300"},"search_flags":{"high_like_rate":True}},
                {"creative_id":"d:3","author_name":"单条账号","query_keyword":"冒菜","matched_keywords":["冒菜"],"search_metrics":{"likes":"20"},"search_flags":{}},
                {"creative_id":"d:4","author_name":"排除号","query_keyword":"冒菜","matched_keywords":["冒菜"],"search_metrics":{},"search_flags":{"high_like_rate":True,"high_completion":True}}]
            watch=update_from_candidates(root,rows)
            self.assertIn("连锁品牌A",watch["seed_accounts"])
            self.assertNotIn("单条账号",watch["seed_accounts"])
            self.assertNotIn("排除号",[row["account_name"] for row in watch["suggested_accounts"]])

    def test_douplus_ranking_normalization_keeps_truth_boundary(self):
        rows=[{"itemId":"1234567890123456789","title":"冲刺班前三秒","createTime":"2026-08-10","statistics":{"ViewCnt":10000,"LikeCnt":500,"ShareCnt":"0","FinishPlayRate":.32,"IndexCnt":88},"author":{"nickname":"示例账号"}}]
        candidate=normalize_douplus_rows(rows,"education",5)[0]
        self.assertEqual(candidate["evidence_class"],"commercial_like_proxy")
        self.assertEqual(candidate["paid_evidence"]["level"],"strong_signal")
        self.assertEqual(candidate["paid_metrics"],{})
        self.assertEqual(candidate["estimated_metrics"]["heat_index"],88)
        self.assertIsNone(candidate["estimated_metrics"]["shares"])
        self.assertIn("不证明",candidate["evidence_note"])
        commercial={**candidate,"title":"全国门店新品套餐限时上市","category":"food"}
        meme={**candidate,"title":"如何判断朋友是不是烤肠","category":"food"}
        context={"industry":"local_life","products":["门店团购套餐"]};watch={"keywords":["门店 团购"]}
        self.assertGreater(daily_candidate_score(commercial,context,watch),daily_candidate_score(meme,context,watch))

    def test_whitebox_is_detailed_plain_language_and_evidence_linked(self):
        whitebox={
            "one_sentence_logic":"先展示结果，再解释过程，最后给行动。",
            "timeline":[
                {"time":"0-3秒","stage":"让人停下","visual":"结果近景","spoken_message":"提出问题","how_they_work_together":"画面先给答案，口播留下问题","why_it_matters":"降低理解成本","evidence":["0秒画面","0-3秒口播"]},
                {"time":"3-8秒","stage":"继续看","visual":"过程动作","spoken_message":"解释步骤","how_they_work_together":"画面展示，口播解释","why_it_matters":"建立理解","evidence":["3-8秒"]},
                {"time":"8-12秒","stage":"行动","visual":"入口画面","spoken_message":"点击商品卡","how_they_work_together":"行动和入口同时出现","why_it_matters":"完成路径","evidence":["8-12秒"]},
            ],
            "persuasion_chain":[{"question":"为什么停下？","answer":"先见结果","evidence":"0-3秒"}],
            "claims_to_check":[{"source_says":"有效","what_we_can_confirm":"只能确认来源说过","needed_before_use":"自有检测资料"}],
            "transfer_reasoning":{"keep":["结果前置"],"replace":["原品牌"],"reason":"借机制，不抄表面"},
            "open_questions":["真实入口是什么？"],
            "reconstruction":{
                "goal":"换成自有商品和真实证据",
                "shots":[
                    {"time":"0-3秒","visual":"顾客问题动作","text":"真实问题","job":"停下"},
                    {"time":"3-6秒","visual":"自有商品","text":"解决哪一步","job":"理解"},
                    {"time":"6-10秒","visual":"过程证据","text":"可核验事实","job":"相信"},
                    {"time":"10-12秒","visual":"核验入口","text":"下一步","job":"行动"},
                ],
                "owner_questions":["真正要卖给谁？","你有哪些合法证据？","真实入口是什么？"],
            },
        }
        self.assertIs(validate_whitebox(whitebox),whitebox)
        rendered=whitebox_html({"whitebox_analysis":whitebox},"")
        self.assertIn("每一段拍了什么、说了什么",rendered)
        self.assertIn("可以学什么",rendered)
        self.assertIn("换成你的业务",rendered)
        self.assertIn("只有这一点会影响结果",rendered)
        self.assertNotIn("schema_version",rendered)
        shorter={**whitebox,"timeline":whitebox["timeline"][:1]}
        self.assertIs(validate_whitebox(shorter),shorter)

    def test_model_review_v2_can_continue_without_fixed_quality_blocks(self):
        from apply_model_review import apply
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);analysis=root/"analysis.json";review=root/"review.json"
            atomic_write_json(analysis,{"interpretations":{},"confidence":{}})
            atomic_write_json(review,{"schema_version":"model_review/v2","reviewer_type":"agent","validation":{"missing":[],"broken_paths":[]},"labels":{"recommendation":{"decision":"hold"}}})
            self.assertEqual("hold",apply(analysis,review)["model_review"]["decision"])

    def test_model_review_rejects_unknown_decision_enum(self):
        from apply_model_review import apply
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);analysis=root/"analysis.json";review=root/"review.json"
            atomic_write_json(analysis,{"interpretations":{},"confidence":{}})
            atomic_write_json(review,{"schema_version":"model_review/v1","reviewer_type":"agent","validation":{"missing":[],"broken_paths":[]},"labels":{"recommendation":{"decision":"banana"}}})
            with self.assertRaisesRegex(ValueError,"decision 非法"):apply(analysis,review)


if __name__ == "__main__":
    unittest.main()
