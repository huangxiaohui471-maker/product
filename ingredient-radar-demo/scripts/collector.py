#!/usr/bin/env python3
"""每日成分线索采集器（Demo）。

它只保存“线索”，不会把抓到的文本直接当成事实：
1. 请求配置中的平台页面；
2. 从 HTML/JSON-LD 文本中识别成分名；
3. 与历史快照去重，按国家选出 1 条今日候选；
4. 写入 data/latest.json，供 Demo 前端读取。

FastMoss/TikTok 页面若需要登录或由 JS 动态渲染，脚本会记录失败原因，
不会伪造数据。后续可把 source.url 替换为公司已授权的导出/API 地址。
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "sources.json"
HISTORY = DATA / "history.json"
LATEST = DATA / "latest.json"
LOG = ROOT / "logs" / "collector.log"

DEFAULT_INGREDIENTS = [
    "烟酰胺", "神经酰胺", "视黄醇", "胜肽", "玻色因", "依克多因", "水杨酸",
    "胶原蛋白", "积雪草", "泛醇", "谷胱甘肽", "玻尿酸", "咖啡因", "传明酸",
    "腺苷", "角鲨烷", "麦角硫因", "发酵滤液", "茶多酚", "维生素C",
    "海茴香提取物", "雪绒花发酵物", "藻蓝蛋白", "白睡莲提取物", "米糠发酵物",
]


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def now_local() -> datetime:
    return datetime.now().astimezone()


def write_log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{now_local().isoformat(timespec='seconds')} {message}\n"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line)
    print(line, end="")


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def fetch(url: str, timeout: int = 25) -> tuple[str, str | None]:
    req = Request(url, headers={
        "User-Agent": "IngredientRadarDemo/0.1 (+authorized internal research)",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace"), None
    except HTTPError as exc:
        return "", f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError) as exc:
        return "", str(exc)


def extract_text(document: str) -> str:
    parser = VisibleText()
    parser.feed(document)
    visible = " ".join(parser.parts)
    # JSON-LD、meta 描述中的商品卖点也作为弱信号，但不提升可信度。
    meta = " ".join(re.findall(r'<meta[^>]+(?:content|name)=["\']([^"\']+)', document, re.I))
    return html.unescape(f"{visible} {meta}")


def detect(text: str, vocabulary: list[str]) -> dict[str, int]:
    return {name: len(re.findall(re.escape(name), text, re.I)) for name in vocabulary if re.search(re.escape(name), text, re.I)}


def choose_candidate(counts: dict[str, int], previous: dict[str, int]) -> tuple[str | None, str]:
    if not counts:
        return None, "no_ingredient_signal"
    ranked = sorted(counts.items(), key=lambda item: (item[1] - previous.get(item[0], 0), item[1]), reverse=True)
    name, today_count = ranked[0]
    before = previous.get(name, 0)
    if before == 0:
        signal = "首次出现"
    elif today_count > before:
        signal = "快速增长"
    else:
        signal = "持续出现"
    return name, signal


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    sources = load_json(CONFIG, [])
    history = load_json(HISTORY, {"days": {}})
    today = now_local().date().isoformat()
    day_counts: dict[str, dict[str, int]] = {}
    results: list[dict] = []
    errors: list[dict] = []
    vocabulary = list(dict.fromkeys(DEFAULT_INGREDIENTS + [x for s in sources for x in s.get("ingredients", [])]))

    for source in sources:
        market = source.get("market", "未标注")
        name = source.get("name", "未命名来源")
        url = source.get("url", "")
        if not url:
            errors.append({"source": name, "error": "missing_url"})
            continue
        document, error = fetch(url)
        if error:
            write_log(f"{name} ({market}) failed: {error}")
            errors.append({"source": name, "market": market, "url": url, "error": error})
            continue
        counts = detect(extract_text(document), vocabulary)
        bucket = day_counts.setdefault(market, {})
        for ingredient, count in counts.items():
            bucket[ingredient] = bucket.get(ingredient, 0) + count
        write_log(f"{name} ({market}) fetched; signals={len(counts)}")

    previous_days = history.get("days", {})
    previous = previous_days.get(sorted(previous_days)[-1], {}) if previous_days else {}
    for market in sorted({s.get("market", "未标注") for s in sources}):
        counts = day_counts.get(market, {})
        prev_counts = previous.get(market, {}) if isinstance(previous, dict) else {}
        ingredient, signal = choose_candidate(counts, prev_counts)
        if ingredient:
            total = counts[ingredient]
            results.append({
                "name": ingredient,
                "market": market,
                "signal": signal,
                "evidence": f"{total} 次文本命中 · {len(counts)} 个成分信号",
                "confidence": "待核验",
                "source": next((s.get("name") for s in sources if s.get("market") == market), "平台页面"),
            })
        else:
            results.append({"market": market, "name": None, "signal": "暂无可验证线索", "evidence": "页面未返回可解析的成分文本", "confidence": "不可判定"})

    history.setdefault("days", {})[today] = day_counts
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "generated_at": now_local().isoformat(timespec="seconds"),
        "scheduled_time": "09:30",
        "status": "ok" if not errors else "partial",
        "new_ingredients": results,
        "errors": errors,
        "note": "抓取结果仅为线索；页面需登录或改为授权 API 时，错误会保留在 errors 中。",
    }
    LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_log(f"completed status={payload['status']} markets={len(results)} errors={len(errors)}")
    return 0 if results else 2


if __name__ == "__main__":
    sys.exit(main())
