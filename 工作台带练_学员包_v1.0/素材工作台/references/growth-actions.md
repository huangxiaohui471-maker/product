# 数据整理与分析报告（0.4）

前台是数据总览、内容明细与复盘报告，支持独立查阅和操作。模型执行仍在宿主 Agent。仅保存请求不等于执行完成。

## 只整理数据

`growth_data` 的目标是让已有内容数据可查阅，不附带复盘或策略派工。pending 提供 ledger、ledger_revision 与 attachment_path。按原底账格式整理真实 batch 后，通过 complete 提交 `{ "ledger_revision": "本次读取值", "batch": {"items": []} }`（items实际必须有记录）。保留observed_at、data_through、source_refs和未知值；导入结束不创建growth_review或next_cycle。

## 复盘请求

运行 `agent_bridge.py --project PROJECT pending`，找到 `growth_review`。读取其指定增长 Skill、ledger、ledger_revision、历史 review，以及 attachment_path（如果有）。业务和旧内容都先复用，别让用户填写字段映射或自己分析。

账号可用原 `collect_recent_posts.py` 在既有授权内读取；平台导出、截图或本地资料由 Agent 阅读整理。保留来源、实际发布日期、采集日、数据截止日和原始证据，未知为 null。不自动发起未获授权的外部调用。

原 `build_weekly_diagnosis.py` 是保守诊断起点，不是完整 AI 判断；其中分类、换开场等启发式不适用所有企业。Agent 必须读取实际内容、数据和评论，依据原增长岗位规则作出判断，不把通用模板输出当业务结论。

完成文件示意（字段值必须来自真实任务）：

```json
{
  "ledger_revision": "本次pending中真实读取的值",
  "label": "账号及观察期间",
  "source_note": "数据来源、时间范围和重要缺口",
  "batch": {"items": []},
  "scope": [{"channel": "douyin", "content_id": "实际作品ID"}],
  "diagnosis": {
    "schema_version": "batch_diagnosis/v1",
    "summary": "整体最重要的业务判断",
    "account_review": {"conclusions": ["有数据支持的观察"]},
    "items": [{
      "content_id": "实际作品ID",
      "facts": ["实际数据与反馈"],
      "observations": ["值得留意的差异"],
      "primary_explanation": "尚待验证的主解释",
      "competing_explanations": [],
      "unknowns": [],
      "decision": "validate",
      "next_experiment": "下一次要弄清什么"
    }],
    "next_actions": [{
      "id": "next-1",
      "title": "一个明确的后续动作",
      "source_ids": ["实际作品ID"],
      "keep": ["有依据应保持的条件"],
      "change": "本轮要改变什么",
      "start_condition": "什么条件下开始",
      "measurement": "何时看什么反馈"
    }]
  }
}
```

- 无新数据可省略 batch。新 batch 每条沿用原 update_content_ledger 格式：channel、content_id、title、published_at、production_ref（无就 null）、observed_at、data_through、public_metrics、internal_metrics、business_results、missing_fields、source_refs。重复读取原快照不应把 observed_at 改成当前时间。账号与平台身份需准确，跨账号ID可能重复时使用带账号标识的作品ID。
- scope 仅包含这份复盘实际处理的作品，不把不同账号混成一条排行。跨平台可作对照，但不能直接合算不同指标。
- 可增加 highlights（label/title/detail/content_id）、method_findings、caveats。方法效果需要有方法版本、可比样本等依据，缺少时说明未知。
- 分析报告可以没有 next_actions，也不需要为没有行动计划填写等待理由。已有历史行动建议可保留在原文件中；当前前台不把它做成派工流程。
- 评论原文、截图、导出保存在本项目隐藏区，通过 source_refs 引用；重要评论或用户反馈可放在 business_results 中，不能伪装成数值结果。
- 用户纠正是新的 growth_review，带 review_id。先读旧判断，补证据、形成新版，不覆盖旧观察。新增资料使旧判断失效时，重新核对再发起下一轮。

用 `complete` 提交结果。桥接复用原增量底账和诊断校验器，并保存本轮快照、来源和历史；数据变化时要求重读。

## 后续明确要求的飞轮联动（当前工作台前台不启用）

仅当用户另行要求把复盘带入新策略和制作时，才执行这一节。不能因为报告完成而自动派工。

`next_cycle` 内有 growth_handoff_ref；pending 提供完整 growth_to_strategy，包括 keep、change、source_content、source_review_ref。按策略 Skill 重新判断和组织方向，必要时搜新素材。上一轮历史作品与新生产任务分开保存。

1. 使用原 export_production_handoff 等方法生成真实 `strategy_to_production/v1`：完整企业上下文、目标人群、场景、主张、变量、保持项、来源与表达边界。
2. 为新一轮设置新的 task_id，在策略 JSON 添加 `growth_handoff_ref`，指向请求里的相同文件；存入当前项目 .content-flywheel 内。
3. 通过 complete 提交：

```json
{"strategy_handoff_ref":"handoffs/实际的新策略.json"}
```

桥接复用原生产初始化器，建立新生产任务和制作请求。继续读取生产 Skill、制作首稿并按 production 格式提交。用户在原复盘页可进入新任务。请求若在等关键事实则保留等待并说明缺口，不能写假策略应付完成。

纯表达修改用 revision，不把账号新方向压成旧稿 v2。旧版仅有 learning_id 的 next_cycle 请求须先转 growth_review 核对后续接。已有采用、市场结果不继承到新稿。
