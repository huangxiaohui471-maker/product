#!/usr/bin/env python3
"""Local two-stage AI gateway for the opportunity radar.

The browser sends cleaned comment records here. This process keeps the API key
server-side and makes exactly one model call for each analysis stage:
  POST /api/opportunity/cluster -> semantic demand discovery
  POST /api/opportunity/judge   -> investment decision for one opportunity

Run with the official DeepSeek API (the browser never receives the key):
  DEEPSEEK_BASE_URL=https://api.deepseek.com/v1 \
  DEEPSEEK_API_KEY=... DEEPSEEK_MODEL=deepseek-chat \
  python3 opportunity-radar/opportunity_ai_server.py

The optional image smoke test runs on a separate local port so it does not
interrupt the existing opportunity-analysis service:
  TIKBIT_API_KEY=... OPPORTUNITY_AI_PORT=4182 \
  python3 opportunity-radar/opportunity_ai_server.py
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HOST = os.getenv("OPPORTUNITY_AI_HOST", "127.0.0.1")
PORT = int(os.getenv("OPPORTUNITY_AI_PORT", "4179"))
PROVIDER = "deepseek"
API_KEY = (
    os.getenv("DEEPSEEK_API_KEY", "").strip()
)
BASE_URL = (
    os.getenv("DEEPSEEK_BASE_URL", "").strip()
    or "https://api.deepseek.com/v1"
).rstrip("/")
MODEL = (
    os.getenv("DEEPSEEK_MODEL", "").strip()
    or os.getenv("OPPORTUNITY_MODEL", "").strip()
    or "deepseek-chat"
)
API_STYLE = os.getenv("OPPORTUNITY_API_STYLE", "chat_completions").strip().lower()
IMAGE_API_KEY = os.getenv("TIKBIT_API_KEY", "").strip() or os.getenv("IMAGE_API_KEY", "").strip()
IMAGE_BASE_URL = os.getenv("TIKBIT_BASE_URL", "https://tikbit.ai").strip().rstrip("/")
IMAGE_MODEL = os.getenv("TIKBIT_IMAGE_MODEL", "gpt-image-2.5-sunburst").strip()
IMAGE_USER_AGENT = os.getenv(
    "TIKBIT_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
)


CLUSTER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "clusters": {
            "type": "array",
            "minItems": 3,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "keyword": {"type": "string"},
                    "title": {"type": "string"},
                    "product_need": {"type": "string"},
                    "actual_need": {"type": "string"},
                    "user_need": {"type": "string"},
                    "trigger_context": {"type": "string"},
                    "evidence_summary": {"type": "string"},
                    "behavior_evidence": {"type": "string"},
                    "existing_solutions": {"type": "string"},
                    "counter_evidence": {"type": "string"},
                    "unknown": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["高", "中", "低"]},
                    "recommendation": {"type": "string", "enum": ["优先判断", "补证后判断", "持续观察"]},
                    "analytics": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "total": {"type": "integer", "minimum": 0},
                            "xhs": {"type": "integer", "minimum": 0},
                            "tb": {"type": "integer", "minimum": 0},
                            "pain": {"type": "integer", "minimum": 0},
                            "products": {"type": "integer", "minimum": 0},
                        },
                        "required": ["total", "xhs", "tb", "pain", "products"],
                    },
                    "evidence": {
                        "type": "array",
                        "maxItems": 5,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "record_id": {"type": "string"},
                                "source": {"type": "string"},
                                "quote": {"type": "string"},
                            },
                            "required": ["record_id", "source", "quote"],
                        },
                    },
                },
                "required": [
                    "id", "keyword", "title", "product_need", "actual_need", "user_need", "trigger_context", "evidence_summary",
                    "behavior_evidence", "existing_solutions", "counter_evidence", "unknown",
                    "confidence", "recommendation", "analytics", "evidence",
                ],
            },
        },
    },
    "required": ["summary", "clusters"],
}


JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": ["建议投入", "有条件投入", "先补证据", "暂不投入"]},
        "verdict_text": {"type": "string"},
        "core_question": {"type": "string"},
        "inference": {"type": "string"},
        "support": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
        "counter": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
        "unknown": {"type": "string"},
        "next_experiment": {"type": "string"},
        "market_assessment": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "level": {"type": "string", "enum": ["大", "中", "小", "待补证"]},
                "score": {"type": "string"},
                "evidence": {"type": "string"},
                "confidence": {"type": "string", "enum": ["高", "中", "低"]},
                "rationale": {"type": "string"},
            },
            "required": ["level", "score", "evidence", "confidence", "rationale"],
        },
        "concepts": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "track": {"type": "string"},
                    "scene": {"type": "string"},
                    "form": {"type": "string"},
                    "promise": {"type": "string"},
                    "rationale": {"type": "string"},
                    "risk": {"type": "string"},
                    "test": {"type": "string"},
                },
                "required": ["name", "track", "scene", "form", "promise", "rationale", "risk", "test"],
            },
        },
        "gates": {
            "type": "array",
            "minItems": 4,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["question", "answer", "status"],
            },
        },
    },
    "required": [
        "verdict", "verdict_text", "core_question", "inference", "support", "counter",
        "unknown", "next_experiment", "market_assessment", "concepts", "gates",
    ],
}


def json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


def schema_outline(schema: dict[str, Any]) -> Any:
    properties = schema.get("properties") or {}
    outline: dict[str, Any] = {}
    for name, item in properties.items():
        kind = item.get("type")
        if kind == "object":
            outline[name] = schema_outline(item)
        elif kind == "array":
            outline[name] = [schema_outline(item.get("items") or {})] if (item.get("items") or {}).get("type") == "object" else []
        else:
            outline[name] = kind or "string"
    return outline


def _text(value: Any) -> str:
    return str(value or "").strip()


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def cluster_quality_issues(result: dict[str, Any]) -> list[str]:
    """Cheap deterministic checks for the first pass.

    These checks are deliberately conservative: they do not replace the model,
    but catch the failure modes that make a demand summary unusable in the UI.
    """
    issues: list[str] = []
    clusters = result.get("clusters") if isinstance(result, dict) else None
    if not isinstance(clusters, list) or not 3 <= len(clusters) <= 5:
        issues.append("需求机会必须有 3 到 5 条，且不能用空数组占位")
        return issues
    titles: set[str] = set()
    symptom_only = ("黑眼圈", "浮肿", "敏感", "脂肪粒", "干燥", "痘痘", "清洁", "假滑")
    for index, cluster in enumerate(clusters, 1):
        if not isinstance(cluster, dict):
            issues.append(f"第 {index} 条需求机会不是对象")
            continue
        title = _text(cluster.get("title"))
        if not title:
            issues.append(f"第 {index} 条缺少面向决策的机会标题")
        if title and title in titles:
            issues.append(f"第 {index} 条与其他机会标题重复")
        titles.add(title)
        if title and title in symptom_only:
            issues.append(f"第 {index} 条标题仍是症状标签，必须写成用户任务或产品缺口")
        product_need = _text(cluster.get("product_need"))
        if not product_need or not _has_any(product_need, ("希望", "需要", "想要")):
            issues.append(f"第 {index} 条没有明确写出用户希望得到的产品/服务")
        actual_need = _text(cluster.get("actual_need"))
        if len(actual_need) < 12 or len(actual_need) > 60:
            issues.append(f"第 {index} 条 actual_need 过短或过长，需压缩为一句可读总结")
        if not isinstance(cluster.get("evidence"), list) or not cluster.get("evidence"):
            issues.append(f"第 {index} 条没有可追溯证据")
        analytics = cluster.get("analytics") if isinstance(cluster.get("analytics"), dict) else {}
        if any(not isinstance(analytics.get(key), int) for key in ("total", "xhs", "tb", "pain", "products")):
            issues.append(f"第 {index} 条来源统计不是整数")
    return issues[:8]


def judgement_quality_issues(result: dict[str, Any], context: str = "") -> list[str]:
    """Self-review the concept output before it reaches the product workflow."""
    issues: list[str] = []
    if not isinstance(result, dict):
        return ["第二层没有返回对象"]
    concepts = result.get("concepts")
    if not isinstance(concepts, list) or not 2 <= len(concepts) <= 4:
        issues.append("必须输出 2 到 4 个真正不同的概念方向")
        concepts = concepts if isinstance(concepts, list) else []
    names: set[str] = set()
    unsupported_claims = ("根治", "彻底消除", "100%", "绝对不会", "保证有效", "立刻治愈")
    actionable_words = ("招募", "访谈", "试用", "对照", "记录", "落地页", "点击", "留资", "复购", "支付", "样本")
    for index, concept in enumerate(concepts, 1):
        if not isinstance(concept, dict):
            issues.append(f"第 {index} 个概念不是对象")
            continue
        name = _text(concept.get("name"))
        if not name:
            issues.append(f"第 {index} 个概念没有名称")
        normalized_name = name.replace(" ", "").lower()
        if normalized_name in names:
            issues.append(f"第 {index} 个概念与前面重复，必须改变解决路径或形态")
        names.add(normalized_name)
        for field, limit in (("name", 24), ("promise", 80), ("rationale", 180), ("risk", 120), ("test", 180)):
            value = _text(concept.get(field))
            if not value:
                issues.append(f"第 {index} 个概念缺少 {field}")
            elif len(value) > limit:
                issues.append(f"第 {index} 个概念的 {field} 太长，需压缩到 {limit} 字以内")
            if field in ("promise", "rationale") and _has_any(value, unsupported_claims):
                issues.append(f"第 {index} 个概念含有未经证实的绝对功效表述")
        test = _text(concept.get("test"))
        if test and not _has_any(test, actionable_words):
            issues.append(f"第 {index} 个概念的验证动作缺少样本、行为或通过标准")
    gates = result.get("gates")
    if not isinstance(gates, list) or len(gates) < 4:
        issues.append("审核问题至少要覆盖 4 个维度，不能只给 2 到 3 条")
    market = result.get("market_assessment") if isinstance(result.get("market_assessment"), dict) else {}
    market_text = context.lower()
    has_denominator = _has_any(market_text, ("gmv", "份额", "市场规模", "分母", "可比样本"))
    if not has_denominator and (_text(market.get("level")) != "待补证" or _text(market.get("score")) not in ("", "—")):
        issues.append("输入没有同口径市场分母时，市场评估必须标为待补证，不能猜规模")
    return issues[:10]


def call_quality_checked(
    system_prompt: str,
    user_prompt: str,
    schema_name: str,
    schema: dict[str, Any],
    stage: str,
) -> dict[str, Any]:
    """Run one model pass, then at most one targeted revision pass.

    This is the stopping rule for language quality: never loop indefinitely;
    keep the best available structured result after one correction round.
    """
    result = call_model(system_prompt, user_prompt, schema_name, schema)
    context = user_prompt
    issues = cluster_quality_issues(result) if stage == "cluster" else judgement_quality_issues(result, context)
    if not issues:
        return result
    feedback = "\n".join(f"- {issue}" for issue in issues)
    revision_prompt = (
        user_prompt
        + "\n\n【第一版自审未通过】\n"
        + feedback
        + "\n请重新生成一份完整 JSON，不要解释修改过程；逐条修正以上问题，并再次检查证据、逻辑和可执行性。"
        + "\n第一版草稿如下：\n"
        + json.dumps(result, ensure_ascii=False)
    )
    revised_system = system_prompt + "\n你现在处于第二遍编辑：宁可减少空泛结论，也不能补写输入中没有的事实。"
    revised = call_model(revised_system, revision_prompt, schema_name, schema)
    revised_issues = cluster_quality_issues(revised) if stage == "cluster" else judgement_quality_issues(revised, context)
    if revised_issues:
        print(f"[opportunity-ai] {stage} 二次修订后仍有质量提示：{'；'.join(revised_issues)}")
    return revised


def call_model(system_prompt: str, user_prompt: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
    if not API_KEY:
        raise RuntimeError("未配置 DeepSeek API 密钥。请通过 DEEPSEEK_API_KEY 提供。")
    contract = json.dumps(schema_outline(schema), ensure_ascii=False)
    system = (
        system_prompt
        + "\n只返回一个合法 JSON 对象，不要 Markdown、解释文字或代码围栏。"
        + f"输出契约（字段不可改名）：{contract}"
    )
    if API_STYLE == "responses":
        payload = {
            "model": MODEL,
            "store": False,
            "max_output_tokens": 5000,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "text": {"format": {"type": "json_schema", "name": schema_name, "strict": True, "schema": schema}},
        }
        endpoint = f"{BASE_URL}/responses"
    else:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 5000,
            "response_format": {"type": "json_object"},
        }
        endpoint = f"{BASE_URL}/chat/completions"
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        error.read()
        if error.code in (401, 403):
            raise RuntimeError("DeepSeek 官方 API 认证失败，请检查 DEEPSEEK_API_KEY。") from error
        raise RuntimeError(f"DeepSeek 官方 API 暂时不可用（HTTP {error.code}）。") from error
    except URLError as error:
        raise RuntimeError(f"无法连接 DeepSeek 官方 API：{error.reason}") from error
    text = response_text(result)
    if not text:
        raise RuntimeError("模型没有返回结构化结果。")
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError("模型返回不是有效 JSON。") from error


def call_tikbit_image(prompt: str) -> dict[str, str]:
    """Call the image provider without exposing its API key to the browser."""
    if not IMAGE_API_KEY:
        raise RuntimeError("未配置 TIKBIT_API_KEY。请通过环境变量提供生图服务密钥。")
    clean_prompt = str(prompt or "").strip()[:2000]
    if not clean_prompt:
        raise RuntimeError("生图提示词不能为空。")
    payload = {
        "model": IMAGE_MODEL,
        "prompt": clean_prompt,
        "n": 1,
        "size": "1024x1024",
    }
    request = Request(
        f"{IMAGE_BASE_URL}/v1/images/generations",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {IMAGE_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": IMAGE_USER_AGENT,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        error.read()
        if error.code in (401, 403):
            raise RuntimeError("生图服务认证失败，请检查 TIKBIT_API_KEY。") from error
        raise RuntimeError(f"生图服务暂时不可用（HTTP {error.code}）。") from error
    except URLError as error:
        raise RuntimeError(f"无法连接生图服务：{error.reason}") from error
    items = result.get("data") or []
    if not items or not isinstance(items[0], dict):
        raise RuntimeError("生图服务没有返回图片。")
    item = items[0]
    if item.get("b64_json"):
        return {"mime_type": "image/png", "b64_json": str(item["b64_json"])}
    if item.get("url"):
        return {"url": str(item["url"])}
    raise RuntimeError("生图服务返回中没有 b64_json 或 url。")


def compact_records(data: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for source_key, source_name in (("xhs", "小红书评论"), ("xhsPosts", "小红书帖子"), ("tb", "淘宝/天猫"), ("negative", "淘宝/天猫负面"), ("demands", "淘宝/天猫需求")):
        for index, row in enumerate(data.get(source_key, []) or []):
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or row.get("content") or row.get("full") or row.get("title") or "").strip()
            if not text:
                continue
            records.append({
                "id": str(row.get("id") or f"{source_key}-{index + 1}"),
                "source": source_name,
                "item": str(row.get("item_name") or row.get("商品名称") or ""),
                "text": text[:700],
            })
    return records


def cluster_prompt(data: dict[str, Any]) -> str:
    records = compact_records(data)
    dataset = data.get("dataset") if isinstance(data.get("dataset"), dict) else {}
    source_counts = {
        "小红书": sum(1 for record in records if record["source"] in ("小红书评论", "小红书帖子")),
        "淘宝/天猫": sum(1 for record in records if record["source"] in ("淘宝/天猫", "淘宝/天猫负面", "淘宝/天猫需求")),
    }
    return json.dumps({
        "任务": "从以下真实的小红书帖子/评论与淘宝/天猫评论中做需求语义聚类",
        "数据集": {"key": dataset.get("key", ""), "label": dataset.get("label", ""), "prompt_version": dataset.get("promptVersion", "")},
        "记录数": len(records),
        "来源记录数": source_counts,
        "records": records,
    }, ensure_ascii=False)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[opportunity-ai] {self.address_string()} {fmt % args}")

    def do_OPTIONS(self) -> None:
        json_response(self, {}, 204)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            json_response(self, {"ok": True, "configured": bool(API_KEY), "provider": PROVIDER, "model": MODEL, "base_url": BASE_URL, "api_style": API_STYLE, "image_configured": bool(IMAGE_API_KEY), "image_model": IMAGE_MODEL})
        else:
            json_response(self, {"error": "not_found"}, 404)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 3_000_000:
            raise ValueError("请求数据过大")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_POST(self) -> None:
        try:
            body = self.read_json()
            if self.path == "/api/opportunity/cluster":
                call_quality_checked(
                    """
