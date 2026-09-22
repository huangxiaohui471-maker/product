#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""眼油要素拆解报告 v2：一级类目 → 二级类目两级拆解 + 计算逻辑佐证。
升级点（相对 v1）：
  ① 功效/形态/价格带 三个章节改为两级类目（L1 大类 → L2 细分功能点/子形态/子价位）；
  ② 每个二级组头部展示：命中关键词词表 + n 条 + 周销合计 + GMV 合计 + 占类目 GMV 比（佐证可复算）；
  ③ 页首新增「计算逻辑」说明块（归类口径、统计公式、数据源）。
输入: eyeoil/rank_fiber_img.json + factsheet.json + summary.json + details/ + directions.json
输出: eyeoil/眼油_要素拆解_产品清单.html（覆盖 v1）
"""
import json
import os
import re
import html as H

BASE = os.path.dirname(os.path.abspath(__file__))
EYE = os.path.join(BASE, 'eyeoil')

rank_rows = json.load(open(os.path.join(EYE, 'rank_fiber_img.json'), encoding='utf-8'))['rows']
fs = json.load(open(os.path.join(EYE, 'factsheet.json'), encoding='utf-8'))
summary = json.load(open(os.path.join(EYE, 'summary.json'), encoding='utf-8'))
directions = json.load(open(os.path.join(EYE, 'directions.json'), encoding='utf-8'))['directions']

# ---------- 合并产品主档 ----------
prods = {}
for r in rank_rows:
    pid = str(r.get('product_id') or '')
    if pid and pid not in prods:
        prods[pid] = r
for it in fs['items']:
    pid = str(it['id'])
    if pid in prods:
        prods[pid]['elements'] = it.get('elements', {})
        prods[pid]['missing'] = it.get('missing', [])

TOTAL_GMV = sum(p.get('gmv_mid') or 0 for p in prods.values())
TOTAL_ORD = sum(p.get('orders_mid') or 0 for p in prods.values())

# 头部详情页评价标签
detail_tags = {}
for fn in os.listdir(os.path.join(EYE, 'details')):
    pid = fn.replace('.txt', '')
    t = open(os.path.join(EYE, 'details', fn), encoding='utf-8').read()
    m = re.search(r'商品评价 \(([\d.w]+)\)', t)
    tags = re.findall(r'([一-龥]{2,6}) (\d[\d.w]*)', t)
    tags = [x for x in tags if x[0] not in ('回头客', '商品评价', '买家秀', '服务保障')][:8]
    detail_tags[pid] = {'n': m.group(1) if m else '', 'tags': tags}

def el(p, key):
    e = p.get('elements') or {}
    v = e.get(key)
    if v is None:
        return [] if key != '产品内料形态' else ''
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return v.get('维度') or []
    return v

def price_lo(p):
    m = re.search(r'([\d.]+)', p.get('price_bin') or '')
    return float(m.group(1)) if m else None

def band_of(v):
    if v is None: return None
    if v < 60: return '<60 元'
    if v < 100: return '60-100 元'
    if v < 200: return '100-200 元'
    if v < 400: return '200-400 元'
    return '400+ 元'

def wan_fen(x):
    if not x: return '0'
    return '%.0f' % (x / 100.0 / 10000.0)

def wan_jian(x):
    if not x: return '0'
    if x >= 10000:
        return '%.1f万' % (x / 10000.0)
    return '%.0f' % x

def esc(s):
    return H.escape(str(s or ''))

# ---------- 组统计（佐证用，可复算） ----------
def gstats(plist):
    n = len(plist)
    orders = sum(p.get('orders_mid') or 0 for p in plist)
    gmv = sum(p.get('gmv_mid') or 0 for p in plist)
    share = gmv / TOTAL_GMV * 100 if TOTAL_GMV else 0
    return {'n': n, 'orders': orders, 'gmv': gmv, 'gmv_share': share}

def gstats_text(st):
    return ('%d 条 · 周销合计 ~%s件 · GMV合计 ~%s万分 · 占类目 GMV <b>%.1f%%</b>'
            % (st['n'], wan_jian(st['orders']), wan_fen(st['gmv']), st['gmv_share']))

# ---------- 商品卡 ----------
def card(p, hi_values, hi_key):
    img = p.get('image_url') or ''
    name = esc(p.get('name'))
    shop = esc(p.get('shop_name'))
    price = esc(p.get('price_bin'))
    rank = p.get('rank')
    gmv = wan_fen(p.get('gmv_mid'))
    orders = wan_jian(p.get('orders_mid'))
    new_badge = '<span class="new">新上榜</span>' if p.get('newly_on_ranking') else ''
    tags = []
    form = el(p, '产品内料形态')
    if form:
        tags.append(('形态', form))
    for c in el(p, '主打成分')[:2]:
        tags.append(('成分', c))
    for s in el(p, '规格')[:1]:
        tags.append(('规格', s))
    for sc in el(p, '香型')[:1]:
        tags.append(('香型', sc))
    tag_html = ''
    for kind, val in tags:
        cls = 'tag hi' if (kind == hi_key and val in hi_values) or (hi_key == '产品内料形态' and kind == '形态' and val in hi_values) else 'tag'
        tag_html += '<span class="%s">%s</span>' % (cls, esc(val))
    img_html = ('<img loading="lazy" referrerpolicy="no-referrer" src="%s" onerror="this.parentNode.classList.add(\'noimg\');this.remove()">' % esc(img)) if img else ''
    return ('<div class="card"><div class="thumb">%s<span class="rk">%s</span></div>'
            '<div class="cbody"><div class="nm" title="%s">%s</div>'
            '<div class="shop">%s %s</div>'
            '<div class="nums"><b class="pr">%s</b><span>周销~%s件</span><span>GMV~%s万</span></div>'
            '<div class="tags">%s</div></div></div>'
            % (img_html, rank, name, name[:46], shop, new_badge, price, orders, gmv, tag_html))

def weighted_share(key, val):
    for row in summary['elements'].get(key, {}).get('rows', []):
        if row.get('value') == val:
            return row.get('weighted_share', 0)
    return 0

# ---------- 两级章节渲染 ----------
def section2(sid, title, share_line, logic, note, l1_groups):
    """l1_groups: [(l1名, l1统计行, [(l2名, l2关键词说明, [prods])])]"""
    out = ['<section id="%s" class="page"><h2>%s</h2><div class="share">%s</div>'
           '<div class="logic">%s</div><p class="note">%s</p>' % (sid, esc(title), share_line, logic, note)]
    for l1, l1stat, l2s in l1_groups:
        out.append('<div class="l1"><h3 class="l1h"><span class="gv">%s</span><span class="gs">%s</span></h3>'
                   % (esc(l1), l1stat))
        for l2, kw, plist in l2s:
            st = gstats(plist)
            cards = ''.join(card(p, [l1], '') for p in plist)
            kw_html = '<span class="kw">%s</span>' % esc(kw) if kw else ''
            out.append('<div class="grp"><h4><span class="gv2">%s</span>%s<span class="gn">%s</span></h4>'
                       '<div class="grid">%s</div></div>'
                       % (esc(l2), kw_html, gstats_text(st), cards))
        out.append('</div>')
    out.append('</section>')
    return '\n'.join(out)

# ---------- 旧单级章节渲染（④-⑨沿用） ----------
def section1(sid, title, share_line, note, groups):
    out = ['<section id="%s" class="page"><h2>%s</h2><div class="share">%s</div><p class="note">%s</p>' % (sid, esc(title), share_line, note)]
    for val, stat, plist, hi_key in groups:
        cards = ''.join(card(p, [val], hi_key) for p in plist)
        out.append('<div class="grp"><h3><span class="gv">%s</span><span class="gs">%s</span>'
                   '<span class="gn">%d 条</span></h3><div class="grid">%s</div></div>'
                   % (esc(val), esc(stat), len(plist), cards))
    out.append('</section>')
    return '\n'.join(out)

def group_by(key, values_order=None, min_n=1):
    g = {}
    for p in prods.values():
        v = el(p, key)
        vs = v if isinstance(v, list) else ([v] if v else [])
        for x in vs:
            if x:
                g.setdefault(x, []).append(p)
    items = [(k, sorted(v, key=lambda p: p.get('rank') or 999)) for k, v in g.items() if len(v) >= min_n]
    if values_order:
        order = {v: i for i, v in enumerate(values_order)}
        items.sort(key=lambda kv: (order.get(kv[0], 99), -len(kv[1])))
    else:
        items.sort(key=lambda kv: -len(kv[1]))
    return items

def stat_text(key, val):
    return '加权份额 %.1f%%' % weighted_share(key, val) if weighted_share(key, val) else ''

def text_of(p):
    return (p.get('name') or '') + ' ' + ((p.get('elements') or {}).get('一句话卖点') or '')

secs = []

# ================= ① 功效（两级） =================
L2_EFF = {
    '抗皱淡纹': ['抗皱', '淡纹', '细纹', '皱纹', '鱼尾纹', '抚纹'],
    '紧致提拉': ['紧致', '提拉', '紧塑', '抗垮', '松弛', '嘭弹', '弹嫩', '反重力', '大眼', '童颜'],
    '眼袋浮肿': ['眼袋', '浮肿', '肿眼泡', '消肿'],
    '保湿滋润': ['保湿', '滋润', '水润', '补水', '润养'],
    '舒缓修护': ['舒缓', '修护', '修复', '敏感肌', '屏障', '维稳'],
    '黑眼圈提亮': ['黑眼圈', '提亮', '焕亮', '暗沉', '明眸', '晶耀'],
    '睫毛眉毛护理': ['睫毛', '眉毛', '纤长'],
    '胶原水光充盈': ['胶原', '水光', '原液'],
    '舒缓润眼（非护肤）': ['润眼', '护眼'],
}

def l2_split(plist, l2_names):
    """把一组产品按 L2 词表再拆；返回 [(l2名, 词表说明, [prods])]，末尾补「未写明」。"""
    buckets = {k: [] for k in l2_names}
    rest = []
    for p in plist:
        t = text_of(p)
        hit = [k for k in l2_names if any(w in t for w in L2_EFF[k])]
        if hit:
            for k in hit:
                buckets[k].append(p)
        else:
            rest.append(p)
    out = []
    for k in l2_names:
        ps = sorted(buckets[k], key=lambda p: p.get('rank') or 999)
        if ps:
            out.append((k, '词表：' + ' / '.join(L2_EFF[k]), ps))
    if rest:
        out.append(('未写明功效点', '标题与卖点均未命中上述词表（多为形态/成分驱动型商品）',
                    sorted(rest, key=lambda p: p.get('rank') or 999)))
    return out

EFF_L1 = [
    ('抗老抗皱', ['抗皱淡纹', '紧致提拉', '眼袋浮肿']),
    ('保湿滋润', ['保湿滋润']),
    ('舒缓修护', ['舒缓修护']),
    ('美白提亮', ['黑眼圈提亮']),
]
eff_tagged = {}
for p in prods.values():
    for t in el(p, '功效'):
        eff_tagged.setdefault(t, []).append(p)
untagged_eff = sorted([p for p in prods.values() if not el(p, '功效')], key=lambda p: p.get('rank') or 999)

eff_l1_groups = []
for l1, l2names in EFF_L1:
    ps = sorted(eff_tagged.get(l1, []), key=lambda p: p.get('rank') or 999)
    st = gstats(ps)
    l1stat = '加权份额 %.1f%% ｜ %s' % (weighted_share('功效', l1), gstats_text(st))
    eff_l1_groups.append((l1, l1stat, l2_split(ps, l2names)))
st_un = gstats(untagged_eff)
eff_l1_groups.append(('未打功效标签', '%s' % gstats_text(st_un),
                      l2_split(untagged_eff, ['睫毛眉毛护理', '胶原水光充盈', '舒缓润眼（非护肤）'])))

secs.append(section2('eff', '① 功效：一级类目 → 二级功能点拆解',
    f'一级：抗老抗皱 <b>65.5%</b>（63 条）· 保湿滋润 <b>39.6%</b>（36 条）· 舒缓修护 12.8%（11 条）· 美白提亮 7.3%（7 条）· 未打功效标签 {len(untagged_eff)} 条｜份额按销量+评价+GMV 加权',
    '<b>计算逻辑（佐证口径）</b>：① 一级类目 = 要素抽取的四类功效标签（多标，一商品可属多个一级）；② 二级功能点 = 扫描「商品标题 + 一句话卖点」，命中词表即归入（一商品可命中多个二级，故各组条数之和 ≥ 一级条数）；③ 组统计 = 组内商品的罗盘区间中值直接求和，占类目比 = 组 GMV 合计 ÷ TOP100 GMV 合计（~%s万分）；④ 「未写明功效点」= 文本未命中任何词表，不等于产品没有该功效。' % wan_fen(TOTAL_GMV),
    '判读：抗皱淡纹与紧致提拉是同一批产品在打的双词（56/41 条高度重合），合起来就是「抗老」这个入场券；黑眼圈提亮 10 条、眼袋浮肿仅 1 条——眼周问题的细分诉求（黑眼圈/眼袋）供给明显不足，是二级类目里最值得注意的缺口；未打功效标签的 %d 条多为睫毛增长（乌斯曼草系）、胶原水光原液、润眼喷雾，严格说不是同一战场。' % len(untagged_eff),
    eff_l1_groups))

# ================= ② 形态（两级） =================
L2_FORM = {
    '滚珠': ['滚珠', '走珠'],
    '胶囊': ['胶囊'],
    '次抛': ['次抛'],
    '安瓶': ['安瓶'],
    '水油双相': ['双相', '水油'],
    '眼膜/贴片': ['眼膜', '贴片', '眼贴'],
    '喷雾': ['喷雾'],
}

def form_l2_split(plist, candidates):
    buckets = {k: [] for k in candidates}
    rest = []
    for p in plist:
        t = text_of(p)
        hit = [k for k in candidates if any(w in t for w in L2_FORM[k])]
        if hit:
            for k in hit:
                buckets[k].append(p)
        else:
            rest.append(p)
    out = []
    for k in candidates:
        ps = sorted(buckets[k], key=lambda p: p.get('rank') or 999)
        if ps:
            out.append((k, '词表：' + ' / '.join(L2_FORM[k]), ps))
    if rest:
        out.append(('瓶装/滴管（默认形态）', '未命中特殊包装词，按常规瓶装/滴管计',
                    sorted(rest, key=lambda p: p.get('rank') or 999)))
    return out

form_tagged = {}
for p in prods.values():
    f = el(p, '产品内料形态')
    if f:
        form_tagged.setdefault(f, []).append(p)
untagged_form = sorted([p for p in prods.values() if not el(p, '产品内料形态')], key=lambda p: p.get('rank') or 999)

FORM_L1 = [
    ('纯油（眼油）', ['纯油'], ['滚珠', '胶囊', '水油双相']),
    ('液体精华', ['液体'], ['次抛', '安瓶', '滚珠']),
    ('水状精华', ['水'], ['次抛', '安瓶']),
    ('霜/乳/膏/凝胶', ['霜', '乳', '膏', '凝胶'], []),
    ('喷雾', ['喷雾'], []),
]
form_l1_groups = []
for l1, tags, l2c in FORM_L1:
    ps = []
    for t in tags:
        ps += form_tagged.get(t, [])
    ps = sorted({id(p): p for p in ps}.values(), key=lambda p: p.get('rank') or 999)
    if not ps:
        continue
    st = gstats(ps)
    ws = sum(weighted_share('产品内料形态', t) for t in tags)
    l1stat = '加权份额 %.1f%% ｜ %s' % (ws, gstats_text(st))
    form_l1_groups.append((l1, l1stat, form_l2_split(ps, l2c)))
st_uf = gstats(untagged_form)
form_l1_groups.append(('未写明形态', '%s' % gstats_text(st_uf),
                       form_l2_split(untagged_form, ['胶囊', '眼膜/贴片', '滚珠', '次抛'])))

secs.append(section2('form', '② 内料形态：一级形态 → 二级子形态（包装线索）',
    f'一级：纯油 <b>39.4%</b>（36 条）· 液体 14.1%（14 条）· 水状 10.8%（12 条）· 霜乳膏凝胶/喷雾合计 <10% · 未写明 {len(untagged_form)} 条',
    '<b>计算逻辑（佐证口径）</b>：① 一级形态 = 要素抽取的内料形态标签（单值）；② 二级子形态 = 扫描标题/卖点中的包装词（滚珠/胶囊/次抛/安瓶/双相/眼膜），未命中者归入「瓶装/滴管（默认形态）」——二级之和 = 一级条数（除多词命中外）；③ 组统计同功效节口径。',
    '判读：纯油 36 条里 <b>27 条是常规瓶装油</b>，滚珠油 3 条、胶囊油 1 条、双相 2 条——子形态创新才刚开始，谁先做出「油的形态创新」（滚珠/双相/次抛油）谁就有差异化；未写明形态的 %d 条里胶囊（CEMOY 眼膜胶囊 5 条）与眼膜贴片占大头，严格说不与眼油直接竞争。' % len(untagged_form),
    form_l1_groups))

# ================= ③ 价格带（两级） =================
SUB_BANDS = {
    '<60 元': [('<30 元', 0, 30), ('30-60 元', 30, 60)],
    '60-100 元': [('60-80 元', 60, 80), ('80-100 元', 80, 100)],
    '100-200 元': [('100-150 元', 100, 150), ('150-200 元', 150, 200)],
    '200-400 元': [('200-300 元', 200, 300), ('300-400 元', 300, 400)],
    '400+ 元': [('400-600 元', 400, 600), ('600+ 元', 600, 10**9)],
}
BAND_ORDER = ['<60 元', '60-100 元', '100-200 元', '200-400 元', '400+ 元']
BAND_NOTE = {
    '<60 元': '走量带：效妆一家独大（榜一，周销中值 17.5 万件），拼投流与供应链成本。',
    '60-100 元': '过渡带：多为白牌/工厂店，缺品牌叙事。',
    '100-200 元': '供给最薄：夹在走量与品牌之间，竞争压力最小的区间。',
    '200-400 元': '主流成交带：雏菊、林清轩、专妍、Kessetti 入门款都挤在这里，成分故事与套组结构是胜负手。',
    '400+ 元': '高端品牌带：雏菊 2.0、Kessetti ¥2180、薇旖美 ¥1380——原料商背书与品牌调性支撑溢价。',
}
band_l1_groups = []
for b in BAND_ORDER:
    ps = sorted([p for p in prods.values() if band_of(price_lo(p)) == b], key=lambda p: p.get('rank') or 999)
    st = gstats(ps)
    l1stat = '%s ｜ %s' % (BAND_NOTE[b], gstats_text(st))
    l2s = []
    for name, lo, hi in SUB_BANDS[b]:
        sub = sorted([p for p in ps if (price_lo(p) or 0) >= lo and (price_lo(p) or 0) < hi],
                     key=lambda p: p.get('rank') or 999)
        if sub:
            l2s.append((name, '按标价下界 ∈ [%d, %s)' % (lo, '∞' if hi > 10**8 else str(hi)), sub))
    band_l1_groups.append((b, l1stat, l2s))

band_counts = ' · '.join('%s <b>%d</b> 条' % (b, len([p for p in prods.values() if band_of(price_lo(p)) == b])) for b in BAND_ORDER)
secs.append(section2('band', '③ 价格带：五档 → 细分价位',
    band_counts + '（按标价下界，n=100）',
    '<b>计算逻辑（佐证口径）</b>：① 价位取商品标价下界（如 ¥328-516 按 328 计）；② 一级 = 五档价格带；③ 二级 = 每档再对半细分子价位，子价位之和 = 所属档条数；④ 组统计同功效节口径——「占类目 GMV」能直接看出每档的钱在哪里。',
    '判读：哑铃结构在二级价位下更清晰——<60 元档的 GMV 高度集中在 30-60 元（效妆 ¥59）；200-400 档内部 200-300 与 300-400 分布能看清「品牌入门款 vs 主力款」的站位；600+ 是超高端（Kessetti/薇旖美），条数少但单链接 GMV 高。',
    band_l1_groups))

# ================= ④ 成分（沿用单级） =================
ING_ORDER = ['PDRN', '乌斯曼草', '精油', '胶原蛋白', '多肽', '山茶花', '咖啡因', '重组胶原蛋白', '胜肽', '蓝铜肽', '密罗木', '乳酸', '叶黄素', '卵磷脂', '晚香玉', '发酵']
ing_groups = [(v, stat_text('主打成分', v), ps, '主打成分') for v, ps in group_by('主打成分', ING_ORDER)]
secs.append(section1('ing', '④ 主打成分：成分阵营拆分',
    '精油 7 条 · 乌斯曼草 7 条 · PDRN 5 条（加权 6.2%）· 胶原蛋白 5 条 · 多肽 4 条｜成分覆盖率 40/100',
    '判读：成分故事三分天下——<b>PDRN</b>（再生医学叙事，效妆带火后 5 家快速跟进）；<b>乌斯曼草</b>（新疆产地叙事，7 条但同质化严重）；<b>经典多肽/重组胶原</b>（原料商背书路线）。山茶花、密罗木、蓝铜肽、叶黄素是单点差异化。注：只抽标题与详情显性词，60 条没写成分 ≠ 没有成分。',
    ing_groups))

# ================= ⑤ 包装（沿用单级） =================
PACK_ORDER = ['贴片', '盒装', '滚珠', '胶囊', '次抛', '瓶装', '袋装']
pack_groups = [(v, stat_text('包装形式', v), ps, '包装形式') for v, ps in group_by('包装形式', PACK_ORDER)]
secs.append(section1('pack', '⑤ 包装形式：滚珠/次抛/胶囊都是谁',
    '贴片 7 条 · 盒装/礼盒 6 条 · 滚珠 5 条（加权 5.3%）· 胶囊 5 条 · 次抛 4 条｜文本覆盖率 21/100',
    '判读：包装是眼油品类最活跃的创新点——<b>滚珠</b>（按摩+便携补涂）、<b>次抛</b>（锁鲜叙事）、<b>胶囊</b>（CEMOY 反重力系列）、<b>盒装/礼盒</b>（节点礼赠）。滚珠与「快速吸收」体验诉求天然绑定。',
    pack_groups))

# ================= ⑥ 香型（沿用单级） =================
SCENT_ORDER = ['东方调', '木质', '草本植物', '玫瑰', '茉莉', '茶香']
scent_groups = [(v, stat_text('香型', v), ps, '香型') for v, ps in group_by('香型', SCENT_ORDER)]
secs.append(section1('scent', '⑥ 香型：打香的 25 条都是谁',
    '东方调（琥珀）15 条（加权 15.7%）· 木质 3 · 草本 3 · 玫瑰 2 · 茉莉 1 · 茶香 1｜75 条未提香型',
    '判读：<b>不打香是主流</b>（75% 没写，眼周「无香=温和」是默认预期）。东方调基本是雏菊「琥珀时光」一个系列在贡献；玫瑰、檀香、茶香是单点。新品做无香或植物油本味即可。',
    scent_groups))

# ================= ⑦ 规格（沿用单级） =================
spec_groups = [(v, '', ps, '规格') for v, ps in group_by('规格')[:10]]
secs.append(section1('spec', '⑦ 规格：容量拆分',
    '8ml <b>8 条</b>（加权 7.9%，眼油基准规格）· 20ml 4 条 · 10ml 3 条 · 2ml 3 条（滚珠/随行装）｜文本覆盖率 21/100',
    '判读：<b>8ml 是雏菊全系列确立的基准规格</b>（双瓶 8ml×2 主力 SKU），配合「小容量+高频复购」。10-20ml 走性价比叙事，2ml 是滚珠随行装。>30ml 在榜内完全缺席。',
    spec_groups))

# ================= ⑧ SKU（沿用单级） =================
sku_groups = [(v, '', ps, 'SKU') for v, ps in group_by('SKU')]
secs.append(section1('sku', '⑧ SKU 结构：套组打法',
    '套装/套组 2 条 · 多件装 2 条 · 试用/旅行装 1 条 · 家庭装/大容量 1 条｜文本覆盖率仅 6/100',
    '判读：头部 SKU 打法收敛成两类——<b>双瓶/多瓶装拉客单</b>、<b>眼油+滚珠/眼膜组合装</b>；派样装用作短视频引流款。覆盖率低是数据源限制，不代表现状。',
    sku_groups))

# ================= ⑨ 体验（沿用单级） =================
exp_groups = [(v, stat_text('使用体验', v), ps, '使用体验') for v, ps in group_by('使用体验')]
secs.append(section1('exp', '⑨ 使用体验：评价标签里的真实体验点',
    '肤感滋润 11 条（加权 13.7%）· 快速吸收 2 条（<b>空白格第一</b>）· 温和不刺激 1 条',
    '判读：榜一效妆 18.1w 条评价给出体验铁三角——<b>很滋润(1.7w) / 不油腻(7532) / 好吸收(5229)</b>，这就是眼油肤感开发的验收标准。「快速吸收」文本供给极少但头部评价反复点名，是明确的体验空白。',
    exp_groups))

# 头部评价标签表
tag_rows = ''
for pid, d in sorted(detail_tags.items(), key=lambda kv: -(prods.get(kv[0], {}).get('gmv_mid') or 0)):
    p = prods.get(pid)
    if not p:
        continue
    tags = ' '.join('<span class="tag">%s %s</span>' % (esc(a), esc(b)) for a, b in d['tags'])
    tag_rows += ('<tr><td class="tname">%s</td><td>%s</td><td class="ttags">%s</td></tr>'
                 % (esc((p.get('name') or '')[:30]), esc(d['n']), tags))
tag_table = ('<table class="tagt"><thead><tr><th>头部商品</th><th>评价数</th><th>评价标签（买家原声聚类）</th></tr></thead><tbody>%s</tbody></table>' % tag_rows)
# 评价标签表并入「体验」页底部
secs = [s.replace('</section>', '<h3 style="margin-top:18px">附：头部商品评价标签（体验要素证据）</h3>' + tag_table + '</section>')
        if s.startswith('<section id="exp"') else s for s in secs]

# 方向卡
dir_html = ''
TYPE_CLS = {'主攻方向': 'main', '备选': 'alt', '观察项': 'watch'}
for d in directions:
    combo = ''.join('<div class="crow"><span class="ck">%s</span><span class="cv">%s</span></div>'
                    % (esc(k), esc('、'.join(v) if isinstance(v, list) else v))
                    for k, v in d['combo'].items())
    ev = ''.join('<li>%s</li>' % esc(x) for x in d['evidence'])
    dir_html += ('<div class="dcard %s"><div class="dtype">%s</div><h3>%s</h3>'
                 '<div class="persona">%s</div><div class="combo">%s</div>'
                 '<div class="dsub">依据</div><ul class="ev">%s</ul>'
                 '<div class="dsub">风险</div><p class="risk">%s</p>'
                 '<div class="dsub">下一步验证</div><p class="next">%s</p></div>'
                 % (TYPE_CLS.get(d.get('type'), 'alt'), esc(d.get('type', '')), esc(d['name']),
                    esc(d['persona']), combo, ev, esc(d['risk']), esc(d['next'])))

# ---------- 页面 ----------
NAV = [('ov', '总览'), ('eff', '① 功效'), ('form', '② 形态'), ('band', '③ 价格带'), ('ing', '④ 成分'), ('pack', '⑤ 包装'),
       ('scent', '⑥ 香型'), ('spec', '⑦ 规格'), ('sku', '⑧ SKU'), ('exp', '⑨ 体验'), ('dir', '研发方向')]
nav_html = ''.join('<a href="#%s">%s</a>' % (a, t) for a, t in NAV)

page = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>眼油要素拆解 v2 · 两级类目与产品清单（抖音罗盘眼部精华榜 TOP100）</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Helvetica Neue",sans-serif;background:#f5f6f8;color:#1f2329;padding-bottom:60px}
.hd{background:linear-gradient(135deg,#1a1f36,#2d3561);color:#fff;padding:28px 20px 22px}
.hd h1{font-size:20px;margin-bottom:8px}
.hd .meta{font-size:12.5px;opacity:.85;line-height:1.7}
.hd .meta b{color:#ffd666}
nav{position:sticky;top:0;z-index:50;background:#fff;display:flex;gap:4px;overflow-x:auto;padding:10px 12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
nav a{flex:0 0 auto;font-size:13px;color:#4e5569;text-decoration:none;padding:7px 13px;border-radius:16px;background:#f0f1f5;white-space:nowrap;cursor:pointer}
nav a:active{background:#2d3561;color:#fff}
nav a.on{background:#2d3561;color:#fff}
.tldr{background:#fff;margin:14px 12px 0;border-radius:12px;padding:16px}
.tldr h2{font-size:15px;margin-bottom:10px}
.tldr li{font-size:13px;line-height:1.8;margin-left:18px;margin-bottom:4px}
.tldr b{color:#c0392b}
section{margin:22px 12px 0}
section.page{display:none}
section.page.on{display:block}
section>h2{font-size:17px;margin-bottom:6px}
.share{font-size:12.5px;color:#8a4b08;background:#fff7e6;border:1px solid #ffe7ba;border-radius:8px;padding:8px 12px;line-height:1.7}
.share b{color:#c0392b}
.logic{font-size:12px;color:#5a6072;background:#eef1f8;border:1px dashed #b8c0d8;border-radius:8px;padding:8px 12px;line-height:1.8;margin-top:8px}
.logic b{color:#2d3561}
.note{font-size:13px;color:#4e5569;line-height:1.85;background:#fff;border-radius:10px;padding:12px 14px;margin-top:8px}
.note b{color:#c0392b}
.l1{margin-top:18px;border-left:3px solid #2d3561;padding-left:10px}
.l1h{font-size:15px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:4px}
.gv{background:#2d3561;color:#fff;padding:3px 10px;border-radius:6px;font-size:13px}
.gs{font-size:12px;color:#4e5569;font-weight:400;line-height:1.7}
.gs b{color:#c0392b}
.grp{margin-top:12px}
.grp h3,.grp h4{font-size:13.5px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.gv2{background:#e8ecf7;color:#2d3561;padding:2px 9px;border-radius:6px;font-size:12.5px;font-weight:700;border:1px solid #c9d2ea}
.kw{font-size:11px;color:#86909c;font-weight:400}
.gn{font-size:11.5px;color:#86909c;font-weight:400}
.gn b{color:#c0392b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:10px}
.card{background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;flex-direction:column}
.thumb{position:relative;aspect-ratio:1;background:linear-gradient(135deg,#e8eaf2,#f5f6fa) center/60px no-repeat}
.thumb.noimg::after{content:"无图";position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#c9cdd4;font-size:12px}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.rk{position:absolute;top:6px;left:6px;background:rgba(26,31,54,.85);color:#ffd666;font-size:11px;padding:2px 7px;border-radius:8px;font-weight:700}
.cbody{padding:8px 9px 9px;display:flex;flex-direction:column;gap:4px;flex:1}
.nm{font-size:12px;line-height:1.45;height:35px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.shop{font-size:11px;color:#86909c;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.new{background:#f53f3f;color:#fff;font-size:10px;padding:1px 5px;border-radius:4px;margin-left:4px}
.nums{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.pr{color:#f53f3f;font-size:15px}
.nums span{font-size:10.5px;color:#86909c}
.tags{display:flex;flex-wrap:wrap;gap:3px;margin-top:2px}
.tag{font-size:10px;background:#f0f1f5;color:#4e5569;padding:1.5px 6px;border-radius:4px}
.tag.hi{background:#ffece8;color:#f53f3f;font-weight:700}
.tagt{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;margin-top:10px;font-size:12px}
.tagt th,.tagt td{padding:9px 10px;border-bottom:1px solid #f0f1f5;text-align:left;vertical-align:top}
.tagt th{background:#f7f8fa;font-size:12px;color:#4e5569}
.tname{max-width:180px}
.ttags{line-height:2}
.dcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:12px}
.dcard{background:#fff;border-radius:12px;padding:16px;border-top:4px solid #86909c}
.dcard.main{border-top-color:#f53f3f}
.dcard.alt{border-top-color:#ff7d00}
.dcard.watch{border-top-color:#86909c}
.dtype{font-size:11px;color:#86909c;letter-spacing:2px}
.dcard h3{font-size:15.5px;margin:4px 0 6px}
.persona{font-size:12px;color:#4e5569;background:#f7f8fa;border-radius:6px;padding:6px 9px;margin-bottom:8px}
.combo{margin:6px 0}
.crow{display:flex;font-size:12px;line-height:1.9}
.ck{flex:0 0 76px;color:#86909c}
.cv{color:#1f2329;font-weight:600}
.dsub{font-size:12px;font-weight:700;color:#2d3561;margin:8px 0 4px}
.ev{font-size:12px;line-height:1.75;color:#4e5569;padding-left:16px}
.ev li{margin-bottom:3px}
.risk,.next{font-size:12px;line-height:1.75;color:#4e5569}
.risk{color:#a23b2e}
.foot{margin:26px 14px 0;font-size:11.5px;color:#86909c;line-height:1.9}
</style></head><body>
<div class="hd"><h1>眼油（眼部精华油）· 要素拆解 v2：两级类目与产品清单</h1>
<div class="meta">数据源：抖音电商罗盘 → 市场 → 商品榜单 → 个护家清/个人护理/眼部护理/<b>眼部精华</b>（总榜 TOP100）<br>
统计周期：<b>2026/09/14 - 2026/09/20</b>（近 7 天）｜样本 n=100，头部 15 商品附详情页评价标签（6 条达人专场链接已下架失效）<br>
一级类目份额 = 销量 0.5 + 评价 0.3 + GMV 0.2 归一加权｜二级类目占比 = 组 GMV 合计 ÷ 类目 GMV 合计（~__TOTAL_GMV__万分）</div></div>
<nav>__NAV__</nav>
<section id="ov" class="page"><div class="tldr" style="margin-top:14px"><h2>核心判读（先看这个）</h2><ul>
<li><b>抗皱是入场券不是差异点</b>：65.5% 的热度在抗老抗皱上——差异化必须落在成分故事（PDRN/重组胶原/产地植萃）与形态（油/滚珠/次抛）上。</li>
<li><b>二级功能点里的缺口</b>：抗皱淡纹 56 条、紧致提拉 41 条高度重合；黑眼圈提亮仅 10 条、眼袋浮肿仅 1 条——眼周细分诉求供给不足。</li>
<li><b>纯油形态 39.4% 已成第一形态</b>，但 36 条纯油里 27 条还是常规瓶装——滚珠油/双相油/次抛油的子形态创新才刚开始。</li>
<li><b>价格呈哑铃</b>：¥59 效妆走量 vs 200-516 元品牌带（32 条）；100-200 元最空（12 条）。</li>
<li><b>体验铁三角</b>：滋润 + 不油腻 + 好吸收；「快速吸收」供给仅 2 条，是最大体验空白。</li>
</ul></div>
<div class="tldr"><h2>阅读指南</h2><ul>
<li>顶部导航切换页面：<b>功效 / 形态 / 价格带 / 成分 / 包装 / 香型 / 规格 / SKU / 体验</b> 各自独立成页，地址栏 hash 可直接定位分享（如 #band）。</li>
<li>①②③ 页为<b>两级类目</b>：深色块 = 一级类目（含加权份额与组统计），浅色块 = 二级类目（含命中词表）；④-⑨ 为单级清单。</li>
<li>每个二级组头部的「n 条 · 周销合计 · GMV 合计 · 占类目 GMV %」均可复算佐证，口径写在该页顶部灰底虚线框内。</li>
</ul></div></section>
__SECS__
<section id="dir" class="page"><h2>研发方向（基于以上证据收敛）</h2>
<div class="dcards">__DIRS__</div></section>
<div class="foot">口径说明：要素只抽商品标题与详情页显性词，抽不到 = 「没写」而非「没有」（成分覆盖 40%、香型 25%、包装 21%、SKU 6%，低覆盖要素结论只作线索）。销量/GMV 为罗盘区间中值（周口径），组统计为中值直接求和，可能与平台实际有出入，仅用于组间相对比较。商品图走抖音 CDN，离线打开时缩略图不显示但不影响数据阅读。6 条失效链接为达人专场下架，非抓取失败。生成时间：__TIME__</div>
<script>
function go(id){var pages=document.querySelectorAll('section.page');var found=false;
pages.forEach(function(s){var on=s.id===id;if(on)found=true;s.classList.toggle('on',on);});
if(!found){go('ov');return;}
document.querySelectorAll('nav a').forEach(function(a){a.classList.toggle('on',a.getAttribute('href')==='#'+id);});
window.scrollTo(0,0);}
document.querySelectorAll('nav a').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();var id=a.getAttribute('href').slice(1);if(location.hash==='#'+id){go(id);}else{location.hash=id;}});});
window.addEventListener('hashchange',function(){go(location.hash.slice(1)||'ov');});
go(location.hash.slice(1)||'ov');
</script>
</body></html>"""

import time
page = (page.replace('__NAV__', nav_html)
        .replace('__SECS__', '\n'.join(secs))
        .replace('__DIRS__', dir_html)
        .replace('__TOTAL_GMV__', wan_fen(TOTAL_GMV))
        .replace('__TIME__', time.strftime('%Y-%m-%d %H:%M')))

out = os.path.join(EYE, '眼油_要素拆解_产品清单.html')
open(out, 'w', encoding='utf-8').write(page)
print('SAVED %s (%.1f KB)' % (out, len(page) / 1024))
print('类目 GMV 合计 ~%s 万分；周销合计 ~%s 件' % (wan_fen(TOTAL_GMV), wan_jian(TOTAL_ORD)))
