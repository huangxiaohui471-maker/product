from __future__ import annotations

import json
import os
import ssl
try:
    import certifi
except ImportError:
    certifi = None
import time, random
import re
from urllib.error import HTTPError, URLError
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen,build_opener,ProxyHandler,HTTPSHandler


USER_AGENT = "PerformanceCreativeIntelligence/0.1"
CONFIG = Path.home() / ".config" / "content-creative-intelligence" / "tikhub.json"
LEGACY_CONFIG = Path.home() / ".xiaohongshu" / "tikhub_config.json"


def token() -> str:
    value = os.environ.get("TIKHUB_API_TOKEN", "").strip()
    if value:
        return value
    for path in (CONFIG, LEGACY_CONFIG):
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            value=str(payload.get("api_token") or payload.get("tikhub_api_token") or "").strip()
            if value:return value
    return ""


def base_url() -> str:
    return os.environ.get("TIKHUB_BASE_URL", "https://api.tikhub.io").rstrip("/")


class ConnectorError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message); self.code=code; self.retryable=retryable


def request(path: str, params: dict[str, Any] | None = None, method: str = "GET", body: Any = None) -> dict:
    api_token = token()
    if not api_token:
        raise RuntimeError("缺少 TikHub 凭据；设置 TIKHUB_API_TOKEN 或配置用户级凭据")
    url = f"{base_url()}{path}"
    if params:
        url += "?" + urlencode(params)
    data = None if method == "GET" else json.dumps({} if body is None else body).encode("utf-8")
    req = Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {api_token}", "Accept": "application/json",
        "Content-Type": "application/json", "User-Agent": USER_AGENT,
    })
    context=ssl.create_default_context(cafile=certifi.where() if certifi else None)
    direct=build_opener(ProxyHandler({}),HTTPSHandler(context=context))
    for attempt in range(3):
        try:
            with urlopen(req, timeout=90, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            code=error.code
            if code in (401,403): raise ConnectorError("authorization",f"TikHub 授权失败 HTTP {code}") from error
            if code==402: raise ConnectorError("insufficient_balance","TikHub 余额不足 HTTP 402") from error
            if code==404: raise ConnectorError("endpoint_version","TikHub 端点不存在 HTTP 404") from error
            if code==429 or code>=500:
                if attempt<2: time.sleep((2**attempt)+random.random());continue
                raise ConnectorError("transient_exhausted",f"TikHub 临时错误重试耗尽 HTTP {code}",True) from error
            raise ConnectorError("http_error",f"TikHub HTTP {code}") from error
        except (URLError,TimeoutError) as error:
            # A learner's stale local proxy must not make TikHub look down.
            # When the configured proxy actively refuses the connection, retry
            # the same request once via a direct opener before normal backoff.
            try:
                with direct.open(req,timeout=90) as response:return json.loads(response.read().decode("utf-8"))
            except Exception:pass
            if attempt<2: time.sleep((2**attempt)+random.random());continue
            raise ConnectorError("network_exhausted","TikHub 网络错误重试耗尽",True) from error
    raise ConnectorError("unknown","TikHub 未知连接器错误")


def search_douyin(keyword: str, days: int = 7, limit: int = 20) -> list[dict[str, Any]]:
    date_type = 3 if days <= 3 else 7 if days <= 7 else 30
    payload = request("/api/v1/douyin/index/fetch_item_query", {
        "query": keyword, "category_id": "0", "date_type": date_type,
        "label_type": 0, "duration_type": 0,
    }, method="POST")
    data = payload.get("data") or {}
    rows = data.get("data") if isinstance(data, dict) else data
    normalized = []
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("itemId") or item.get("item_id") or "").strip()
        if not item_id:
            continue
        normalized.append({
            "creative_id": f"douyin:{item_id}", "platform": "douyin",
            "canonical_url": item.get("url") or f"https://www.douyin.com/video/{item_id}",
            "title": str(item.get("title") or item.get("itemTitle") or "").strip(),
            "author_name": str(item.get("nickname") or "").strip(),
            "published_at": item.get("createTime") or item.get("create_time"),
            "search_metrics": {"likes": item.get("likes")},
            "search_flags": {
                "low_fans_hot": bool(item.get("isLowFansButHot")),
                "high_completion": bool(item.get("isHighPlayOverRate")),
                "high_fan_growth": bool(item.get("isHighFansRiseRate")),
                "high_like_rate": bool(item.get("isHighLikeRate")),
            },
        })
    return normalized[:max(1, limit)]


