#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2：三平台真实数据 → 「全球新品库」33 字段记录（含关联达人数）。

数据源（全部为平台真实数据，非示例）：
- data/douyin_compass_fiber.json  抖音罗盘·商品榜单（fiber，含精确数值/商品ID/真实价格）
- data/chanmama_beauty.json       蝉妈妈·抖音商品销量榜（Vue dataList 明文值）
- data/fastmoss_sales_fiber.json  FastMoss·TikTok销量榜（fiber，含 author_count）
- data/fastmoss_new_fiber.json    FastMoss·TikTok新品榜（fiber，含 author_count）

口径：
- 区间值取中值（罗盘直接用 fiber 的上下界数值求中，比解析文本更准）；
- 多币种不折算：FastMoss 的价格/销售额留空，原始币种数值写进选品笔记（汇率待用户拍板）；
- FastMoss 游客态返回全类目榜 → 本地只保留 all_category_name[0] == '美妆个护' 的记录，杜绝污染；
- 销量保留各平台原始口径并在笔记里写明。
"""
import collections
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
OUT = os.path.join(D, 'records_v2.json')

REGION_CODE = {
    'VN': '东南亚', 'ID': '东南亚', 'TH': '东南亚', 'PH': '东南亚',
    'MY': '东南亚', 'SG': '东南亚',
    'US': '欧美', 'GB': '欧美', 'DE': '欧美', 'FR': '欧美', 'IT': '欧美', 'ES': '欧美',
    'MX': '欧美', 'BR': '欧美', 'CA': '欧美', 'AU': '欧美',
    'JP': '日本', 'KR': '韩国',
}

# FastMoss / TikTok 二级类目 → 本站六大品类
FM_L2 = {
    '美容护肤': '护肤', '面部护理': '护肤', '身体护理': '身体',
    '洗浴与身体护理': '个护', '沐浴露与香皂': '个护', '头部护理与造型': '个护',
    '洗发护发': '个护', '头发与头皮养护': '个护', '鼻子口腔护理': '个护',
    '美妆': '彩妆', '化妆': '彩妆', '眼妆': '彩妆', '唇妆': '彩妆', '美甲': '彩妆',
    '香水': '香氛', '男女通用香水': '香氛',
    '美容、个护电器': '工具', '美容工具': '工具',
    '手足及指甲护理': '身体', '手足膜': '身体',
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
                 r'|móng|dầu dưỡng móng|电动|仪器|按摩仪|脱毛仪'),
        ('身体', r'身体乳|身体霜|身体护理|磨砂|护手霜|护足|颈霜|body lotion|body cream|body scrub|hand cream'
                 r'|zaitun|olive oil|perawatan tubuh|dưỡng thể'),
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


def price_mid(text):
    """'¥69' -> 69 ; '¥89-¥169' -> 129"""
    if not text:
        return None
    nums = [num_of(x) for x in re.split(r'[-–~]', str(text).replace('¥', ' '))]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None
    return int(round(sum(nums) / len(nums)))


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
    if not ts:
        return None
    try:
        import datetime
        return datetime.datetime.utcfromtimestamp(int(ts)).strftime('%Y-%m-%dT00:00:00Z')
    except Exception:
        return None


records = []
stat = collections.Counter()

# ---------------- 1. 抖音罗盘 · 商品榜单（中国，fiber 精确值） ----------------
dp = json.load(open(os.path.join(D, 'douyin_compass_fiber.json'), encoding='utf-8'))
rng = dp.get('meta', {}).get('range', '')
for r in dp['rows']:
    price = price_mid(r.get('price_bin'))
    note = ('抖音罗盘·商品榜单 第%s名（行业类目：个护家清/个人护理/身体清洁/沐浴露·油·乳；统计周期 %s）；'
            '店铺=%s；店铺名称≠品牌，品牌为店铺名去渠道后缀所得；'
            '口径：用户支付金额 %s、成交件数 %s、点击次数 %s、点击成交转化率 %s%%（区间取中值）；'
            '商品价格=%s（平台展示价）；商品ID=%s；%s'
            % (r.get('rank'), rng, r.get('shop_name'), fmt_num(r.get('gmv_mid')), fmt_num(r.get('orders_mid')),
               fmt_num(r.get('clicks_mid')), r.get('conv_mid'),
               r.get('price_bin') or '—', r.get('product_id'),
               '本期新上榜' if r.get('newly_on_ranking') else '非新上榜'))
    records.append({
        '商品名称': r.get('name', ''),
        '品牌': brand_of(r.get('shop_name')),
        '商品ID': str(r.get('product_id') or ''),
        '品类': '个护',
        '细分品类': '沐浴露/油/乳',
        '价格': price,
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
stat['抖音罗盘'] = len(dp['rows'])

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
        '上市日期': ts_date(r.get('first_crawl_time')),
        '销量': qty,
        '销售额': amt,
        '环比增速': growth,
        '关联达人数': None,
        '数据标记': '真实',
        '决策状态': '待评',
        '选品笔记': note,
    })
stat['蝉妈妈'] = len(cm['rows'])


# ---------------- 3 & 4. FastMoss（海外，fiber 全字段） ----------------
def fm_common(r, kind_text):
    ac = r.get('all_category_name') or []
    l2 = ac[1] if len(ac) > 1 else ''
    cat = FM_L2.get(l2) or CAT_BY_PLATFORM_CAT.get(l2) or cat_by_title(r.get('title', ''))
    return l2, cat


def fm_add(path, kind_text, qty_field):
    d = json.load(open(os.path.join(D, path), encoding='utf-8'))
    kept = 0
    for r in d['rows']:
        ac = r.get('all_category_name') or []
        if not ac or ac[0] != '美妆个护':
            continue          # 游客态全类目榜 → 只留美妆个护，杜绝污染
        l2, cat = fm_common(r, kind_text)
        if not cat:
            continue
        mk = REGION_CODE.get(r.get('region'), '')
        qty = r.get(qty_field)
        growth = num_of(r.get('sold_count_inc_rate'))
        note = ('FastMoss·%s（TikTok，全类目榜筛出美妆个护，第%d页）；国家/地区=%s；店铺=%s；类目=%s；'
                '佣金比例=%s；上架时间=%s；'
                '口径：当期销量 %s 件、销量环比 %s、销售额 %s%s、总销量 %s 件、总销售额 %s%s；'
                '关联达人数 %s（累计 %s）；关联视频 %s、关联直播 %s；'
                '价格与销售额因多币种未折算暂不入库（海外价折算汇率待定），原始数值见上'
                % (kind_text, r.get('page'), r.get('region'), r.get('shop_name'),
                   ' / '.join(ac), r.get('commission_rate') or '—', r.get('launch_time') or '—',
                   fmt_num(r.get('sold_count')), r.get('sold_count_inc_rate') or '—',
                   fmt_num(r.get('sale_amount')), r.get('currency') or '',
                   fmt_num(r.get('total_sold_count')), fmt_num(r.get('total_sale_amount')), r.get('currency') or '',
                   fmt_num(r.get('author_count')), fmt_num(r.get('total_author_count')),
                   fmt_num(r.get('aweme_count')), fmt_num(r.get('live_count'))))
        rec = {
            '商品名称': r.get('title', ''),
            '品牌': brand_of(r.get('shop_name')),
            '商品ID': str(r.get('product_id') or ''),
            '品类': cat,
            '细分品类': l2,
            '价格': None,
            '数据来源': 'FastMoss',
            '所属市场': mk,
            '榜单排名': 'FastMoss·TikTok%s 第%d页（全类目筛美妆个护·%s）' % (kind_text, r.get('page'), r.get('region')),
            '销量': qty,
            '销售额': None,
            '环比增速': growth,
            '关联达人数': r.get('author_count'),
            '数据标记': '真实',
            '决策状态': '待评',
            '选品笔记': note,
        }
        if r.get('launch_time'):
            rec['上市日期'] = str(r['launch_time'])[:10] + 'T00:00:00Z'
        records.append(rec)
        kept += 1
    stat['FastMoss·' + kind_text] = kept
    stat['FastMoss·%s·原始行' % kind_text] = len(d['rows'])


fm_add('fastmoss_sales_fiber.json', '销量榜', 'sold_count')
fm_add('fastmoss_new_fiber.json', '新品榜', 'sold_count')

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
print('明细:', dict(stat))