你是严谨的消费者需求研究员，负责把真实用户原文整理成可供产品经理决策的需求机会。

工作顺序：
1. 先按“用户要完成的任务 + 发生场景 + 当前障碍 + 期待结果”聚类，不按症状词频机械分组。
2. 每个机会都要经过“原文证据 → 用户任务 → 产品缺口”的推理链；只把输入记录能支持的内容写成结论。
3. 反证必须保留：如果评论只是抱怨、询问或表达愿望，不能升级成购买意愿、普遍需求或功效证明。
4. 自审一遍：机会之间不能只是换词；如果两组用户任务、场景和障碍相同，应合并，空出名额给真正不同的机会。

字段规则：
- keyword：2 到 8 个汉字的痛点标签，只给雷达图用。
- title：面向产品决策的机会标题，必须包含任务或缺口，不能只写“黑眼圈/浮肿/敏感/清洁”等症状。
- product_need：必须以“希望有一款/希望有一种/需要一种”开头，写清产品或服务形态、使用约束和期待结果；不要直接写成具体品牌或未经证实的成分方案。
- actual_need：15 到 40 字，一句话说清用户要完成什么购买或使用任务。
- user_need：比 actual_need 更短，但不能退化成症状词。
- trigger_context：只写输入中出现的触发场景。
- evidence_summary、behavior_evidence、existing_solutions、counter_evidence、unknown：分别写证据、已发生行为、现有解法、反证和最大未知，不能互相重复。
- evidence：每条必须引用给定 record_id、来源和原文短引；不能编造 record_id。
- analytics：只统计输入记录，total 应与 xhs + tb 的来源口径一致，不能估算。

