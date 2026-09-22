#!/usr/bin/env python3
"""用 TikHub 拉取 TikTok 商品详情，补齐评分 / 评价数 / 店铺 / 描述全文 / 官方类目 / 法规属性。

数据源：data/records_cat_400.json 里 数据来源=FastMoss 且 国家/地区 有对应 region 的记录。
输出：data/tikhub_details.json（可断点续跑）

【2026-09-20 修正的关键 bug】
  旧版 find_component 走 root['product_data']，真实路径是 root['data']['product_data']，
  导致永远取不到 components_map → 每条都被误判成「组件缩水」，并伪造成「频率限制」现象。
  实测修正后：**不存在隐性频率限制**，间隔 1.5 秒连续拉取即可。
  （教训：连续同形状失败要先 dump 原始响应验证，别急着换姿势重试。）

字段位置（root）：
  data.product_data.page_config.components_map[] 里 component_type=product_info 的那条
    .component_data.error_code / error_message      → 0 / success 才算成功
    .component_data.product_info.product_model      → product_id/sold_count/name/description/...
    .component_data.product_info.review_model       → product_overall_score / product_review_count
    .component_data.product_info.seller_model       → shop_name
    .component_data.category_info.recommended_categories → 官方三级 cid 路径
    .component_data.product_properties              → 法规属性（印尼 BPOM 号、美国 CA prop 65 等）
注意：sold_count / product_review_count 是**字符串**，要转 int。

用法：
  python3 tikhub_detail_fetch.py --limit 3      # 试跑 3 条
  python3 tikhub_detail_fetch.py                # 全量（跳过已成功缓存）
  python3 tikhub_detail_fetch.py --gap 1.5      # 调间隔
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tikhub  # noqa: E402

D = Path(__file__).parent
SRC = D / 'data' / 'records_cat_400.json'
OUT = D / 'data' / 'tikhub_details.json'

# 国家/地区 -> TikTok Shop region（openapi.json 里 region 的合法枚举：
# US, SG, MY, PH, TH, VN, ID, JP, MX, BR；GB 官方明确暂不支持）
REGION = {
    '美国': 'US', '印度尼西亚': 'ID', '泰国': 'TH', '越南': 'VN',
    '菲律宾': 'PH', '马来西亚': 'MY', '新加坡': 'SG', '日本': 'JP',
    '巴西': 'BR', '墨西哥': 'MX',
}

EP = '/api/v1/tiktok/shop/web/fetch_product_detail_v3'


def to_int(v):
    """sold_count / review_count 是字符串，可能带 'K+' 之类后缀。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().replace(',', '')
    m = re.match(r'^([\d.]+)\s*([KkMm])?', s)
    if not m:
        return None
    n = float(m.group(1))
    unit = (m.group(2) or '').lower()
    if unit == 'k':
        n *= 1_000
    elif unit == 'm':
        n *= 1_000_000
    return int(n)


def cmap(root: dict) -> list:
    """取 components_map。兼容两种层级，避免再踩路径坑。"""
    for path in (('data', 'product_data'), ('product_data',)):
        node = root
        for k in path:
            node = (node or {}).get(k) if isinstance(node, dict) else None
        if isinstance(node, dict):
            pc = node.get('page_config') or {}
            cm = pc.get('components_map') if isinstance(pc, dict) else None
            if cm:
                return cm
    return []


def find_component(root: dict, ctype: str) -> dict:
    for c in cmap(root):
        if c.get('component_type') == ctype or c.get('component_name') == ctype:
            return c.get('component_data') or {}
    return {}


def desc_text(desc) -> str:
    """把富文本 description 的文字段落拼起来（丢弃图片节点）。"""
    if isinstance(desc, str):
        s = desc.strip()
        if not s.startswith('['):
            return s
        try:
            desc = json.loads(s)
        except Exception:
            return s
    out = []
    if isinstance(desc, list):
        for node in desc:
            if isinstance(node, dict) and node.get('type') == 'text':
                t = node.get('text') or ''
                if t:
                    out.append(t)
                for sub in node.get('sub') or []:
                    st = sub.get('t') if isinstance(sub, dict) else None
                    if st and st != t:
                        out.append(st)
            elif isinstance(node, str):
                out.append(node)
    elif isinstance(desc, dict):
        return str(desc.get('text') or '')
    # 去重连续重复行（TikTok 的 sub 常与 text 重复）
    seen, clean = set(), []
    for line in out:
        if line in seen:
            continue
        seen.add(line)
        clean.append(line)
    return '\n'.join(clean)


