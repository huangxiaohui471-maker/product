# Data contracts

所有 JSON 使用 UTF-8，时间使用带时区 RFC3339，契约使用 `schema_version` 显式标识。未知字段必须保留兼容，缺失关键字段必须阻塞而非猜测。

## `creative_evidence/v1`

```json
{
  "schema_version": "creative_evidence/v1",
  "creative_id": "douyin:aweme_id",
  "platform": "douyin",
  "canonical_url": "https://www.douyin.com/video/...",
  "author": {"platform_id": "...", "display_name": "..."},
  "published_at": "RFC3339",
  "collected_at": "RFC3339",
  "metrics": {"plays": null, "likes": null, "comments": null, "shares": null, "collects": null},
  "evidence_class": "verified_paid_platform_library|verified_paid_owned_account|authorized_top_ad|third_party_ad_library|commercial_like_proxy|public_content_only|user_supplied_unverified",
  "organic_metrics": {},
  "paid_metrics": {},
  "estimated_metrics": {},
  "paid_evidence": {"level": "verified_paid|strong_signal|weak_signal|unknown", "sources": []},
  "media": {"local_path": "...", "sha256": "...", "duration_sec": null, "width": null, "height": null},
  "source_snapshot_path": "...",
  "provenance": {"adapter": "tikhub", "adapter_version": "..."}
}
```

指标必须分仓：公开互动只进入 `organic_metrics`；只有官方广告库或获授权广告账户真值才进入 `paid_metrics`；第三方供应商的曝光、金额、计划数、热度和“跑量分”只能进入 `estimated_metrics`。`metrics` 暂为向后兼容的公开互动镜像。

## `ad_intelligence_batch/v1`

飞瓜易投、AppGrowing 等第三方导出先归一化为候选批次，不能直接写成官方已验证投放：

```json
{
  "schema_version": "ad_intelligence_batch/v1",
  "provider": "feigua_yitou|appgrowing|generic",
  "source_receipt": {"filename": "...", "sha256": "...", "row_count": 1},
  "provider_export_verified": false,
  "evidence_policy": "unverified import; user_supplied_unverified; supplier estimates never become paid_metrics",
  "candidates": [{
    "schema_version": "ad_intelligence_candidate/v1",
    "provider_record_id": "...",
    "creative_id": "douyin:...|provider:...",
    "platform": "douyin|oceanengine_unspecified|kuaishou|xiaohongshu|unknown",
    "canonical_url": "...",
    "media_url": "...",
    "source_library_url": "...",
    "advertiser": "...",
    "first_seen_at": "...",
    "last_seen_at": "...",
    "evidence_class": "user_supplied_unverified|third_party_ad_library",
    "paid_metrics": {},
    "estimated_metrics": {}
  }]
}
```

文件名、列名或 `provider` 参数本身不能证明来源。默认导入为 `user_supplied_unverified/unknown`；只有确认为供应商原始导出时，才作为第三方广告素材信号使用。素材进入后直接下载和分析，不增加媒体权利确认流程。

## `creative_analysis/v1`

```json
{
  "schema_version": "creative_analysis/v1",
  "creative_id": "douyin:aweme_id",
  "route": "native_video|scene_fusion|fixed_frame_fallback",
  "route_version": "...",
  "observations": {
    "transcript": [],
    "onscreen_text": [],
    "shots": [],
    "people": [],
    "settings": [],
    "products": [],
    "audio": []
  },
  "interpretations": {
    "opening_hook": "...",
    "target_situation": "...",
    "customer_tension": "...",
    "action_answer": "...",
    "proof_devices": [],
    "offer": "...",
    "cta": "...",
    "narrative_structure": [],
    "production_pattern": "..."
  },
  "confidence": {},
  "evidence_refs": [],
  "model": {"provider": "...", "name": "...", "prompt_version": "..."},
  "degradations": []
}
```

`observations` 只能包含可回看证据支持的观察；`interpretations` 必须保留置信度和证据引用。

视觉复核完成后，`creative_analysis/v1` 可以增加用户白盒块 `whitebox_analysis`：

- `one_sentence_logic`：一句话解释整条素材怎样推进。
- `timeline`：至少三段，每段包含时间、任务、画面、口播/屏幕信息、二者配合、作用和可回看证据。
- `persuasion_chain`：用“为什么停下/继续/相信/行动”的用户问题解释判断。
- `claims_to_check`：只用“来源说什么—目前能确认什么—使用前补什么”的人话。
- `transfer_reasoning`：明确保留机制、替换表面及理由。
- `open_questions`：为企业上下文或执行准备留下可继续互动的问题。