语言要求：短句、具体、少形容词。不要使用“赋能、闭环、全方位、精准解决、重新定义”等空泛词。当前数据集名称只用于区分品类，不得把其他品类经验混入结论。
                    """,
                    cluster_prompt(body.get("data") or {}),
                    "opportunity_clusters",
                    CLUSTER_SCHEMA,
                    "cluster",
                )
                json_response(self, result)
                return
            if self.path == "/api/opportunity/judge":
                opportunity = body.get("opportunity") or {}
                evidence = body.get("evidence") or {}
                prompt = json.dumps({"机会": opportunity, "第一层证据": evidence}, ensure_ascii=False)
                result = call_quality_checked(
                    """
你是产品投资评审与概念策略顾问。你的任务不是写漂亮文案，而是把一条真实需求变成可比较、可验证、可继续执行的产品方向。

请按以下顺序推理：
1. 先用一句话界定核心问题：用户在什么场景下，因什么障碍，想完成什么任务。
2. 再拆支持证据、反证和未知项，明确哪些来自原文，哪些仍未被证明。
3. 给出投入判断，但把它当作风险提示，不得把评论愿望当成购买意愿，也不得把评论条数当成市场规模。
4. 生成 2 到 4 个真正不同的概念方向。差异必须来自解决路径、使用时机、产品形态或服务方式，不能只是“精华/眼霜/眼油”换名。
5. 对每个方向做一次自审：它是否回到真实用户任务？是否使用了输入中不存在的成分、功效、价格或市场事实？是否有明确的最小验证动作？不合格就重写，不要把问题留给页面。

