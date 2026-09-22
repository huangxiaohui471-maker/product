#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3：三平台真实数据 → 「全球新品库」33 字段记录（关联达人数已补齐）。

相对 v2 的关键改动：
- FastMoss 以**登录态抽取的表格数据**（fastmoss_sales.json / fastmoss_new.json，覆盖 60 个商品、
  全是美妆个护）为底，再用 **fiber 全字段数据**按 product_id 关联，补上
  关联达人数 / 累计关联达人数 / 关联视频数 / 关联直播数 / 精确上架时间 / 佣金比例；
- fiber 里出现、表格底料没有的美妆个护商品，一并补进来（这些天然带关联达人数）；
- 抖音罗盘改用 fiber 精确值（商品ID / 展示价 / 上下界求中），并保留原始区间文本。
"""
import collections
import datetime
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
OUT = os.path.join(D, 'records_v3.json')

REGION_CODE = {
    'VN': '东南亚', 'ID': '东南亚', 'TH': '东南亚', 'PH': '东南亚', 'MY': '东南亚', 'SG': '东南亚',
    'US': '欧美', 'GB': '欧美', 'DE': '欧美', 'FR': '欧美', 'IT': '欧美', 'ES': '欧美',
    'MX': '欧美', 'BR': '欧美', 'CA': '欧美', 'AU': '欧美',
    'JP': '日本', 'KR': '韩国',
}
MARKET_CN = {
    '越南': '东南亚', '印尼': '东南亚', '印度尼西亚': '东南亚', '泰国': '东南亚',
    '菲律宾': '东南亚', '马来西亚': '东南亚', '新加坡': '东南亚',
    '美国': '欧美', '英国': '欧美', '德国': '欧美', '法国': '欧美', '意大利': '欧美',
    '西班牙': '欧美', '墨西哥': '欧美', '巴西': '欧美',
    '日本': '日本', '韩国': '韩国',
}

FM_L2 = {
    '美容护肤': '护肤', '身体护理': '身体', '洗浴与身体护理': '个护', '沐浴露与香皂': '个护',
    '头部护理与造型': '个护', '鼻子口腔护理': '个护', '美妆': '彩妆', '香水': '香氛',
    '男女通用香水': '香氛', '美容、个护电器': '工具', '手足及指甲护理': '身体', '手足膜': '身体',
}
CAT_BY_PLATFORM_CAT = {
    '沐浴露与香皂': '个护', '洗发护发': '个护', '头发与头皮养护': '个护', '脱发产品': '个护',
    '身体霜、乳': '身体', '身体护理套装': '身体', '保湿油、按摩油': '身体',
    '护手足霜、乳液与磨砂膏': '身体',
    '面膜': '护肤', '面部精华液': '护肤', '保湿乳液、乳霜与喷雾': '护肤',
    '爽肤水、化妆水': '护肤', '卸妆': '护肤', '痘痘、粉刺护理': '护肤',
    '口红与唇彩': '彩妆', '腮红': '彩妆', '遮瑕与粉底': '彩妆', '假睫毛与胶水': '彩妆',
    '美甲装饰和配饰': '工具', '男女通用香水': '香氛',
}


def cat_by_title(t):
    s = (t or '').lower()
    rules = [
        ('香氛', r'香水|香氛|fragrance|perfume|parfum|nước hoa'),
        ('彩妆', r'口红|唇膏|唇釉|唇泥|唇彩|粉底|遮瑕|眼影|眼线|腮红|睫毛|眉笔|眉膏|染眉|气垫|散粉|蜜粉|定妆|粉饼|bb霜|cc霜'
                 r'|lipstick|mascara|foundation|blush|concealer|eyeshadow|eyeliner|bulu mata|bút phấn mắt|bút kẻ|ดินสอ|เขียนคิ้ว'),
        ('工具', r'美甲|指甲|化妆刷|粉扑|美妆蛋|睫毛夹|修眉|刮眉|nail|brush|pemotong|cukur|กันคิ้ว|โกนคิ้ว|hair clipper|móng'),
        ('身体', r'身体乳|身体霜|身体护理|磨砂|护手霜|护足|颈霜|body lotion|body cream|body scrub|hand cream|perawatan tubuh|dưỡng thể'),
        ('个护', r'沐浴|洗发|护发|牙膏|牙刷|香皂|洗手|剃须|脱发|grooming|口腔|漱口'
                 r'|shampoo|soap|body wash|xà phòng|dầu gội|dầu xả|ผม|ผมร่วง|bàn chải|sabun'),
        ('护肤', r'水乳|精华|面霜|面膜|泥膜|眼霜|眼膜|爽肤水|化妆水|防晒|肌底|安瓶|洗面|洁面|卸妆|去角质|祛痘|凝胶|乳霜'
                 r'|烟酰胺|熊果苷|保湿|补水|控油|毛孔|提亮|嫩肤|屏障|抗皱|淡斑|美白|紧致'
                 r'|serum|cream|toner|mask|lotion|essence|sunscreen|moisturiz|cleanser'
                 r'|sữa rửa|mặt nạ|kem dưỡng|tinh dầu|dưỡng ẩm|สร้างฟอง|บำรุงผิว'),
    ]
    for cat, pat in rules:
        if re.search(pat, s):
            return cat
    return ''


def num_of(text):
    if text is None:
        return None
    s = str(text).strip()
    if not s or s in ('-', '—', '**'):
        return None
    s = s.replace(',', '').replace(' ', '')
    s = re.sub(r'^[^\d\-+]+', '', s)
    pct = s.endswith('%')
    s = s.rstrip('%')
    m = re.match(r'^(-?[\d.]+)(万|亿|k|K|千|w)?$', s)
    if not m:
        return None
    v = float(m.group(1))
    unit = m.group(2)
    if unit in ('万', 'w'):
        v *= 10000
    elif unit == '亿':
        v *= 100000000
    elif unit in ('k', 'K', '千'):
        v *= 1000
    if pct:
        return round(v, 2)
    return int(round(v)) if abs(v) >= 1 else round(v, 2)


def range_mid(text):
    raw = (text or '').strip()
    if not raw:
        return None, ''
    parts = re.split(r'\s*[-–~]\s*', raw) if ('-' in raw or '~' in raw) else [raw]
    nums = [n for n in (num_of(p) for p in parts) if n is not None]
    if not nums:
        return None, raw
    if len(nums) == 1:
        return nums[0], raw
    return int(round(sum(nums) / len(nums))), raw


def price_mid(text):
    if not text:
        return None
    nums = [n for n in (num_of(x) for x in re.split(r'[-–~]', str(text).replace('¥', ' '))) if n is not None]
    return int(round(sum(nums) / len(nums))) if nums else None


def brand_of(shop):
    s = re.split(r'店铺销量', shop or '')[0].strip()
    s = re.sub(r'(海外)?(官方)?(旗舰店|专卖店|专营店|旗舰|官方店|官方)$', '', s).strip()
    return s


def fmt_num(v):
    if v is None:
        return '—'
    if v >= 100000000:
        return '%.2f亿' % (v / 100000000)
    if v >= 10000:
        return '%.2f万' % (v / 10000)
    return str(v)


def ts_date(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime('%Y-%m-%dT00:00:00Z')
    except Exception:
        return None


# ---------- fiber 索引：product_id -> 全字段 ----------
fiber = {}
for fn in ('fastmoss_sales_fiber.json', 'fastmoss_new_fiber.json'):
    for r in json.load(open(os.path.join(D, fn), encoding='utf-8'))['rows']:
        pid = str(r.get('product_id') or '')
        if pid:
            fiber.setdefault(pid, r)
print('fiber 索引条数:', len(fiber))

records = []

# ---------------- 1. 抖音罗盘 · 商品榜单（fiber 精确值） ----------------
dp = json.load(open(os.path.join(D, 'douyin_compass_fiber.json'), encoding='utf-8'))
rng = dp.get('meta', {}).get('range', '')
for r in dp['rows']:
    note = ('抖音罗盘·商品榜单 第%s名（行业类目：个护家清/个人护理/身体清洁/沐浴露·油·乳；统计周期 %s）；'
            '店铺=%s；店铺名称≠品牌，品牌为店铺名去渠道后缀所得；'
            '口径：用户支付金额 %s、成交件数 %s、点击次数 %s、点击成交转化率 %s%%（区间按上下界取中值，原始数值见括号）'
            '【%s】【%s】【%s】【%s】；商品展示价 %s；商品ID %s；%s。'
            % (r.get('rank'), rng, r.get('shop_name'),
               fmt_num(r.get('gmv_mid')), fmt_num(r.get('orders_mid')), fmt_num(r.get('clicks_mid')), r.get('conv_mid'),
               r.get('gmv_raw'), r.get('orders_raw'), r.get('clicks_raw'), r.get('conv_raw'),
               r.get('price_bin') or '—', r.get('product_id'),
               '本期新上榜' if r.get('newly_on_ranking') else '非新上榜'))
    records.append({
        '商品名称': r.get('name', ''),
        '品牌': brand_of(r.get('shop_name')),
        '商品ID': str(r.get('product_id') or ''),
        '品类': '个护',
        '细分品类': '沐浴露/油/乳',
        '价格': price_mid(r.get('price_bin')),
        '数据来源': '抖音罗盘',
        '所属市场': '中国',
        '榜单排名': '抖音罗盘·商品榜单 第%s名（个护家清·沐浴露/油/乳，%s）' % (r.get('rank'), rng),
        '销量': r.get('orders_mid'),
        '销售额': r.get('gmv_mid'),
        '环比增速': None,
        '关联达人数': None,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    })

# ---------------- 2. 蝉妈妈 · 抖音商品销量榜（中国·美妆护肤） ----------------
cm = json.load(open(os.path.join(D, 'chanmama_beauty.json'), encoding='utf-8'))
for r in cm['rows']:
    qty = num_of(r.get('day_order_exact'))
    amt = r.get('amount_exact')
    amt = int(round(amt)) if isinstance(amt, (int, float)) else num_of(amt)
    growth = None
    if r.get('last7') and r.get('prev7'):
        growth = round((r['last7'] - r['prev7']) / r['prev7'] * 100, 1)
    unit = '—'
    if qty and amt:
        unit = '客单价约¥%.1f（=日销售额÷日销量推算，非平台标价）' % (amt / qty)
    note = ('蝉妈妈·抖音商品销量榜（美妆护肤类目，第%s名）；店铺=%s；'
            '口径：日销量 %s 件、日销售额 ¥%s（平台明文值）；近1年销量 %s 件；30天转化率 %s；%s；'
            '环比=近7天销量 %s vs 前7天 %s；平台隐藏标价，价格字段留空'
            % (r.get('rank'), r.get('shop'), fmt_num(qty), fmt_num(amt),
               fmt_num(num_of(r.get('year_order_exact'))), r.get('conv') or '—',
               unit, fmt_num(r.get('last7')), fmt_num(r.get('prev7'))))
    records.append({
        '商品名称': r.get('title', ''),
        '品牌': brand_of(r.get('shop', '')),
        '商品ID': r.get('product_id', ''),
        '品类': cat_by_title(r.get('title', '')),
        '细分品类': '',
        '价格': None,
        '数据来源': '蝉妈妈',
        '所属市场': '中国',
        '榜单排名': '蝉妈妈抖音商品销量榜 第%s名（美妆护肤，日榜）' % r.get('rank'),
        '上市日期': ts_date(r.get('first_crawl_time')),
        '销量': qty,
        '销售额': amt,
        '环比增速': growth,
        '关联达人数': None,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    })

# ---------------- 3. FastMoss 销量榜（登录态表格底料 + fiber 补达人） ----------------
fm = json.load(open(os.path.join(D, 'fastmoss_sales.json'), encoding='utf-8'))
H = fm['heads']
used_ids = set()


def cell(row, name, heads=H):
    try:
        return row['cells'][heads.index(name)]
    except Exception:
        return ''


for idx, r in enumerate(fm['rows']):
    pid = str(r.get('productId') or '')
    f = fiber.get(pid)
    used_ids.add(pid)
    country = cell(r, '国家/地区')
    pcat = cell(r, '商品分类')
    qty = num_of(cell(r, '销量'))
    growth = num_of(cell(r, '销量环比'))
    extra = ''
    author = None
    if f:
        author = f.get('author_count')
        extra = ('；fiber 补全：关联达人数 %s、累计关联达人数 %s、关联视频 %s、关联直播 %s、上架时间 %s'
                 % (fmt_num(f.get('author_count')), fmt_num(f.get('total_author_count')),
                    fmt_num(f.get('aweme_count')), fmt_num(f.get('live_count')), (f.get('launch_time') or '—')))
    else:
        extra = '；该商品无 fiber 明细，关联达人数暂缺（FastMoss 游客态仅放 2 页）'
    note = ('FastMoss·销量榜（美妆个护类目，第%d页第%d位）；国家/地区=%s；店铺=%s；商品分类=%s；佣金比例=%s；'
            '口径：当期销量 %s 件、销量环比 %s、销售额 %s、总销量 %s、总销售额 %s；'
            '价格与销售额因多币种未折算暂不入库（海外价折算汇率待定），原始币种数值见上%s'
            % (r.get('page'), (idx % 10) + 1, country, cell(r, '所属店铺'), pcat,
               cell(r, '佣金比例') or '—', cell(r, '销量') or '—', cell(r, '销量环比') or '—',
               cell(r, '销售额') or '—', cell(r, '总销量') or '—', cell(r, '总销售额') or '—', extra))
    rec = {
        '商品名称': re.sub(r'\s*售价：.*$', '', cell(r, '商品')).strip(),
        '品牌': brand_of(cell(r, '所属店铺')),
        '商品ID': pid,
        '品类': CAT_BY_PLATFORM_CAT.get(pcat) or cat_by_title(cell(r, '商品')),
        '细分品类': pcat if pcat != '美妆个护' else (fiber.get(pid, {}).get('category_name') or [''])[0],
        '价格': None,
        '数据来源': 'FastMoss',
        '所属市场': MARKET_CN.get(country, ''),
        '榜单排名': 'FastMoss销量榜 第%d页第%d位（美妆个护·%s）' % (r.get('page'), (idx % 10) + 1, country),
        '销量': qty,
        '销售额': None,
        '环比增速': growth,
        '关联达人数': author,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    }
    if f and f.get('launch_time'):
        rec['上市日期'] = str(f['launch_time'])[:10] + 'T00:00:00Z'
    records.append(rec)

# ---------------- 4. FastMoss 新品榜（登录态表格底料 + fiber 补达人） ----------------
ne = json.load(open(os.path.join(D, 'fastmoss_new.json'), encoding='utf-8'))
NH = ne['heads']
for i, r in enumerate(ne['rows']):
    pid = str(r.get('productId') or '')
    used_ids.add(pid)
    f = fiber.get(pid)
    country = cell(r, '国家/地区', NH)
    title_raw = cell(r, '商品', NH)
    if not title_raw:
        continue
    mUp = re.search(r'上架时间：(\d{4}-\d{2}-\d{2})', title_raw)
    mPrice = re.search(r'售价：([^\s上]+)', title_raw)
    pcat = cell(r, '商品分类', NH)
    cat = CAT_BY_PLATFORM_CAT.get(pcat) or cat_by_title(title_raw)
    if f and (f.get('all_category_name') or [''])[0] == '美妆个护':
        l2 = (f.get('all_category_name') or ['', ''])[1]
        cat = cat or FM_L2.get(l2) or ''
    if not cat:
        continue
    launch = (mUp.group(1) if mUp else None) or (str(f.get('launch_time'))[:10] if f and f.get('launch_time') else None)
    extra = ''
    author = None
    if f:
        author = f.get('author_count')
        extra = ('；fiber 补全：关联达人数 %s、累计关联达人数 %s、关联视频 %s、关联直播 %s'
                 % (fmt_num(f.get('author_count')), fmt_num(f.get('total_author_count')),
                    fmt_num(f.get('aweme_count')), fmt_num(f.get('live_count'))))
    else:
        extra = '；该商品无 fiber 明细，关联达人数暂缺（FastMoss 游客态仅放 2 页）'
    note = ('FastMoss·新品榜（美妆个护，第%d页第%d位）；国家/地区=%s；店铺=%s；商品分类=%s；'
            '上架时间=%s；售价=%s（多币种未折算，价格字段留空）；'
            '口径：三日销量 %s、三日销售额 %s、总销量 %s、总销售额 %s；店铺销量 %s%s'
            % (r.get('page'), (i % 10) + 1, country, cell(r, '所属店铺', NH), pcat,
               launch or '—', mPrice.group(1) if mPrice else '—',
               cell(r, '三日销量', NH) or '—', cell(r, '三日销售额', NH) or '—',
               cell(r, '总销量', NH) or '—', cell(r, '总销售额', NH) or '—',
               re.sub(r'.*店铺销量：', '', cell(r, '所属店铺', NH)) or '—', extra))
    rec = {
        '商品名称': re.sub(r'\s*(售价|上架时间)：.*$', '', title_raw).strip(),
        '品牌': brand_of(cell(r, '所属店铺', NH)),
        '商品ID': pid,
        '品类': cat,
        '细分品类': pcat if pcat != '美妆个护' else (fiber.get(pid, {}).get('category_name') or [''])[0],
        '价格': None,
        '数据来源': 'FastMoss',
        '所属市场': MARKET_CN.get(country, ''),
        '榜单排名': 'FastMoss新品榜 第%d页第%d位（美妆个护·%s）' % (r.get('page'), (i % 10) + 1, country),
        '销量': num_of(cell(r, '总销量', NH)),
        '销售额': None,
        '环比增速': None,
        '关联达人数': author,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    }
    if launch:
        rec['上市日期'] = launch + 'T00:00:00Z'
    records.append(rec)

# ---------------- 5. fiber 里新增的美妆个护商品（表格底料没有的） ----------------
added = 0
for pid, f in fiber.items():
    if pid in used_ids:
        continue
    ac = f.get('all_category_name') or []
    if not ac or ac[0] != '美妆个护':
        continue
    l2 = ac[1] if len(ac) > 1 else ''
    cat = FM_L2.get(l2) or CAT_BY_PLATFORM_CAT.get(l2) or cat_by_title(f.get('title', ''))
    if not cat:
        continue
    mk = REGION_CODE.get(f.get('region'), '')
    note = ('FastMoss·%s（TikTok 全类目榜筛出美妆个护）；国家/地区=%s；店铺=%s；类目=%s；佣金比例=%s；'
            '上架时间=%s；口径：当期销量 %s 件、销量环比 %s、销售额 %s%s、总销量 %s 件、总销售额 %s%s；'
            '关联达人数 %s（累计 %s）；关联视频 %s、关联直播 %s；'
            '价格与销售额因多币种未折算暂不入库（海外价折算汇率待定），原始数值见上'
            % ('新品榜' if 'launch_time' in f else '销量榜', f.get('region'), f.get('shop_name'),
               ' / '.join(ac), f.get('commission_rate') or '—', f.get('launch_time') or '—',
               fmt_num(f.get('sold_count')), f.get('sold_count_inc_rate') or '—',
               fmt_num(f.get('sale_amount')), f.get('currency') or '',
               fmt_num(f.get('total_sold_count')), fmt_num(f.get('total_sale_amount')), f.get('currency') or '',
               fmt_num(f.get('author_count')), fmt_num(f.get('total_author_count')),
               fmt_num(f.get('aweme_count')), fmt_num(f.get('live_count'))))
    rec = {
        '商品名称': f.get('title', ''),
        '品牌': brand_of(f.get('shop_name')),
        '商品ID': pid,
        '品类': cat,
        '细分品类': l2,
        '价格': None,
        '数据来源': 'FastMoss',
        '所属市场': mk,
        '榜单排名': 'FastMoss·TikTok榜单（全类目筛美妆个护·%s）' % f.get('region'),
        '销量': f.get('sold_count'),
        '销售额': None,
        '环比增速': num_of(f.get('sold_count_inc_rate')),
        '关联达人数': f.get('author_count'),
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    }
    if f.get('launch_time'):
        rec['上市日期'] = str(f['launch_time'])[:10] + 'T00:00:00Z'
    records.append(rec)
    added += 1

# 去重：优先商品ID，其次商品名称
seen, dedup = set(), []
for r in records:
    key = r['商品ID'] or r['商品名称']
    if not key or key in seen:
        continue
    seen.add(key)
    dedup.append(r)

json.dump({'count': len(dedup), 'records': dedup}, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('写入', OUT, '共', len(dedup), '条（fiber 新增 %d 条）' % added)
print('按来源:', dict(collections.Counter(r['数据来源'] for r in dedup)))
print('按市场:', dict(collections.Counter(r['所属市场'] or '(空)' for r in dedup)))
print('按品类:', dict(collections.Counter(r['品类'] or '(空)' for r in dedup)))
print('有关联达人数:', sum(1 for r in dedup if r['关联达人数'] is not None))
print('有环比:', sum(1 for r in dedup if r['环比增速'] is not None),
      '| 有价格:', sum(1 for r in dedup if r['价格'] is not None),
      '| 有销售额:', sum(1 for r in dedup if r['销售额'] is not None),
      '| 有上市日期:', sum(1 for r in dedup if r.get('上市日期')))
for s in ('抖音罗盘', '蝉妈妈', 'FastMoss'):
    sub = [r for r in dedup if r['数据来源'] == s]
    print('  %s: %d 条，其中有关联达人数 %d 条' % (s, len(sub), sum(1 for r in sub if r['关联达人数'] is not None)))