LEGAL_HINT = ('ijin', 'bpom', 'pirt', 'prop 65', 'registration', '备案', 'license', 'permit', 'fda')


def legal_props(props) -> list:
    """挑出法规/备案类属性。"""
    got = []
    for p in props or []:
        if not isinstance(p, dict):
            continue
        nm = str(p.get('property_name') or '')
        if any(h in nm.lower() for h in LEGAL_HINT):
            vals = [str(v.get('property_value_name')) for v in (p.get('property_values') or [])
                    if isinstance(v, dict) and v.get('property_value_name')]
            if vals:
                got.append({'name': nm, 'value': ' / '.join(vals)})
    return got


def parse(root: dict):
    """解析。返回 (dict, err)。err 非空即失败原因。"""
    cd = find_component(root, 'product_info')
    if not cd:
        return None, 'no_product_info_component'
    ec = cd.get('error_code')
    if ec not in (0, '0', None):
        return None, 'component_error:%s:%s' % (ec, str(cd.get('error_message'))[:40])
    pi = cd.get('product_info') or {}
    pm = pi.get('product_model') or {}
    if not pm.get('name'):
        return None, 'no_product_model'
    rm = pi.get('review_model') or {}
    shop = pi.get('seller_model') or {}
    cats = (cd.get('category_info') or {}).get('recommended_categories') or []
    dt = desc_text(pm.get('description'))
    return {
        'name': pm.get('name'),
        'sold_count': to_int(pm.get('sold_count')),
        'score': rm.get('product_overall_score'),
        'review_count': to_int(rm.get('product_review_count')),
        'shop_name': shop.get('shop_name'),
        'description': dt,
        'desc_len': len(dt),
        'cat_names': [c.get('category_name') for c in cats if c.get('category_name')],
        'cat_ids': [str(c.get('category_id')) for c in cats if c.get('category_id')],
        'sku_count': len(pm.get('skus') or []),
        'legal': legal_props(pm.get('product_properties')),
        'status': ((pi.get('base_resp') or {}).get('StatusMessage') or ''),
    }, ''


