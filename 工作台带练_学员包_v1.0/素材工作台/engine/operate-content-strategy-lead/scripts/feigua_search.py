#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞瓜易投 · 信息流素材搜索连接器 V1
=================================
直调网页端内部接口（apiyt.feigua.cn），用本人已购账号的 Cookie 鉴权。
适用版本：运营版 ¥399（已验证 2026-08-11：CreativeGroupType=-1/1/3 可用）。

鉴权来源（优先级从高到低）：
  1. 环境变量 FEIGUA_COOKIE
  2. ~/.config/feigua-yt/cookie.txt（chmod 600，由 agent 在浏览器重新登录后更新）

注意：FEIGUATYT 会话 Cookie 约 1 天过期。脚本遇到鉴权失败会以退出码 2 结束，
      由 agent 走「重新登录 → 更新 cookie.txt → 重跑」的维护流程。

数据口径：曝光/互动等均为供应商估算值，落库时归入 estimated_metrics，
          evidence_class=supplier_estimate（见 engineering/国内广告情报数据源深挖与接入决策_V1.md）。
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import ssl
try:
    import certifi
except ImportError:
    certifi = None
from datetime import datetime, timedelta

API = "https://apiyt.feigua.cn/api/v1/material/search/list"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

GROUP_TYPES = {"-1": "全部(信息流)", "1": "商品广告", "3": "直播引流广告"}
SORT_FIELDS = {
    "exposure": "ExposureCount",
    "interaction": "InteractionCount",
    "like": "LikeCount",
    "pubdate": "PubDateTime",
}


class AuthExpired(Exception):
    pass


def load_cookie() -> str:
    env = os.environ.get("FEIGUA_COOKIE", "").strip()
    if env:
        return env
    path = os.path.expanduser("~/.config/feigua-yt/cookie.txt")
    if os.path.exists(path):
        return open(path).read().strip()
    raise AuthExpired("未找到 Cookie：请设置 FEIGUA_COOKIE 或写入 ~/.config/feigua-yt/cookie.txt")


# 本机系统代理（如 Clash）会劫持国内站点的 urllib HTTPS 请求，导致
# SSL: UNEXPECTED_EOF_WHILE_READING（2026-08-11 实测，表象易被误判为风控）。
# 飞瓜是国内站点，固定走直连；如需走代理请显式设置 FEIGUA_COOKIE 之外的代理方案。
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where() if certifi else None)
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=_SSL_CONTEXT))


def api_get(cookie: str, params: dict) -> dict:
    params["_"] = int(time.time() * 1000)
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Cookie": cookie,
        "Accept": "application/json, text/plain, */*",
        "User-Agent": UA,
        "Referer": "https://yt.feigua.cn/",
    })
    with _OPENER.open(req, timeout=30) as r:
        j = json.loads(r.read())
    if not j.get("Status") or j.get("Code") != 200 or not j.get("Data"):
        code = j.get("Code")
        if code in (402,403):
            raise AuthExpired("接口返回 403：Cookie 已过期或该功能超出当前会员权限")
        raise RuntimeError(f"接口异常: {json.dumps(j, ensure_ascii=False)[:200]}")
    return j["Data"]


def flatten(item: dict) -> dict:
    i = item.get("Info", {})
    return {
        "标题": i.get("Title"),
        "抖音链接": i.get("DouyinVideoUrl"),
        "发布时间": i.get("PubDateTimeStr"),
        "时长": i.get("DurationStr"),
        "分类": i.get("AwemeTagFullName"),
        "广告类型": i.get("GroupIdStr"),
        "投放平台": i.get("AdvertisingChannelStr"),
        "跑量分": i.get("RunScore"),
        "预估曝光": i.get("ExposureCountStr"),
        "预估互动量": i.get("InteractionCountStr"),
        "点赞": i.get("LikeCountStr"),
        "评论": i.get("CommentCountStr"),
        "分享": i.get("ShareCountStr"),
        "收藏": i.get("CollectCountStr"),
        "互动率": i.get("InteractionRatioStr"),
        "封面": i.get("CoverUrl"),
        "evidence_class": "supplier_estimate",
    }


