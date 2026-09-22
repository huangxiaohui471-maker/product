#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把三平台原始抽取结果规范化为「全球新品库」33 字段记录。

口径（与本项目一致，务必保持）：
- 区间值（如「2.5万 - 5万」）取**中值**，原始区间写进选品笔记；
- 多币种不折算：FastMoss 记录的 价格 / 销售额 **留空**，原始币种数值写进笔记；
  原因：海外价折算汇率是用户尚未拍板的口径（见 MEMORY.md 待拍板项 1）。
- 销量保留各平台原始口径（FastMoss=销量榜当期、蝉妈妈=日销量、罗盘=近7天成交件数），
  并在笔记中写明口径，不做跨口径求和假设。
"""
import json
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
OUT = os.path.join(D, 'records.json')

MARKET = {
    '越南': '东南亚', '印尼': '东南亚', '印度尼西亚': '东南亚', '泰国': '东南亚',
    '菲律宾': '东南亚', '马来西亚': '东南亚', '新加坡': '东南亚',
    '美国': '欧美', '英国': '欧美', '德国': '欧美', '法国': '欧美', '意大利': '欧美',
    '西班牙': '欧美', '墨西哥': '欧美', '巴西': '欧美',
    '日本': '日本', '韩国': '韩国',
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
        ('香氛', r'香水|香氛|fragrance|perfume|parfum|nước hoa|kit reve'),
        ('彩妆', r'口红|唇膏|唇釉|唇泥|唇彩|粉底|遮瑕|眼影|眼线|腮红|睫毛|眉笔|眉膏|染眉|气垫|散粉|蜜粉|定妆|粉饼|bb霜|cc霜'
                 r'|lipstick|mascara|foundation|blush|concealer|eyeshadow|eyeliner|bulu mata|bút phấn mắt|bút kẻ'
                 r'|ดินสอ|เขียนคิ้ว'),
        ('工具', r'美甲|指甲|化妆刷|粉扑|美妆蛋|睫毛夹|修眉|刮眉|nail|brush|pemotong|cukur|กันคิ้ว|โกนคิ้ว|hair clipper'
                 r'|móng|dầu dưỡng móng'),
        ('身体', r'身体乳|身体霜|身体护理|磨砂|护手霜|护足|颈霜|body lotion|body cream|body scrub|hand cream'
                 r'|zaitun|olive oil|perawatan tubuh|dưỡng thể'),
        ('个护', r'沐浴|洗发|护发|牙膏|牙刷|香皂|洗手|剃须|脱发|grooming'
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
    """'2.06万' -> 20600 ; '29.66%' -> 29.66 ; '1,234' -> 1234"""
    if text is None:
        return None
    s = str(text).strip()
    if not s or s in ('-', '—', '**'):
        return None
    s = s.replace(',', '').replace(' ', '')
    s = re.sub(r'^[^\d\-+]+', '', s)          # 去币种符号
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
    """'2.5万 - 5万' -> (mid, raw) ; '¥100万 - ¥250万' -> (mid, raw)"""
    raw = (text or '').strip()
    if not raw:
        return None, ''
    parts = re.split(r'\s*[-–~]\s*', raw.replace('¥', '¥')) if '-' in raw or '~' in raw else [raw]
    nums = [num_of(p) for p in parts]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None, raw
    if len(nums) == 1:
        return nums[0], raw
    return int(round(sum(nums) / len(nums))), raw


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


records = []

# ---------------- 1. 抖音罗盘 · 商品TOP200（中国） ----------------
dp = json.load(open(os.path.join(D, 'douyin_compass_rank.json'), encoding='utf-8'))
for r in dp['rows']:
    sales, sales_raw = range_mid(r.get('orders'))
    gmv, gmv_raw = range_mid(r.get('gmv'))
    band = r.get('price_band') or ''
    pb_nums = [num_of(x) for x in re.split(r'\s*-\s*', band) if num_of(x) is not None]
    price = min(pb_nums) if pb_nums else None
    note = ('抖音罗盘·商品TOP200（%s，行业类目：个护家清/个人护理/身体清洁/沐浴露·油·乳）；'
            '店铺=%s；店铺名称≠品牌，品牌为店铺名去渠道后缀所得；'
            '榜单展示区间：用户支付金额 %s、成交件数 %s（已取中值）；点击成交转化率 %s；价格带展示为 %s'
            % (dp.get('range', ''), r.get('shop', ''), gmv_raw or '—', sales_raw or '—',
               r.get('conv', '—'), band or '—'))
    records.append({
        '商品名称': r.get('name', ''),
        '品牌': brand_of(r.get('shop', '')),
        '商品ID': '',
        '品类': '个护',
        '细分品类': '沐浴露/油/乳',
        '价格': price,
        '数据来源': '抖音罗盘',
        '所属市场': '中国',
        '榜单排名': '抖音商品TOP200 第%d名（个护家清·沐浴露/油/乳，近7天）' % r['idx'],
        '销量': sales,
        '销售额': gmv,
        '环比增速': None,
        '关联达人数': None,
        '评分': None,
        '评价数': None,
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
            '口径：日销量 %s 件、日销售额 ¥%s（平台明文值）；'
            '近1年销量 %s 件；30天转化率 %s；%s；'
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
        '销量': qty,
        '销售额': amt,
        '环比增速': growth,
        '关联达人数': None,
        '评分': None,
        '评价数': None,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    })

# ---------------- 3. FastMoss 销量榜（海外，含销量环比） ----------------
fm = json.load(open(os.path.join(D, 'fastmoss_sales.json'), encoding='utf-8'))
H = fm['heads']


def cell(row, name):
    try:
        return row['cells'][H.index(name)]
    except Exception:
        return ''


for r in fm['rows']:
    country = cell(r, '国家/地区')
    mk = MARKET.get(country, '')
    qty = num_of(cell(r, '销量'))
    growth = num_of(cell(r, '销量环比'))
    pcat = cell(r, '商品分类')
    note = ('FastMoss·销量榜（美妆个护类目，第%d页第%d位）；国家/地区=%s；店铺=%s；商品分类=%s；佣金比例=%s；'
            '口径：当期销量 %s 件、销量环比 %s、销售额 %s、总销量 %s、总销售额 %s；'
            '价格与销售额因多币种未折算暂不入库（海外价折算汇率待定），原始币种数值见上'
            % (r.get('page'), (fm['rows'].index(r) % 10) + 1, country, cell(r, '所属店铺'), pcat,
               cell(r, '佣金比例') or '—', cell(r, '销量') or '—', cell(r, '销量环比') or '—',
               cell(r, '销售额') or '—', cell(r, '总销量') or '—', cell(r, '总销售额') or '—'))
    records.append({
        '商品名称': re.sub(r'\s*售价：.*$', '', cell(r, '商品')).strip(),
        '品牌': brand_of(cell(r, '所属店铺')),
        '商品ID': r.get('productId', ''),
        '品类': CAT_BY_PLATFORM_CAT.get(pcat) or cat_by_title(cell(r, '商品')),
        '细分品类': pcat,
        '价格': None,
        '数据来源': 'FastMoss',
        '所属市场': mk,
        '榜单排名': 'FastMoss销量榜 第%d页第%d位（美妆个护·%s）' % (r.get('page'), (fm['rows'].index(r) % 10) + 1, country),
        '销量': qty,
        '销售额': None,
        '环比增速': growth,
        '关联达人数': None,
        '评分': None,
        '评价数': None,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    })

# ---------------- 4. FastMoss 新品榜（海外，带上架时间） ----------------
ne = json.load(open(os.path.join(D, 'fastmoss_new.json'), encoding='utf-8'))
NH = ne['heads']
skipped = []
for i, r in enumerate(ne['rows']):
    c = r['cells']
    if len(c) < len(NH):
        continue
    g = lambda n: c[NH.index(n)] if n in NH else ''
    country = g('国家/地区')
    title_raw = g('商品')
    if not title_raw:
        continue
    mUp = re.search(r'上架时间：(\d{4}-\d{2}-\d{2})', title_raw)
    mPrice = re.search(r'售价：([^\s上]+(?:\s*-\s*[^\s上]+)?)', title_raw)
    cat = CAT_BY_PLATFORM_CAT.get(g('商品分类')) or cat_by_title(title_raw)
    if not cat:
        # FastMoss 新品榜的「商品分类」多为笼统的「美妆个护」，标题又无法判定品类时
        # 无法确认它属于六类中的哪一类（如足球贴纸被归进美妆个护），不入库，避免污染选品库
        skipped.append((g('商品分类'), title_raw[:60]))
        continue
    note = ('FastMoss·新品榜（美妆个护，第%d页第%d位）；国家/地区=%s；店铺=%s；商品分类=%s；'
            '上架时间=%s；售价=%s（多币种未折算，价格字段留空）；'
            '口径：三日销量 %s、三日销售额 %s、总销量 %s、总销售额 %s；店铺销量 %s'
            % (r.get('page'), (i % 10) + 1, country, g('所属店铺'), g('商品分类'),
               mUp.group(1) if mUp else '—', mPrice.group(1) if mPrice else '—',
               g('三日销量') or '—', g('三日销售额') or '—', g('总销量') or '—', g('总销售额') or '—',
               re.sub(r'.*店铺销量：', '', g('所属店铺')) or '—'))
    records.append({
        '商品名称': re.sub(r'\s*(售价|上架时间)：.*$', '', title_raw).strip(),
        '品牌': brand_of(g('所属店铺')),
        '商品ID': r.get('productId', ''),
        '品类': cat,
        '细分品类': g('商品分类'),
        '价格': None,
        '数据来源': 'FastMoss',
        '所属市场': MARKET.get(country, ''),
        '榜单排名': 'FastMoss新品榜 第%d页第%d位（美妆个护·%s）' % (r.get('page'), (i % 10) + 1, country),
        '上市日期': (mUp.group(1) + 'T00:00:00Z') if mUp else None,
        '销量': num_of(g('总销量')),
        '销售额': None,
        '环比增速': None,
        '关联达人数': None,
        '评分': None,
        '评价数': None,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    })

# 去重（按商品名称）
seen, dedup = set(), []
for r in records:
    k = r['商品名称']
    if not k or k in seen:
        continue
    seen.add(k)
    dedup.append(r)

json.dump({'count': len(dedup), 'records': dedup}, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

import collections
print('写入', OUT, '共', len(dedup), '条')
print('按来源:', dict(collections.Counter(r['数据来源'] for r in dedup)))
print('按市场:', dict(collections.Counter(r['所属市场'] or '(空)' for r in dedup)))
print('按品类:', dict(collections.Counter(r['品类'] or '(空)' for r in dedup)))
print('有环比:', sum(1 for r in dedup if r['环比增速'] is not None),
      '| 有价格:', sum(1 for r in dedup if r['价格'] is not None),
      '| 有销售额:', sum(1 for r in dedup if r['销售额'] is not None))
print('FastMoss新品榜因无法判定品类而跳过:', len(skipped))
for c, t in skipped:
    print('   -', c, '|', t)