它是详细、可质疑的用户分析，不是内部审计字段。不得出现 C/I/P、Schema、置信度枚举或工作流状态代码。没有该块时可以兼容旧产物，但驾驶舱必须明确显示“详细拆解待补”，不得用五行摘要冒充完整拆解。

`model_review/v2` 在此基础上可增加：

- `whitebox_analysis.reconstruction`：`goal` + 4–6 段 `shots`（每段含 `time/visual/text/job`）+ 3–5 个真正问句形式的 `owner_questions`。

前台展示可回看的关键画面、逐段说服逻辑、不能照抄的部分和可执行重拍建议。需要老板补充事实时最多问一个真正会改变方向的问题。

## `strategy_cluster/v1`

```json
{
  "schema_version": "strategy_cluster/v1",
  "cluster_id": "...",
  "label": "...",
  "mechanism": "...",
  "member_creative_ids": [],
  "first_seen_at": "RFC3339",
  "last_seen_at": "RFC3339",
  "novelty": "new|growing|stable|cooling",
  "evidence_strength": 0.0
}
```

## `experiment_task/v1`

```json
{
  "schema_version": "experiment_task/v1",
  "experiment_id": "...",
  "enterprise_context_id": "...",
  "business_goal": "...",
  "target_customer": "...",
  "customer_situation": "...",
  "hypothesis": "...",
  "why_now": "...",
  "evidence_creative_ids": [],
  "borrow_mechanism": "...",
  "do_not_copy": [],
  "single_variable": {"name": "...", "from": "...", "to": "..."},
  "constants": [],
  "required_assets": [],
  "draft_brief": "...",
  "future_success_signals": [],
  "decision": "pending|adopt|hold|reject",
  "decision_reason": null
}
```

运行时扩展字段：`adoptable` 是结构化安全门；`hold_reasons` 为可累积原因；`visible_in_dashboard=false` 抑制重复卡；`claim_boundaries` 供未来生产消费者执行品牌与合规边界。消费者必须容忍新增可选字段。

`production_handoff` 是给未来脚本/图片/视频生产模块的可选扩展：它传递完整重拍目标、4–6段分镜、老板问题和主张核验清单。本期只产出该契约，不调用生产模块。

## `daily_run/v1` 的候选漏斗扩展

每日回执必须保留一个源批次，不能把同一天多个搜索批次合并成更大的前台数字。

```json
{
  "schema_version": "daily_run/v1",
  "source_batch": ".../candidates.json",
  "candidate_funnel": {
    "discovered": 14,
    "shortlisted": 8,
    "already_seen": 2,
    "deep_reviewed": 1,
    "failed": 0
  },
  "shortlist": [
    {
      "rank": 1,
      "creative_id": "...",
      "title": "...",
      "reason": "命中当前业务词和成交表达",
      "status": "待深拆|已进入深拆|历史已看，已排重|本次读取失败"
    }
  ]
}
```

`shortlist` 最多 8 条；`reason` 使用业务语言，不得向学员展示模型分、权重或证据等级。前台的发现、入围、深拆和排重数字必须全部来自这一个回执。

## `decision_event/v1`

```json
{
  "schema_version": "decision_event/v1",
  "event_id": "...",
  "experiment_id": "...",
  "decision": "adopt|hold|reject",
  "reason": "...",
  "decided_by": "human",
  "decided_at": "RFC3339",
  "cooldown_until": "RFC3339|null"
}
```

## `feedback_event/v1`（未来接口，本期只校验与存档）

```json
{
  "schema_version": "feedback_event/v1",
  "feedback_id": "...",
  "experiment_id": "...",
  "event_type": "published|metric_snapshot|human_review|stopped",
  "occurred_at": "RFC3339",
  "source": "future-producer-or-review-system",
  "metrics": {},
  "human_notes": ""
}
```

第一阶段不得根据该事件自动改写判断标准，只能追加式存档，待复盘模块另行认证。

## `performance_result/v1`（未来正式效果回流接口）

必填 `result_id/experiment_id/observed_at/source/metrics/measurement_window`。本期只做契约校验、幂等与追加式存档，不据此自动修改策略、判断标准或发布状态。
