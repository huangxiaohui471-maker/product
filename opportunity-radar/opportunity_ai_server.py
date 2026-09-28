#!/usr/bin/env python3
"""Local two-stage AI gateway for the opportunity radar.

The browser sends cleaned comment records here. This process keeps the API key
server-side and makes exactly one model call for each analysis stage:
  POST /api/opportunity/cluster -> semantic demand discovery
  POST /api/opportunity/judge   -> investment decision for one opportunity

Run with a DeepSeek-compatible relay (the browser never receives the key):
  OPPORTUNITY_RELAY_BASE_URL=https://your-relay.example/v1 \
  DEEPSEEK_API_KEY=... DEEPSEEK_MODEL=deepseek-chat \
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
    or os.getenv("OPPORTUNITY_RELAY_API_KEY", "").strip()
    or os.getenv("OPENAI_API_KEY", "").strip()
)
BASE_URL = (
    os.getenv("OPPORTUNITY_RELAY_BASE_URL", "").strip()
    or os.getenv("DEEPSEEK_BASE_URL", "").strip()
    or os.getenv("OPENAI_BASE_URL", "").strip()
    or "https://api.deepseek.com/v1"
).rstrip("/")
MODEL = (
    os.getenv("DEEPSEEK_MODEL", "").strip()
    or os.getenv("OPPORTUNITY_MODEL", "").strip()
    or "deepseek-chat"
)
API_STYLE = os.getenv("OPPORTUNITY_API_STYLE", "chat_completions").strip().lower()


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
                    "id", "keyword", "title", "actual_need", "user_need", "trigger_context", "evidence_summary",
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
            "minItems": 3,
            "maxItems": 5,
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
        "unknown", "next_experiment", "concepts", "gates",
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


def call_model(system_prompt: str, user_prompt: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
    if not API_KEY:
        raise RuntimeError("未配置 DeepSeek API 密钥。请通过 DEEPSEEK_API_KEY 或中转站环境变量提供。")
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
            raise RuntimeError("DeepSeek 中转服务认证失败，请检查 API 密钥。") from error
        raise RuntimeError(f"AI 服务暂时不可用（HTTP {error.code}）。") from error
    except URLError as error:
        raise RuntimeError(f"无法连接 DeepSeek 中转服务：{error.reason}") from error
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
    return json.dumps({"任务": "从以下真实的小红书帖子/评论与淘宝/天猫评论中做需求语义聚类", "记录数": len(records), "records": records}, ensure_ascii=False)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[opportunity-ai] {self.address_string()} {fmt % args}")

    def do_OPTIONS(self) -> None:
        json_response(self, {}, 204)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            json_response(self, {"ok": True, "configured": bool(API_KEY), "provider": PROVIDER, "model": MODEL, "base_url": BASE_URL, "api_style": API_STYLE})
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
                result = call_model(
                    "你是严谨的消费者需求研究员。只能根据给定的小红书帖子/评论和淘宝/天猫评论判断，不得把关键词频次直接当成需求强度。请把相似表达按真实用户任务、场景和障碍聚成 3 到 5 个需求机会；保留反证，不发明未出现的用户行为。每条证据必须引用给定 record_id。每个机会必须提供 keyword：2 到 8 个汉字，或两个很短的词用“/”连接，专门作为图表标签，不能写完整句子。请另外提供 actual_need：用你自己的语言，把用户正在抱怨什么、遇到什么障碍、希望得到什么结果总结成一句 15 到 35 字的话；不要复述单条评论，不要写成产品名、成分名或功能方案。不要输出产品名称或固定模板，第一层只发现机会。analytics.xhs 统计小红书帖子与评论，analytics.tb 统计淘宝/天猫记录。",
                    cluster_prompt(body.get("data") or {}),
                    "opportunity_clusters",
                    CLUSTER_SCHEMA,
                )
                json_response(self, result)
                return
            if self.path == "/api/opportunity/judge":
                opportunity = body.get("opportunity") or {}
                evidence = body.get("evidence") or {}
                prompt = json.dumps({"机会": opportunity, "第一层证据": evidence}, ensure_ascii=False)
                result = call_model(
                    "你是产品投资评审与概念策略顾问。只能依据第一层已经识别的机会和证据做判断，不得把评论中的愿望直接当成购买意愿。请给出是否投入的结论，并生成可落地但仍需验证的产品概念。概念必须回应用户场景、使用障碍和现有解法缺口；明确风险、反证和最便宜的下一步。不要声称已经证明功效或市场规模。",
                    prompt,
                    "opportunity_judgement",
                    JUDGE_SCHEMA,
                )
                json_response(self, result)
                return
            json_response(self, {"error": "not_found"}, 404)
        except Exception as error:  # noqa: BLE001 - surface a safe local error to the UI
            json_response(self, {"error": str(error)}, 500)


if __name__ == "__main__":
    print(f"Opportunity AI server listening on http://{HOST}:{PORT} (model={MODEL})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
