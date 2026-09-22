#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,tempfile,threading,unittest,urllib.request
from unittest.mock import patch
from datetime import datetime,timedelta
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from common import atomic_write_json,read_json
from init_workspace import main as _unused
from run_pipeline import run
from dummy_future_consumer import consume
from apply_model_review import apply as apply_review
from rebuild_experiment import rebuild
from memory_store import MemoryStore
from render_dashboard import render
from serve_dashboard import DashboardHandler
from import_ad_intelligence import import_file as import_ad_intelligence
from run_ad_intel_candidate import run_candidate as run_ad_intel_candidate
from setup_from_brief import configure as setup_from_brief
import setup_from_brief as setup_module
from daily_run import _business_fit,_score,run_daily

SCRIPTS=Path(__file__).parent
class PipelineTests(unittest.TestCase):
    def complete_v2_review(self,review_dir:Path,decision:str="adopt")->dict:
        timeline=[
            {"time":"0-1秒","stage":"让人停下","visual":"商品近景","spoken_message":"真实问题","how_they_work_together":"画面给结果，口播留悬念","why_it_matters":"快速识别商品","evidence":["audit.jpg"]},
            {"time":"1-3秒","stage":"继续看","visual":"使用动作","spoken_message":"解释一步","how_they_work_together":"动作承接解释","why_it_matters":"建立理解","evidence":["audit.jpg"]},
            {"time":"3-4秒","stage":"决定行动","visual":"结果画面","spoken_message":"经核验下一步","how_they_work_together":"结果与入口同时出现","why_it_matters":"减少行动疑问","evidence":["audit.jpg"]},
        ]
        shots=[{"time":f"{i}-{i+1}秒","visual":f"自有画面{i}","text":f"可核验信息{i}","job":job} for i,job in enumerate(("停下","理解","相信","行动"))]
        whitebox={"one_sentence_logic":"先用真实结果留人，再用过程证据完成行动。","timeline":timeline,
            "persuasion_chain":[{"question":"为什么停下？","answer":"第一眼看见结果","evidence":"audit.jpg"}],
            "claims_to_check":[{"source_says":"效果好","what_we_can_confirm":"只能确认来源说过","needed_before_use":"自有成交证据"}],
            "transfer_reasoning":{"keep":["结果前置"],"replace":["竞品品牌"],"reason":"只借说服顺序"},"open_questions":["真实客户是谁？"],
            "reconstruction":{"goal":"换成自有商品、证据与入口","shots":shots,"owner_questions":[]}}
        return {"schema_version":"model_review/v2","reviewer_type":"independent_agent","validation":{"missing":[],"broken_paths":[]},"labels":{"ad_intent":{"label":"paid_like","confidence":.9},"hook":{"label":"竞品开场","confidence":.9},"target_stage":{"label":"awareness"},"pain_or_desire":{"label":"痛点"},"proof":{"label":"过程演示"},"offer":{"label":"none"},"cta":{"label":"none"},"scene":{"label":"商品演示"},"transferable_mechanism":{"label":"结果前置—过程证明—行动"},"non_transferable_surface":{"value":["竞品品牌"]},"context_fit":{"score_0_to_1":.9},"recommendation":{"decision":decision,"confidence":.9},"evidence_refs":["audit.jpg"],"whitebox_analysis":whitebox}}
    def fixture(self,root:Path)->tuple[Path,Path]:
        ws=root/"ws"
        subprocess.run(["python3",str(SCRIPTS/"init_workspace.py"),"--workspace",str(ws),"--name","夹具企业","--industry","local_life"],check=True,capture_output=True)
        c=read_json(ws/"config/enterprise_context.json");c.update({"long_term_business":"本地门店增长","business_goal":"提升到店",
            "current_priority":"验证开场","target_customer":"三公里顾客","products":["套餐"],"claim_boundaries":["不虚构销量"],
            "production_capabilities":["门店实拍"],"authorization_scope":{"platforms":["manual"],"public_sources_only":True,"max_downloads_per_run":5}});atomic_write_json(ws/"config/enterprise_context.json",c)
        video=root/"ad.mp4";subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","testsrc=size=360x640:rate=15:duration=4","-c:v","libx264","-pix_fmt","yuv420p",str(video)],check=True)
        return ws,video
    def test_full_local_route_and_repeat_suppression(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));first=run(ws,str(video),"local");second=run(ws,str(video),"local")
            a=read_json(first/"experiment.json");b=read_json(second/"experiment.json")
            self.assertFalse(a["adoptable"]);self.assertFalse(b["is_new_creative"]);self.assertFalse(b["visible_in_dashboard"])
            self.assertTrue(a["needs_strategy_review"])
            manifest=read_json(first/"run_manifest.json")
            self.assertEqual(manifest["status"],"succeeded")
            stages=[row["stage"] for row in manifest["stage_history"]]
            self.assertEqual(stages[0],"WAIT_CONFIG")
            self.assertIn("COLLECTING",stages);self.assertIn("UNDERSTANDING",stages)
            self.assertIn("DEGRADED_UNDERSTANDING",stages)
            self.assertEqual(stages[-1],"WAIT_DECISION")
            self.assertTrue((first/"events/state_transitions.jsonl").exists())
            self.assertEqual(consume(first/"experiment.json")["status"],"ACK")
            dashboard=(ws/"dashboard.html").read_text()
            self.assertEqual(dashboard.count("data-id="),1)
            self.assertIn("今日作战",dashboard);self.assertIn("素材情报",dashboard)
            self.assertIn("素材库",dashboard);self.assertIn("我的记忆",dashboard)
            self.assertIn("<video",dashboard);self.assertNotIn("prompt(",dashboard)
            self.assertIn("每日内容情报 · 自然流",dashboard);self.assertNotIn("今天同行在投什么",dashboard)
            decided_at=datetime.now().astimezone()
            MemoryStore(ws).add_decision({"schema_version":"decision_event/v1","event_id":"test-hold","experiment_id":b["experiment_id"],"decision":"hold","reason":"","decided_by":"human","decided_at":decided_at.isoformat(),"cooldown_until":(decided_at+timedelta(days=3)).isoformat()})
            render(ws,ws/"dashboard.html")
            self.assertIn("今天还没有可拆解的视频",(ws/"dashboard.html").read_text())
    def test_incomplete_context_fails_with_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ws=root/"ws";subprocess.run(["python3",str(SCRIPTS/"init_workspace.py"),"--workspace",str(ws),"--name","空企业"],check=True,capture_output=True)
            with self.assertRaises(ValueError):run(ws,"missing.mp4","local")
            manifest=read_json(next((ws/"runs").glob("*/run_manifest.json")));self.assertEqual(manifest["status"],"failed")
            self.assertEqual(manifest["current_stage"],"BLOCKED_INPUT")

    def test_pipeline_failure_before_completion_does_not_pollute_seen_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp))
            with patch("run_pipeline.render",side_effect=OSError("dashboard write failed")):
                with self.assertRaises(OSError):run(ws,str(video),"local")
            self.assertEqual(MemoryStore(ws).seen_index(),{})
            manifest=read_json(next((ws/"runs").glob("*/run_manifest.json")),{})
            self.assertEqual(manifest["status"],"failed")

    def test_memory_commit_rolls_back_seen_when_run_history_write_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp))
            with patch.object(MemoryStore,"add_run",side_effect=OSError("history write failed")):
                with self.assertRaises(OSError):run(ws,str(video),"local")
            store=MemoryStore(ws)
            self.assertEqual(store.seen_index(),{})
            self.assertFalse(store.run_path.exists())

    def test_connector_evidence_seed_survives_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));seed={"creative_id":"douyin:123","platform":"douyin","canonical_url":"https://www.douyin.com/video/123","metrics":{"plays":9},"paid_evidence":{"level":"weak_signal","sources":["high_like_rate"]},"evidence_class":"public_content_only","provenance":{"adapter":"tikhub"}}
            out=run(ws,str(video),"local",seed);e=read_json(out/"creative/evidence.json");x=read_json(out/"experiment.json")
            self.assertEqual(e["creative_id"],"douyin:123");self.assertEqual(e["provenance"]["adapter"],"tikhub");self.assertEqual(x["evidence_creative_ids"],["douyin:123"])
            self.assertEqual(e["evidence_class"],"public_content_only")

    def test_agent_visual_review_closes_strategy_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review={"schema_version":"model_review/v1","reviewer_type":"independent_agent","validation":{"missing":[],"broken_paths":[]},"labels":{"ad_intent":{"label":"organic_like","confidence":.9},"hook":{"label":"竞品黄桃果霸问题开场","confidence":.9},"target_stage":{"label":"awareness"},"pain_or_desire":{"label":"痛点"},"proof":{"label":"演示"},"offer":{"label":"none"},"cta":{"label":"none"},"scene":{"label":"口播"},"transferable_mechanism":{"label":"问题—证据—行动"},"non_transferable_surface":{"value":["竞品黄桃果霸"]},"context_fit":{"label":"partial","confidence":.8},"recommendation":{"decision":"hold","confidence":.9},"evidence_refs":[]}}
            # Initial, unreviewed workspace clusters are UI candidates only. They must
            # never enter durable pattern memory before an explicit review/rebuild.
            self.assertFalse((ws/"memory/pattern_history.jsonl").exists())
            review_path=out/"review.json";atomic_write_json(review_path,review);apply_review(out/"analysis/analysis.json",review_path);task=rebuild(ws,out)
            self.assertEqual(task["decision"],"hold");self.assertFalse(task["adoptable"]);self.assertTrue((out/"mechanism_clusters.json").exists())
            self.assertEqual(task["borrow_mechanism"],"问题—证据—行动")
            learner_action=json.dumps({key:task.get(key) for key in ("hypothesis","borrow_mechanism","single_variable","draft_brief")},ensure_ascii=False)
            self.assertNotIn("竞品黄桃果霸",learner_action)
            self.assertFalse((ws/"memory/pattern_history.jsonl").exists())
            review["labels"]["recommendation"]={"decision":"adopt","confidence":.9};atomic_write_json(review_path,review);apply_review(out/"analysis/analysis.json",review_path);task=rebuild(ws,out)
            self.assertEqual(task["decision"],"hold");self.assertFalse(task["adoptable"])
            self.assertIn("详细拆解未达当前证据门",task["decision_reason"])
            self.assertFalse((ws/"memory/pattern_history.jsonl").exists())

    def test_v2_review_with_artifacts_reconstruction_and_questions_is_adoptable(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review_path=out/"review-v2.json";atomic_write_json(review_path,self.complete_v2_review(out))
            apply_review(out/"analysis/analysis.json",review_path);task=rebuild(ws,out)
            self.assertTrue(task["adoptable"]);self.assertEqual(task["decision"],"pending")
            self.assertEqual(len((ws/"memory/pattern_history.jsonl").read_text().splitlines()),1)
            dashboard=(ws/"dashboard.html").read_text()
            self.assertIn("换成你的业务，可以这样重拍",dashboard)
            self.assertIn("你只需要补充这几件真实信息",dashboard)
            self.assertNotIn("retained-audit-frame",dashboard)

    def test_v2_review_list_non_transferable_surface_rebuilds_dashboard(self):
        """Real reviewer output may use the contract's direct list form."""
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review=self.complete_v2_review(out,decision="hold")
            review["labels"]["non_transferable_surface"]=["竞品品牌","竞品价格"]
            review["labels"]["whitebox_analysis"]["persuasion_chain"]="问题开场 → 过程证明 → 行动"
            review["labels"]["whitebox_analysis"]["claims_to_check"]=["销量需要核验","价格需要核验"]
            review["labels"]["whitebox_analysis"]["transfer_reasoning"]="只借说服顺序，替换品牌、价格与证据。"
            review_path=out/"review-v2-list.json";atomic_write_json(review_path,review)
            apply_review(out/"analysis/analysis.json",review_path);task=rebuild(ws,out)
            self.assertEqual(task["decision"],"hold")
            dashboard=(ws/"dashboard.html").read_text()
            self.assertIn("竞品品牌",dashboard);self.assertIn("竞品价格",dashboard)
            self.assertIn("问题开场 → 过程证明 → 行动",dashboard)
            self.assertIn("销量需要核验",dashboard)
            self.assertIn("只借说服顺序，替换品牌、价格与证据。",dashboard)

    def test_nested_mechanism_values_never_leak_python_dict_repr(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review=self.complete_v2_review(out)
            review["labels"]["transferable_mechanism"]=[
                {"value":"结果可视化开场","confidence":.9},
                {"label":"只讲一个决策点","confidence":.8},
            ]
            review_path=out/"review-nested.json";atomic_write_json(review_path,review)
            apply_review(out/"analysis/analysis.json",review_path);rebuild(ws,out)
            dashboard=(ws/"dashboard.html").read_text()
            self.assertIn("结果可视化开场",dashboard)
            self.assertIn("只讲一个决策点",dashboard)
            self.assertNotIn("{'value':",dashboard)
            self.assertNotIn("'confidence':",dashboard)

    def test_rejected_review_never_becomes_lead_or_formal_library_item(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review_path=out/"review-reject.json";atomic_write_json(review_path,self.complete_v2_review(out,"reject"))
            apply_review(out/"analysis/analysis.json",review_path);task=rebuild(ws,out)
            self.assertEqual("excluded",task["recommendation_state"])
            self.assertFalse(task["adoptable"])
            dashboard=(ws/"dashboard.html").read_text()
            self.assertNotIn(task["experiment_id"],dashboard)

    def test_compact_completed_review_is_not_labeled_still_processing(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review=self.complete_v2_review(out);review["labels"].pop("whitebox_analysis")
            review_path=out/"review-compact.json";atomic_write_json(review_path,review)
            apply_review(out/"analysis/analysis.json",review_path);rebuild(ws,out)
            dashboard=(ws/"dashboard.html").read_text()
            self.assertIn("系统已经看过画面和口播",dashboard)
            self.assertNotIn("还在拆这条视频",dashboard)
            self.assertNotIn("进入制作模块前须人工确认",dashboard)

    def test_legacy_v1_adopt_cannot_override_incomplete_hold_task(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            task=read_json(out/"experiment.json");task.update({"decision":"hold","adoptable":False,"recommendation_state":None,"content_ready":None})
            task["review_gate"]={"decision":"adopt","recommendation":{"decision":"adopt"}}
            atomic_write_json(out/"experiment.json",task);render(ws,ws/"dashboard.html")
            pointer=read_json(ws/"current_strategy.json")
            self.assertEqual("processing",pointer["status"])
            self.assertNotIn(task["experiment_id"],(ws/"dashboard.html").read_text())

    def test_server_post_rerenders_durable_decision_state(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local");task=read_json(out/"experiment.json")
            DashboardHandler.workspace=ws
            server=ThreadingHTTPServer(("127.0.0.1",0),partial(DashboardHandler,directory=str(ws)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                event={"schema_version":"decision_event/v1","event_id":"http-adopt","experiment_id":task["experiment_id"],"decision":"adopt","reason":"","decided_by":"human","decided_at":__import__('datetime').datetime.now().astimezone().isoformat(),"cooldown_until":None}
                request=urllib.request.Request(f"http://127.0.0.1:{server.server_port}/api/decisions",data=json.dumps(event).encode(),headers={"Content-Type":"application/json"},method="POST")
                with self.assertRaises(urllib.error.HTTPError) as blocked:urllib.request.urlopen(request,timeout=5)
                self.assertEqual(blocked.exception.code,400)
                event.update({"event_id":"http-hold","decision":"hold"})
                request=urllib.request.Request(f"http://127.0.0.1:{server.server_port}/api/decisions",data=json.dumps(event).encode(),headers={"Content-Type":"application/json"},method="POST")
                self.assertEqual(json.loads(urllib.request.urlopen(request,timeout=5).read()),{"ok":True})
                self.assertEqual(read_json(out/"run_manifest.json")["current_stage"],"DONE")
            finally:
                server.shutdown();server.server_close();thread.join(timeout=3)

    def test_live_dashboard_serves_video_and_accepts_ready_action(self):
        """The learner uses the local app, so media and its one main action must work over HTTP."""
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review_path=out/"review-v2.json";atomic_write_json(review_path,self.complete_v2_review(out))
            apply_review(out/"analysis/analysis.json",review_path);task=rebuild(ws,out)
            DashboardHandler.workspace=ws
            server=ThreadingHTTPServer(("127.0.0.1",0),partial(DashboardHandler,directory=str(ws)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base=f"http://127.0.0.1:{server.server_port}"
                dashboard=urllib.request.urlopen(base+"/dashboard.html",timeout=5).read().decode()
                import re
                src=re.search(r'<video[^>]+src="([^"]+)"',dashboard).group(1)
                media=urllib.request.urlopen(base+"/"+src.lstrip("./"),timeout=5).read()
                self.assertGreater(len(media),100)
                event={"schema_version":"decision_event/v1","event_id":"http-ready-adopt","experiment_id":task["experiment_id"],"decision":"adopt","reason":"","decided_by":"human","decided_at":datetime.now().astimezone().isoformat(),"cooldown_until":None}
                request=urllib.request.Request(base+"/api/decisions",data=json.dumps(event).encode(),headers={"Content-Type":"application/json"},method="POST")
                self.assertEqual(json.loads(urllib.request.urlopen(request,timeout=5).read()),{"ok":True})
                self.assertIn("http-ready-adopt",(ws/"memory/decisions.jsonl").read_text())
            finally:
                server.shutdown();server.server_close();thread.join(timeout=3)

    def test_business_relevance_beats_unrelated_viral_heat(self):
        context={"target_customer":"三公里家庭顾客","business_goal":"提升到店核销","current_priority":"冒菜套餐","products":["冒菜套餐"]}
        watch={"keywords":["冒菜","门店团购"]}
        relevant={"creative_id":"relevant","title":"附近冒菜双人套餐到店团购","organic_metrics":{"likes":120},"canonical_url":"https://example.com/r"}
        viral={"creative_id":"viral","title":"小游戏通关挑战","organic_metrics":{"likes":99999999},"canonical_url":"https://example.com/v"}
        self.assertGreater(_business_fit(relevant,context,watch),_business_fit(viral,context,watch))
        self.assertGreater(_score(relevant,context,watch),_score(viral,context,watch))

    def test_current_strategy_pointer_matches_rendered_lead(self):
        with tempfile.TemporaryDirectory() as temp:
            ws,video=self.fixture(Path(temp));out=run(ws,str(video),"local")
            review_path=out/"review-v2.json";atomic_write_json(review_path,self.complete_v2_review(out))
            apply_review(out/"analysis/analysis.json",review_path);task=rebuild(ws,out)
            pointer=read_json(ws/"current_strategy.json")
            dashboard=(ws/"dashboard.html").read_text()
            self.assertEqual(pointer["experiment_id"],task["experiment_id"])
            self.assertEqual(pointer["creative_id"],task["creative_id"])
            self.assertIn(task["experiment_id"],dashboard)

    def test_daily_view_excludes_yesterday_and_old_adopt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ws,video=self.fixture(root);old_run=run(ws,str(video),"local");old_task=read_json(old_run/"experiment.json")
            yesterday=(datetime.now().astimezone()-timedelta(days=1)).strftime("%Y-%m-%d")
            renamed=old_run.with_name(yesterday+old_run.name[10:]);old_run.rename(renamed)
            MemoryStore(ws).add_decision({"schema_version":"decision_event/v1","event_id":"yesterday-adopt","experiment_id":old_task["experiment_id"],"decision":"adopt","reason":"","decided_by":"human","decided_at":(datetime.now().astimezone()-timedelta(days=1)).isoformat(),"cooldown_until":None})
            second=root/"ad2.mp4";subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=blue:size=360x640:rate=15:duration=4","-c:v","libx264","-pix_fmt","yuv420p",str(second)],check=True)
            current=run(ws,str(second),"local");current_task=read_json(current/"experiment.json")
            render(ws,ws/"dashboard.html");dashboard=(ws/"dashboard.html").read_text()
            self.assertNotIn(old_task["experiment_id"],dashboard)
            self.assertIn(current_task["experiment_id"],dashboard)

    def test_review_completed_today_surfaces_yesterday_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ws,video=self.fixture(root);run_dir=run(ws,str(video),"local")
            yesterday=(datetime.now().astimezone()-timedelta(days=1)).strftime("%Y-%m-%d")
            renamed=run_dir.with_name(yesterday+run_dir.name[10:]);run_dir.rename(renamed)
            review_path=renamed/"review-v2.json";atomic_write_json(review_path,self.complete_v2_review(renamed))
            apply_review(renamed/"analysis/analysis.json",review_path);task=rebuild(ws,renamed)
            self.assertEqual(task["reviewed_at"][:10],datetime.now().astimezone().strftime("%Y-%m-%d"))
            dashboard=(ws/"dashboard.html").read_text()
            self.assertIn(task["experiment_id"],dashboard)
            self.assertIn("换成你的业务，可以这样重拍",dashboard)

    def test_feigua_export_to_full_pipeline_keeps_estimates_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ws,video=self.fixture(root);source=root/"飞瓜样例.csv"
            source.write_text("素材ID,投放平台,视频下载地址,素材标题,广告主,投放类型,首次发现,最后发现,曝光指数,预估消耗\nFG-001,巨量本地推,%s,附近冒菜团购,测试品牌,本地推,2026-08-09,2026-08-10,88,100-300元\n"%video,encoding="utf-8")
            batch_path=import_ad_intelligence(ws,source,"feigua_yitou",verified_provider_export=True);batch=read_json(batch_path);candidate=batch["candidates"][0]
            self.assertEqual(candidate["evidence_class"],"third_party_ad_library")
            self.assertEqual(candidate["paid_metrics"],{})
            self.assertEqual(candidate["estimated_metrics"]["exposure_index"],"88")
            out=run_ad_intel_candidate(ws,candidate,"local");evidence=read_json(out/"creative/evidence.json")
            self.assertEqual(evidence["evidence_class"],"third_party_ad_library")
            self.assertEqual(evidence["paid_metrics"],{})
            self.assertEqual(evidence["estimated_metrics"]["spend_estimate"],"100-300元")
            self.assertEqual(evidence["provenance"]["adapter"],"feigua_yitou_export")
            self.assertIn("每日内容情报",(ws/"dashboard.html").read_text())

    def test_appgrowing_json_aliases_normalize_without_promoting_estimates(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ws,_=self.fixture(root);source=root/"appgrowing.json"
            atomic_write_json(source,{"items":[{"广告ID":"AG-9","媒体":"巨量引擎","广告详情链接":"https://example.com/ad/AG-9","广告文案":"考研半年冲刺","公司":"测试教育","推广行业":"教育","推广目标":"线索收集","投放金额估算":"1万-3万"}]})
            batch=read_json(import_ad_intelligence(ws,source,"appgrowing"));candidate=batch["candidates"][0]
            self.assertEqual(candidate["platform"],"oceanengine_unspecified")
            self.assertEqual(candidate["objective"],"线索收集")
            self.assertEqual(candidate["paid_metrics"],{})
            self.assertEqual(candidate["estimated_metrics"]["spend_estimate"],"1万-3万")
            self.assertEqual(candidate["evidence_class"],"user_supplied_unverified")
            self.assertEqual(candidate["paid_evidence"]["level"],"unknown")

    def test_brief_setup_and_single_daily_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ws=root/"ws"
            subprocess.run(["python3",str(SCRIPTS/"init_workspace.py"),"--workspace",str(ws),"--name","学员企业","--industry","local_life"],check=True,capture_output=True)
            with patch.object(setup_module,"ACTIVE_WORKSPACE",root/"active-workspace.json"):
                receipt=setup_from_brief(ws,{"name":"学员企业","industry":"local_life","long_term_business":"连锁门店增长",
                    "business_goal":"提升团购核销","current_priority":"验证前三秒","target_customer":"三公里顾客",
                    "products":["冒菜套餐"],"claim_boundaries":["不虚构销量"],"production_capabilities":["门店实拍"]})
            self.assertEqual(receipt["status"],"ready")
            self.assertEqual(read_json(root/"active-workspace.json")["workspace"],str(ws.resolve()))
            self.assertTrue(read_json(ws/"config/watch_universe.json")["keywords"])
            video=root/"daily.mp4";subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=green:size=360x640:rate=15:duration=3","-c:v","libx264","-pix_fmt","yuv420p",str(video)],check=True)
            batch=root/"batch.json";atomic_write_json(batch,{"candidates":[{"schema_version":"ad_intelligence_candidate/v1","provider":"generic","creative_id":"generic:daily-1","platform":"douyin","media_url":str(video),"canonical_url":"","source_library_url":"","paid_evidence":{"level":"unknown","sources":["user"]},"evidence_class":"user_supplied_unverified"}]})
            daily=read_json(run_daily(ws,batch,False,1,"local"),{})
            self.assertEqual(daily["status"],"succeeded")
            self.assertEqual(len(daily["runs"]),1)
            self.assertTrue(daily["runs"][0]["needs_agent_review"])
            self.assertEqual(daily["candidate_funnel"],{"discovered":1,"shortlisted":1,"already_seen":0,"deep_reviewed":1,"failed":0})
            self.assertEqual(daily["shortlist"][0]["status"],"已进入深拆")
            self.assertTrue(daily["shortlist"][0]["reason"])
            repeated=read_json(run_daily(ws,batch,False,1,"local"),{})
            self.assertEqual(repeated["status"],"succeeded")
            self.assertEqual(repeated["runs"],[])
            self.assertEqual(len(repeated["skipped"]),1)
            self.assertEqual(repeated["candidate_funnel"]["already_seen"],1)
            self.assertEqual(repeated["shortlist"][0]["status"],"历史已看，已排重")
            self.assertEqual(repeated["current_stage"],"WAIT_REVIEW")
            second_video=root/"daily2.mp4";subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=blue:size=360x640:rate=15:duration=3","-c:v","libx264","-pix_fmt","yuv420p",str(second_video)],check=True)
            refill=root/"refill.json";atomic_write_json(refill,{"candidates":[read_json(batch,{})["candidates"][0],{"schema_version":"ad_intelligence_candidate/v1","provider":"generic","creative_id":"generic:daily-2","platform":"douyin","media_url":str(second_video),"canonical_url":"","source_library_url":"","paid_evidence":{"level":"unknown","sources":["user"]},"evidence_class":"user_supplied_unverified"}]})
            refilled=read_json(run_daily(ws,refill,False,1,"local"),{})
            self.assertEqual(refilled["selected"][0]["creative_id"],"generic:daily-2")
            upgrade=root/"upgrade.json";upgraded={**read_json(batch,{})["candidates"][0],"evidence_class":"third_party_ad_library","paid_evidence":{"level":"strong_signal","sources":["verified_export"]}}
            atomic_write_json(upgrade,{"candidates":[upgraded]})
            upgraded_run=read_json(run_daily(ws,upgrade,False,1,"local"),{})
            self.assertEqual(len(upgraded_run["runs"]),1)
            self.assertEqual(MemoryStore(ws).seen_index()["generic:daily-1"]["evidence_class"],"third_party_ad_library")
            upgraded_again=read_json(run_daily(ws,upgrade,False,1,"local"),{})
            self.assertEqual(upgraded_again["runs"],[])

    def test_daily_dashboard_failure_never_leaves_false_ready_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ws,video=self.fixture(root)
            batch=root/"batch.json";atomic_write_json(batch,{"candidates":[{"schema_version":"ad_intelligence_candidate/v1","provider":"generic","creative_id":"generic:render-fail","platform":"douyin","media_url":str(video),"canonical_url":"","source_library_url":"","paid_evidence":{"level":"unknown","sources":["user"]},"evidence_class":"user_supplied_unverified"}]})
            with patch("daily_run.render",side_effect=OSError("disk full")):
                receipt=read_json(run_daily(ws,batch,False,1,"local"),{})
            self.assertEqual(receipt["status"],"partial")
            self.assertEqual(receipt["current_stage"],"FAILED_PERMANENT")
            self.assertTrue(any(row.get("type")=="DashboardRenderError" for row in receipt["errors"]))

if __name__=="__main__":unittest.main()