概念字段规则：
- name：16 个汉字以内，像产品方向，不写广告口号。
- track：短标签，说明解决路径或形态。
- scene：具体到使用时机、触发场景和用户状态，避免“日常使用”这种空话。
- form：写清产品/服务形态、关键交互或使用方式；只有输入明确提到某成分时才可写成分，否则写质地、剂型、流程或工具形态。
- promise：一句可验证的用户结果，不使用“根治、保证、100%、立刻治愈、完全不会”等绝对功效。
- rationale：说明“哪条证据支持这个方向、它填补了什么缺口”，尽量引用输入中的 record_id 或来源，不得编造研究结论。
- risk：至少写一个可能推翻方向的风险或反证。
- test：必须是 7 到 14 天内可执行的最小验证，写清对象数量/样本、要观察的行为、通过或失败标准；不要只写“收集反馈”。

市场评估规则：只能使用输入中存在的同口径市场规模、GMV、份额分母或可比样本证据。没有分母时 level 必须为“待补证”、score 必须为“—”，不得用评论条数或常识猜市场大小。

gates 只用于页面展示证据检查项，不是页面流转权限；必须至少覆盖：证据可追溯、用户任务清晰度、支付/购买行为、市场分母、差异化/商业空间和下一步验证路径。最终输出前再检查：概念之间有差异、语言具体、每个结论都有来源或明确标注未知。
                    """,
                    prompt,
                    "opportunity_judgement",
                    JUDGE_SCHEMA,
                    "judge",
                )
                json_response(self, result)
                return
            if self.path == "/api/opportunity/image":
                prompt = body.get("prompt") or "a clean, premium cosmetic product concept render for a new skincare opportunity, neutral studio background, no text, no logo"
                image = call_tikbit_image(prompt)
                json_response(self, {"model": IMAGE_MODEL, **image})
                return
            json_response(self, {"error": "not_found"}, 404)
        except Exception as error:  # noqa: BLE001 - surface a safe local error to the UI
            json_response(self, {"error": str(error)}, 500)


if __name__ == "__main__":
    print(f"Opportunity AI server listening on http://{HOST}:{PORT} (model={MODEL})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
