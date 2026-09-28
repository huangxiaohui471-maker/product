# 机会雷达双层分析流程

## 结论

DeepSeek 的分析规则已经内置在 `opportunity_ai_server.py`，但 API Key 不内置。密钥只通过本机环境变量注入，浏览器不会接触密钥。

提示词的唯一运行时来源是服务端 `Handler.do_POST()` 中的两段系统提示词：

- `/api/opportunity/cluster`：需求语义聚类。
- `/api/opportunity/judge`：机会校准与投入判断。

`prompt_history.md` 用来记录提示词版本和用户修正意见；修改规则时追加版本，不覆盖历史版本。

## 第一层：发现需求机会

输入：清洗后的真实数据，包括小红书帖子/评论、淘宝/天猫评论、负面评论和需求评论。

执行链路：

1. 前端读取 `data/eye-care-opportunities/` 下的数据文件。
2. 服务端 `compact_records()` 给每条记录生成 `record_id`，保留来源、商品和原文。
3. `cluster_prompt()` 将记录序列化为模型输入。
4. 服务端系统提示词要求模型按“用户任务、场景、障碍、期望结果”聚类，而不是按症状词频排序。
5. 模型返回 3–5 个机会，每个机会必须保留证据、反证、未知项和来源统计。

关键字段边界：

- `keyword`：只用于雷达图的短痛点标签。
- `title`：面向产品决策的机会标题，不能只是“黑眼圈”“敏感”等症状。
- `product_need`：用户希望得到什么样的产品或服务，不直接编造成分或功效。
- `actual_need`：用户真正想完成的结果和购买任务。
- `evidence`：必须引用真实 `record_id`。

## 第二层：机会校准

输入：第一层已经识别出的单个机会、证据、反证和未知项。第二层不重新读取全量评论，也不重新发明机会。

服务端系统提示词要求：

- 给出“建议投入 / 有条件投入 / 先补证据 / 暂不投入”的结论。
- 解释支持证据、反证和不能由当前数据证明的部分。
- 生成可落地但仍需验证的产品概念，不把评论愿望直接当成购买意愿。
- 每个概念必须包含场景、形态、核心承诺、推导、风险和最便宜的验证动作。
- 给出进入产品决策台前必须回答的审核问题。

## 前端调用关系

```text
真实评论数据
    │
    ▼
/api/opportunity/cluster  ── 一次模型调用 ──> 需求机会卡 / 雷达气泡
    │
    ▼ 用户点击“进入机会校准”
/api/opportunity/judge    ── 一次模型调用 ──> 投入结论 / 概念方向 / 审核问题
    │
    ▼
主工作台的产品决策台
```

当前 `prototype.html` 只负责展示和交互，不保存 API Key，也不包含固定产品机会模板。第一层缓存带有 `CLUSTER_PROMPT_VERSION`，提示词版本变化时不会错误复用旧结果。

## 合并到主工作台的边界

合并时只需要保留：

1. `opportunity-radar/prototype.html` 的两层页面和交互。
2. `opportunity-radar/opportunity_ai_server.py` 的两个分析接口。
3. `data/eye-care-opportunities/` 中与机会分析相关的清洗数据和分析缓存。
4. `go('strategy')` 的 `postMessage` 数据桥，把第二层结论和证据传给主工作台产品决策台。

不要把 API Key、DeepSeek 中转密钥、临时测试图片或其他模块的本地改动一起合并。

## 配置

```bash
DEEPSEEK_API_KEY="本机环境变量中的密钥" \
DEEPSEEK_BASE_URL="https://api.deepseek.com/v1" \
DEEPSEEK_MODEL="deepseek-chat" \
python3 opportunity-radar/opportunity_ai_server.py
```

生图接口是独立的可选能力，使用 `TIKBIT_API_KEY` 和 4182 端口，不参与两层机会判断。
