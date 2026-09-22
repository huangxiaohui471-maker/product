#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v4：三平台真实数据 → 「全球新品库」记录。

相对 v3 的关键改动：
- FastMoss 改为**登录态 CDP 抓取的 fiber 全字段**（销量榜 150 + 新品榜 100，全为美妆个护，
  不再需要「表格底料 + fiber 关联」两步），三个源字段密度一致；
- 品类映射改以**三级类目**为准（250 条全有三级），二级 / 标题关键词兜底；
- 价格与销售额维持「多币种不折算即不入库、原始值写笔记」口径。
"""
import collections
import datetime
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
OUT = os.path.join(D, 'records_v4.json')

REGION_CODE = {
    'VN': '东南亚', 'ID': '东南亚', 'TH': '东南亚', 'PH': '东南亚', 'MY': '东南亚', 'SG': '东南亚',
    'US': '欧美', 'GB': '欧美', 'DE': '欧美', 'FR': '欧美', 'IT': '欧美', 'ES': '欧美',
    'MX': '欧美', 'BR': '欧美', 'CA': '欧美', 'AU': '欧美',
    'JP': '日本', 'KR': '韩国',
}

# 三级类目 → 六大品类（源自 FastMoss 美妆个护类目树实测）
CAT_L3 = {
    '护肤': ['面部精华液', '保湿乳液、乳霜与喷雾', '爽肤水、化妆水', '面膜', '洗面乳', '洗面乳、卸妆',
             '脸部防晒霜与晒后修复', '防晒', '卸妆', '痘痘、粉刺护理', '眼部护理', '唇部护理',
             '面部护理套装', '妆前乳与眼影打底膏', '面部磨砂膏与去角质', '精华', '乳液'],
    '彩妆': ['口红与唇彩', '假睫毛与胶水', '遮瑕与粉底', '腮红', '定妆喷雾', '眉笔&眉粉&眉胶',
             '眼线笔与唇线笔', '睫毛膏', 'BB霜与CC霜', '美妆套装', '指甲油', '眼影'],
    '个护': ['沐浴露与香皂', '牙膏', '头发与头皮养护', '洗发护发', '脱发产品', '口腔喷剂',
             '鼻部清洁用品', '手动牙刷', '牙线和牙签', '私密处清洁用品', '卫生巾', '成人纸尿裤',
             '染发用品', '男士洗浴与身体护理', '男士手动剃须工具', '驱虫剂', '眼罩', '暖宝宝'],
    '身体': ['身体护理套装', '身体霜、乳', '保湿油、按摩油', '护手足霜、乳液与磨砂膏',
             '身体磨砂膏、去角质', '手足膜', '除毛乳、除毛蜜蜡&除毛器'],
    '香氛': ['男女通用香水', '女士香水', '男士香水', '香水套装'],
    '工具': ['洗澡工具', '化妆工具', '美甲装饰和配饰', '美甲套装', '理发器', '手动按摩用品',
             '耳垢清洁产品和工具', '手足工具与配件', '面部护理工具', '按摩器', '卷、直发器',
             '指甲护理', '粉扑', '美甲工具'],
}
CAT_BY_L3 = {}
for _c, _lst in CAT_L3.items():
    for _x in _lst:
        CAT_BY_L3[_x] = _c

CAT_L2 = {
    '美容护肤': '护肤', '洗浴与身体护理': '个护', '头部护理与造型': '个护', '鼻子口腔护理': '个护',
    '美妆': '彩妆', '香水': '香氛', '美容、个护电器': '工具', '手足及指甲护理': '身体',
    '女性私密处护理': '个护', '特殊个护': '个护', '眼镜耳朵护理': '个护', '男士护理': '个护',
}


def cat_by_title(t):
    s = (t or '').lower()
    rules = [
        ('香氛', r'香水|香氛|fragrance|perfume|parfum|nước hoa'),
        ('彩妆', r'口红|唇膏|唇釉|唇泥|唇彩|粉底|遮瑕|眼影|眼线|腮红|睫毛|眉笔|眉膏|染眉|气垫|散粉|蜜粉|定妆|粉饼'
                 r'|lipstick|mascara|foundation|blush|concealer|eyeshadow|eyeliner'),
        ('工具', r'美甲|指甲|化妆刷|粉扑|美妆蛋|睫毛夹|修眉|刮眉|nail|brush|hair clipper|móng'),
        ('身体', r'身体乳|身体霜|身体护理|磨砂|护手霜|护足|颈霜|body lotion|body cream|body scrub|hand cream'),
        ('个护', r'沐浴|洗发|护发|牙膏|牙刷|香皂|洗手|剃须|脱发|grooming|口腔|漱口|私密'
                 r'|shampoo|soap|body wash|sabun'),
        ('护肤', r'水乳|精华|面霜|面膜|泥膜|眼霜|眼膜|爽肤水|化妆水|防晒|肌底|安瓶|洗面|洁面|卸妆|去角质|祛痘|凝胶|乳霜'
                 r'|保湿|补水|控油|毛孔|提亮|维稳|屏障|抗皱|淡斑|美白|紧致|嫩肤|修护'
                 r'|serum|cream|toner|mask|lotion|essence|sunscreen|moisturiz|cleanser'),
    ]
    for cat, pat in rules:
        if re.search(pat, s):
            return cat
    return ''


def cat_of(f):
    ac = f.get('all_category_name') or []
    l3 = ac[2] if len(ac) > 2 else ''
    l2 = ac[1] if len(ac) > 1 else ''
    c = CAT_BY_L3.get(l3) or CAT_L2.get(l2) or cat_by_title(f.get('title', ''))
    return c, l2, l3


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


def price_mid(text):
    if not text:
        return None
    nums = [n for n in (num_of(x) for x in re.split(r'[-–~]', str(text))) if n is not None]
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


records = []

# ---------------- 1. 抖音罗盘 · 商品榜单 ----------------
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
        '细分品类': '沐浴露与香皂',
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

# ---------------- 2. 蝉妈妈 · 抖音商品销量榜 ----------------
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

# ---------------- 3. FastMoss · 登录态 fiber 全字段（销量榜 + 新品榜） ----------------
KIND_CN = {'sales': '销量榜', 'new': '新品榜'}
for fn, kind in (('fastmoss_sales_fiber.json', 'sales'), ('fastmoss_new_fiber.json', 'new')):
    data = json.load(open(os.path.join(D, fn), encoding='utf-8'))
    pos = {}
    for f in data['rows']:
        cat, l2, l3 = cat_of(f)
        if not cat:
            continue
        pg = f.get('page') or 1
        pos[pg] = pos.get(pg, 0) + 1
        cur = f.get('currency') or ''
        author = f.get('author_count')
        note = ('FastMoss·TikTok %s（美妆个护，第%s页第%d位）；国家/地区=%s；店铺=%s；类目=%s；佣金比例=%s；'
                '上架时间=%s；'
                '口径：当期销量 %s 件、销量环比 %s、销售额 %s%s、总销量 %s 件、总销售额 %s%s；'
                '关联达人数 %s（累计 %s）、关联视频 %s、关联直播 %s；'
                '价格与销售额因多币种未折算暂不入库（海外价折算汇率待定），原始展示价 %s'
                % (KIND_CN[kind], pg, pos[pg], f.get('region'), f.get('shop_name'), ' / '.join(f.get('all_category_name') or []),
                   f.get('commission_rate') or '—', f.get('launch_time') or '—',
                   fmt_num(f.get('sold_count')), f.get('sold_count_inc_rate') or '—',
                   fmt_num(f.get('sale_amount')), cur,
                   fmt_num(f.get('total_sold_count')), fmt_num(f.get('total_sale_amount')), cur,
                   fmt_num(author), fmt_num(f.get('total_author_count')),
                   fmt_num(f.get('aweme_count')), fmt_num(f.get('live_count')),
                   f.get('real_price') or '—'))
        rec = {
            '商品名称': f.get('title', ''),
            '品牌': brand_of(f.get('shop_name')),
            '商品ID': str(f.get('product_id') or ''),
            '品类': cat,
            '细分品类': l3 or l2,
            '价格': None,
            '数据来源': 'FastMoss',
            '所属市场': REGION_CODE.get(f.get('region'), ''),
            '榜单排名': 'FastMoss %s 第%s页第%d位（美妆个护·%s）' % (KIND_CN[kind], pg, pos[pg], f.get('region')),
            '销量': f.get('sold_count'),
            '销售额': None,
            '环比增速': num_of(f.get('sold_count_inc_rate')),
            '关联达人数': author,
            '数据标记': '真实',
            '决策状态': '待评',
            '选品笔记': note,
        }
        if f.get('launch_time'):
            rec['上市日期'] = str(f['launch_time'])[:10] + 'T00:00:00Z'
        records.append(rec)

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

print('写入', OUT, '共', len(dedup), '条')
print('按来源:', dict(collections.Counter(r['数据来源'] for r in dedup)))
print('按市场:', dict(collections.Counter(r['所属市场'] or '(空)' for r in dedup)))
print('按品类:', dict(collections.Counter(r['品类'] or '(空)' for r in dedup)))
print('有关联达人数:', sum(1 for r in dedup if r['关联达人数'] is not None))
print('有环比:', sum(1 for r in dedup if r['环比增速'] is not None),
      '| 有价格:', sum(1 for r in dedup if r['价格'] is not None),
      '| 有销售额:', sum(1 for r in dedup if r['销售额'] is not None),
      '| 有上市日期:', sum(1 for r in dedup if r.get('上市日期')))
g = [r['环比增速'] for r in dedup if r['环比增速'] is not None]
if g:
    print('环比≥60 的条数:', sum(1 for x in g if x >= 60), '| 环比<0 的条数:', sum(1 for x in g if x < 0))