def search(cookie, keyword, from_date, to_date, period_type,
           group_type, sort_field, pages, page_size, delay, no_live=False):
    rows, raw = [], []
    total = None
    for p in range(1, pages + 1):
        data = api_get(cookie, {
            "fromDate": from_date, "toDate": to_date,
            "periodType": period_type, "sortField": sort_field,
            "CreativeGroupType": group_type,
            "pageNum": p, "pageSize": page_size,
            **({"keyword": keyword} if keyword else {}),
        })
        total = data.get("Total")
        items = data.get("Items") or []
        if not items:
            break
        if no_live:  # 只看信息流：剔除直播引流素材
            items = [x for x in items
                     if "直播引流" not in (x.get("Info", {}).get("GroupIdStr") or "")]
        rows.extend(flatten(x) for x in items)
        raw.extend(items)
        print(f"  第 {p} 页：+{len(items)} 条（累计 {len(rows)}，库内命中 {total}）",
              file=sys.stderr)
        if len(items) < page_size:
            break
        if p < pages:
            time.sleep(delay)
    return rows, raw, total


def main():
    ap = argparse.ArgumentParser(description="飞瓜易投信息流素材搜索连接器")
    ap.add_argument("--keyword", default="", help="搜索关键词（可空）")
    ap.add_argument("--days", type=int, default=7, help="最近 N 天（7/30/90/180）")
    ap.add_argument("--from-date", help="起始日 YYYYMMDD（覆盖 --days）")
    ap.add_argument("--to-date", help="截止日 YYYYMMDD（覆盖 --days）")
    ap.add_argument("--group-type", default="-1", choices=GROUP_TYPES.keys(),
                    help="-1=全部信息流 1=商品广告 3=直播引流")
    ap.add_argument("--sort", default="exposure", choices=SORT_FIELDS.keys())
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--page-size", type=int, default=20, choices=[10, 20])
    ap.add_argument("--delay", type=float, default=1.5, help="翻页间隔秒数，防风控")
    ap.add_argument("--outdir", default=None, help="输出目录，默认 runs/今天日期/")
    ap.add_argument("--tag", default="", help="输出文件名前缀标签")
    ap.add_argument("--no-live", action="store_true",
                    help="只看信息流：剔除直播引流素材（group-type=-1 时建议开启）")
    args = ap.parse_args()

    try:
        cookie = load_cookie()
    except AuthExpired as e:
        print(f"[鉴权失败] {e}", file=sys.stderr)
        sys.exit(2)

    if args.from_date and args.to_date:
        from_date, to_date = args.from_date, args.to_date
        period_type = args.days
    else:
        to = datetime.now() - timedelta(days=1)   # 昨天，数据已完整
        frm = to - timedelta(days=args.days - 1)
        from_date, to_date = frm.strftime("%Y%m%d"), to.strftime("%Y%m%d")
        period_type = args.days

    try:
        rows, raw, total = search(
            cookie, args.keyword, from_date, to_date, period_type,
            args.group_type, SORT_FIELDS[args.sort],
            args.pages, args.page_size, args.delay, args.no_live)
    except AuthExpired as e:
        print(f"[鉴权失败] {e} → 请在浏览器重新登录 yt.feigua.cn 后由 agent 更新 Cookie", file=sys.stderr)
        sys.exit(2)

    outdir = args.outdir or os.path.join(
        os.path.expanduser("~/Documents/内容飞轮操作系统/runs"),
        datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.now().strftime("%H%M")
    tag = (args.tag + "_") if args.tag else ""
    kw = args.keyword or "all"

    csv_path = os.path.join(outdir, f"feigua_{tag}{kw}_{from_date}-{to_date}_{stamp}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["空"])
        w.writeheader()
        w.writerows(rows)
    raw_path = csv_path.replace(".csv", "_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"query": vars(args), "total_in_lib": total, "items": raw},
                  f, ensure_ascii=False)

    print(f"完成：{len(rows)} 条（库内命中 {total}）")
    print(f"CSV: {csv_path}")
    print(f"RAW: {raw_path}")


if __name__ == "__main__":
    main()