def _detail(payload:dict[str,Any])->dict[str,Any]:
    data=payload.get("data") or {}
    if not isinstance(data,dict):return {}
    return data.get("aweme_detail") or data.get("aweme") or (data if data.get("aweme_id") else {})

def detail_by_url(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    match=re.search(r"(?:video/|modal_id=)(\d{10,})",url);aweme_id=match.group(1) if match else ""
    routes=[("share_url","/api/v1/douyin/web/fetch_one_video_by_share_url",{"share_url":url})]
    if aweme_id:
        # TikHub's own current docs tell clients to fall back between Web V1,
        # Web V2 and APP when one detail route is unstable.
        routes.extend([
            ("web_v2","/api/v1/douyin/web/fetch_one_video_v2",{"aweme_id":aweme_id}),
            ("web_v1","/api/v1/douyin/web/fetch_one_video",{"aweme_id":aweme_id,"need_anchor_info":False}),
            ("app_v3","/api/v1/douyin/app/v3/fetch_one_video",{"aweme_id":aweme_id}),
        ])
    failures=[];payload={};detail={};route=""
    for name,path,params in routes:
        try:
            candidate=request(path,params);candidate_detail=_detail(candidate)
            if not candidate_detail:raise RuntimeError("作品详情为空")
            payload,detail,route=candidate,candidate_detail,name;break
        except ConnectorError as error:
            if error.code in {"authorization","insufficient_balance"}:raise
            failures.append(f"{name}:{error.code}")
        except RuntimeError:failures.append(f"{name}:empty")
    if not detail:
        raise RuntimeError("TikHub 多路详情均不可用："+", ".join(failures))
    stats = detail.get("statistics") or {}
    author = detail.get("author") or {}
    item_id = str(detail.get("aweme_id") or "")
    engagement=[stats.get("digg_count"),stats.get("comment_count"),stats.get("share_count"),stats.get("collect_count")]
    plays=stats.get("play_count");metric_warnings=[]
    if plays==0 and any(isinstance(v,(int,float)) and v>0 for v in engagement):plays=None;metric_warnings.append("play_count_zero_conflicts_with_positive_engagement_treated_as_unknown")
    evidence = {
        "schema_version": "creative_evidence/v1",
        "creative_id": f"douyin:{item_id}", "platform": "douyin",
        "canonical_url": f"https://www.douyin.com/video/{item_id}",
        "title": detail.get("desc") or "",
        "author": {"platform_id": author.get("sec_uid") or author.get("uid"), "display_name": author.get("nickname")},
        "published_at": detail.get("create_time"),
        "metrics": {
            "plays": plays, "likes": stats.get("digg_count"),
            "comments": stats.get("comment_count"), "shares": stats.get("share_count"),
            "collects": stats.get("collect_count"),
        },
        "metric_warnings":metric_warnings,
        "provenance": {"adapter": "tikhub", "adapter_version": "openapi-v5.3.2", "detail_route":route,"failed_routes":failures},
    }
    return evidence, payload


def media_urls(raw_payload: dict[str, Any]) -> list[str]:
    detail = _detail(raw_payload)
    video = detail.get("video") or {}
    values: list[str] = []
    for field in ("download_addr", "play_addr", "play_addr_h264"):
        urls = (video.get(field) or {}).get("url_list") or []
        values.extend(url for url in urls if isinstance(url, str) and url.startswith("http"))
    return list(dict.fromkeys(values))
