# 运行接续

所有命令在素材工作台目录运行，路径参数由Agent填写。学员不需要手工输入。

## 素材发现与下载

底层沿用 `engine/operate-content-strategy-lead/scripts/`：

- `daily_run.py --workspace 项目/.content-flywheel --discover-public --top 3 --analysis local`：按已有业务配置发现、去重、下载；返回待Agent复核时继续看原片/关键帧及转写，不能停在候选列表。
- `feigua_search.py`：已有登录和授权时使用供应商投放素材来源，具体参数看原Skill。
- `import_ad_intelligence.py`：已有供应商导出文件可直接导入。导入不是已经联网搜索。
- `run_pipeline.py --workspace 项目/.content-flywheel --source 已有视频路径 --analysis local`：接入本地素材。先核对其转写依赖与授权，不把本地分析选项当作保证零外部调用。
- `apply_model_review.py`、`rebuild_experiment.py`：Agent实际看过证据并完成拆解后，应用复核并重建适配判断。新产生的 `runs/*/experiment.json` 自动进入工作台。

若业务配置不满足旧引擎要求，使用其已有初始化/配置脚本，保留已有事实。不要偷偷填默认产品、受众或效果指标来通过校验。

## 页面请求与真实产物

```bash
python3 agent_bridge.py --project 项目路径 pending
python3 agent_bridge.py --project 项目路径 complete --request 请求ID --result 结果JSON路径
```

制作/修改内容时的结果文件：

```json
{"base_version": null, "text": "完整第一版内容"}
```

改稿的 `base_version` 填真实读取的当前版本，如 `v1`。新版本默认未采用，等待用户看结果。采用、实际投用与市场效果分开。

其他请求结果格式：

```json
{"output_refs": ["runs/真实运行目录/experiment.json"], "summary": "完成了什么，仍有哪些未知"}
```

引用必须在当前项目 `.content-flywheel` 内且文件真实存在。搜索无结果也可以形成带实际查询范围和失败/空结果说明的回执，不编造候选。

企业纠正后，在共同底稿和重新适配后的实验中写入真实当前 `workbench_context_revision`（用 `Workspace.context_revision()` 取得），再完成请求。对不适配或未判断的旧实验将 `adoptable` 设为 false 并保留原因，不销毁原片或历史判断。不能只填写修订标记冒充已重新理解。

重复提交已完成请求返回既有结果；业务改变后，旧请求不能直接完成。重新读取现状、创建对应新请求再执行。

## 当前能力事实

页面支持素材查看、原片播放、完整拆解、业务纠正、制作任务、修改请求、内容版本、采用、结果快照、下一轮请求。AI推理发生在宿主Agent对话内，本版本没有常驻模型服务。课堂演示要真实展示“页面提出要求→Agent执行→刷新看到结果”，不能说点按钮后模型已在无人值守运行。

## 新业务接入

先读现有工作流/产品资料，归纳业务目标、客户、产品、真实证据与表达边界。`assets/learner_business_brief.example.json` 是结构例子，不是可直接沿用的企业事实。

用真实整理的 `learner_business_brief/v1` 调用 `engine/operate-content-strategy-lead/scripts/setup_from_brief.py --workspace 项目/.content-flywheel --brief 已有业务简报.json`，承接其生成的企业配置和共同底稿。不要把启动原引擎的旧页面当成本包唯一入口；用户入口仍是 `server.py`。

随后核对当前业务配置是否保留了用户在页面作出的纠正，复核或降级原推荐。用 `Workspace.context_revision()` 标记共同底稿和已重审实验的 `workbench_context_revision`，再完成 `context_review`。新业务下重新建立内容任务，旧企业的任务只供回看，不通过保存新版本偷换其业务身份。

## 添加视频后的续接

页面已把原文件保存到 `uploads/`，待办的 `attachment_path` 指向实际文件。先检查依赖，再运行：

```bash
python3 connectors.py check
python3 connectors.py ingest --project 项目路径 --request 请求ID
```

默认只下载/接入并抽帧，不调用外部转写；已有转写授权时才加 `--allow-asr`。视频直链可用 `--source`，抖音分享页必须先由原连接器解析。这个命令留下“证据已到，待复核”，不会伪装成拆解已经完成。失败时查原运行记录修复，再重试；成功后重试会承接同一结果。

Agent 接着读取真实原片、关键帧与可得转写，按原策略 Skill 做 `model_review/v2`，使用 `apply_model_review.py` 与 `rebuild_experiment.py` 保存。只有实际完成后才以结果文件提交 `complete`。仅有关键帧时，涉及未听见的台词、节奏或完整视频判断保持未知。

## 复盘与下一轮

按 [增长接续协议](growth-actions.md) 执行。`growth_review` 交付 AI 实际完成的批量诊断，`next_cycle` 交付依据诊断形成的新策略，`production` 再制作正文。旧版把 `next_cycle` 直接提交正文的方式已停用。

## 卡住时

- 缺来源登录/配额：说明缺哪一项，保留请求；先用已有视频或已授权导出继续，不能假称联网找到。
- 缺业务事实：只问影响这一步的一处，不填一个看似合理的答案。
- 内容版本冲突：重读当前版本，保留双方修改，再保存；不覆盖较新的稿件。
- 业务改变：旧请求标为需要重审，新判断要基于更新后的资料。
- 校验不通过：原文件和失败记录保留，修复后重试；不得直接把状态改为完成。