def fetch_one(t: dict, maxtry: int, gap: float, fallbacks=()) -> dict:
    """拉单条。

    站点回退：实测 TH / PH / VN 的 storefront 接口大面积返回 400 或返回 200 但组件为空，
    但同一 product_id 用 ID 站点能取到完整数据（商品名与原区一致）→ 说明商品存在、
    只是该区站点解析不了。故本区失败时按 fallbacks 顺序换站点再试，
    并把实际使用的站点记进 region_used / fallback 两个字段，便于事后区分置信度。
    """
    entry = {'pid': t['pid'], 'region': t['region'], 'country': t['country'],
             'src_name': t['name'], 'ok': False, 'region_used': None, 'fallback': False}
    for rg in [t['region']] + [x for x in fallbacks if x != t['region']]:
        for attempt in range(maxtry):
            d = tikhub.get(EP, {'product_id': t['pid'], 'region': rg}, retry=1, timeout=50)
            if d.get('_error'):
                err = str(d['_error'])
                entry['err'] = err[:160]
                if '"code":400' in err or '"code":404' in err:
                    break  # 该站点解析不了，换下一个站点
                if attempt + 1 < maxtry:
                    time.sleep(gap + attempt)
                continue
            parsed, perr = parse(d)
            if parsed:
                entry.update(parsed)
                entry['ok'] = True
                entry['region_used'] = rg
                entry['fallback'] = (rg != t['region'])
                entry['tries'] = attempt + 1
                return entry
            entry['err'] = perr
            if attempt + 1 < maxtry:
                time.sleep(gap + attempt)
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--maxtry', type=int, default=2)
    ap.add_argument('--gap', type=float, default=1.5, help='请求间隔秒')
    ap.add_argument('--save-every', type=int, default=10)
    ap.add_argument('--out', default=str(OUT), help='输出文件（并行分片时各自指定）')
    ap.add_argument('--only', default='', help='只跑这些 region，逗号分隔，如 MY,VN')
    ap.add_argument('--fallback', default='ID,US', help='本区取不到时依次回退的站点')
    ap.add_argument('--part', default='', help='分片 i/N（如 2/3），用于把同一个大区拆成多进程并行')
    args = ap.parse_args()
    out_path = Path(args.out)
    only = set(x.strip().upper() for x in args.only.split(',') if x.strip())
    fallbacks = [x.strip().upper() for x in args.fallback.split(',') if x.strip()]

    recs = json.load(open(SRC, encoding='utf-8'))['records']
    targets = []
    for r in recs:
        if r.get('数据标记') != '真实' or r.get('数据来源') != 'FastMoss':
            continue
        rg = REGION.get(r.get('国家/地区'))
        if not rg:
            continue
        targets.append({'pid': str(r.get('商品ID')), 'region': rg,
                        'country': r.get('国家/地区'), 'name': r.get('商品名称')})
    if only:
        targets = [t for t in targets if t['region'] in only]
    PRIORITY = {'US': 0, 'ID': 1, 'JP': 2, 'SG': 3, 'MY': 4, 'VN': 5, 'TH': 6, 'PH': 7, 'MX': 8, 'BR': 9}
    targets.sort(key=lambda t: PRIORITY.get(t['region'], 9))
    if args.part:
        _i, _n = (int(x) for x in args.part.split('/'))
        targets = [t for _k, t in enumerate(targets) if _k % _n == _i - 1]
    if args.limit:
        targets = targets[:args.limit]

    cache = {}
    if out_path.is_file() and not args.force:
        try:
            cache = json.load(open(out_path, encoding='utf-8'))
        except Exception:
            cache = {}

    todo = [t for t in targets if not (cache.get(t['pid']) or {}).get('ok')]
    print('目标 %d 条｜已成功 %d 条｜本轮待拉 %d 条｜间隔 %.1fs' % (
        len(targets), sum(1 for v in cache.values() if v.get('ok')), len(todo), args.gap), flush=True)

    stat = {'ok': 0, 'fail': 0}
    t0 = time.time()
    for i, t in enumerate(todo, 1):
        entry = fetch_one(t, args.maxtry, args.gap, fallbacks)
        cache[entry['pid']] = entry
        if entry['ok']:
            stat['ok'] += 1
            print('[%3d/%3d] ✓ %-3s%-4s sold=%-9s score=%-4s rev=%-7s desc=%-5s legal=%-2d %s' % (
                i, len(todo), entry['region'],
                ('→' + entry['region_used']) if entry.get('fallback') else '',
                entry.get('sold_count'), entry.get('score'),
                entry.get('review_count'), entry.get('desc_len'), len(entry.get('legal') or []),
                (entry.get('shop_name') or '')[:20]), flush=True)
        else:
            stat['fail'] += 1
            print('[%3d/%3d] ✗ %-3s %-30s %s' % (
                i, len(todo), entry['region'], str(entry.get('src_name'))[:28],
                str(entry.get('err'))[:70]), flush=True)
        if i % args.save_every == 0:
            json.dump(cache, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(args.gap)
    json.dump(cache, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    el = time.time() - t0
    okall = sum(1 for v in cache.values() if v.get('ok'))
    print('\n本轮 成功 %d / 失败 %d ｜ 耗时 %.0f 秒' % (stat['ok'], stat['fail'], el))
    print('累计成功 %d / %d 条（%.0f%%）' % (okall, len(targets), 100.0 * okall / max(len(targets), 1)))
    okl = [v for v in cache.values() if v.get('ok')]
    print('有评分 %d｜有评价数 %d｜有描述(>50字) %d｜有店铺名 %d｜有法规属性 %d' % (
        sum(1 for v in okl if v.get('score') is not None),
        sum(1 for v in okl if v.get('review_count') is not None),
        sum(1 for v in okl if (v.get('desc_len') or 0) > 50),
        sum(1 for v in okl if v.get('shop_name')),
        sum(1 for v in okl if v.get('legal'))))
    fails = [v for v in cache.values() if not v.get('ok')]
    if fails:
        from collections import Counter
        c = Counter(str(v.get('err'))[:40] for v in fails)
        print('失败原因 TOP:', c.most_common(5))


if __name__ == '__main__':
    main()
