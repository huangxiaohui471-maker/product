#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""眼油要素拆解报告：每个统计值背后「是哪些产品」全部罗列成商品卡。
输入: eyeoil/rank_fiber_img.json + factsheet.json + details/ + directions.json
输出: eyeoil/眼油_要素拆解_产品清单.html
"""
import json
import os
import re
import html as H

BASE = os.path.dirname(os.path.abspath(__file__))
EYE = os.path.join(BASE, 'eyeoil')

rank_rows = json.load(open(os.path.join(EYE, 'rank_fiber_img.json'), encoding='utf-8'))['rows']
fs = json.load(open(os.path.join(EYE, 'factsheet.json'), encoding='utf-8'))
directions = json.load(open(os.path.join(EYE, 'directions.json'), encoding='utf-8'))['directions']

# ---------- 合并产品主档 ----------
prods = {}  # pid -> dict
for r in rank_rows:
    pid = str(r.get('product_id') or '')
    if not pid or pid in prods:
        continue
    prods[pid] = r
for it in fs['items']:
    pid = str(it['id'])
    if pid in prods:
        prods[pid]['elements'] = it.get('elements', {})
        prods[pid]['missing'] = it.get('missing', [])

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
    if isinstance(v, dict):  # SKU
        dims = v.get('维度') or []
        return dims
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
    if not x: return ''
    return '%.0f' % (x / 100.0 / 10000.0)

def wan_jian(x):
    if not x: return ''
    if x >= 10000:
        return '%.1f万' % (x / 10000.0)
    return '%.0f' % x

def esc(s):
    return H.escape(str(s or ''))

# ---------- 商品卡 ----------
def card(p, hi_values, hi_key):
    pid = [k for k, v in prods.items() if v is p][0]
    img = p.get('image_url') or ''
    name = esc(p.get('name'))
    shop = esc(p.get('shop_name'))
    price = esc(p.get('price_bin'))
    rank = p.get('rank')
    gmv = wan_fen(p.get('gmv_mid'))
    orders = wan_jian(p.get('orders_mid'))
    new_badge = '<span class="new">新上榜</span>' if p.get('newly_on_ranking') else ''
    # 小标签：形态/成分/规格（与本节要素相关的值高亮）
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

def section(sid, title, share_line, note, groups):
    """groups: [(取值, 份额文本, [prods], hi_key)]"""
    out = ['<section id="%s"><h2>%s</h2><div class="share">%s</div><p class="note">%s</p>' % (sid, esc(title), share_line, note)]
    for val, stat, plist, hi_key in groups:
        cards = ''.join(card(p, [val], hi_key) for p in plist)
        out.append('<div class="grp"><h3><span class="gv">%s</span><span class="gs">%s</span>'
                   '<span class="gn">%d 条</span></h3><div class="grid">%s</div></div>'
                   % (esc(val), esc(stat), len(plist), cards))
    out.append('</section>')
    return '\n'.join(out)

# ---------- 分组数据 ----------
def group_by(key, values_order=None, min_n=1):
    """返回 [(值, [prods 按 rank 排])]，多选字段一个产品可进多组"""
    g = {}
    for p in prods.values():
        v = el(p, key)
        vs = v if isinstance(v, list) else ([v] if v else [])
        for x in vs:
            if not x:
                continue
            g.setdefault(x, []).append(p)
    items = [(k, sorted(v, key=lambda p: p.get('rank') or 999)) for k, v in g.items() if len(v) >= min_n]
    if values_order:
        order = {v: i for i, v in enumerate(values_order)}
        items.sort(key=lambda kv: (order.get(kv[0], 99), -len(kv[1])))
    else:
        items.sort(key=lambda kv: -len(kv[1]))
    return items

def share_of(key, val):
    s = summary['elements'].get(key, {}).get('values', {})
    v = s.get(val)
    if not v:
        return ''
    return '加权份额 %.1f%%' % v.get('weighted_share', 0)

summary = json.load(open(os.path.join(EYE, 'summary.json'), encoding='utf-8'))

def stat_text(key, val, n):
    s = summary['elements'].get(key, {}).get('values', {}).get(val)
    if s:
        return '加权份额 %.1f%%' % s.get('weighted_share', 0)
    return ''

# ---------- 各节 ----------
secs = []

# 1 功效
EFF_ORDER = ['抗老抗皱', '保湿滋润', '舒缓修护', '美白提亮']
eff_groups = [(v, stat_text('功效', v, len(ps)), ps, '功效') for v, ps in group_by('功效', EFF_ORDER)]
secs.append(section('eff', '① 功效：每个功效词背后是哪些产品',
    '抗老抗皱 <b>65.5%</b>（63 条）· 保湿滋润 <b>39.6%</b>（36 条）· 舒缓修护 12.8%（11 条）· 美白提亮 7.3%（7 条）｜份额按销量+评价+GMV 加权',
    '判读：「抗皱」是眼部精华的入场券——63 条商品、近 2/3 的加权热度都在这个词上，不打抗皱基本进不了这个类目；但也正因为它拥挤，差异化必须落在成分故事与形态上。保湿滋润常作为第二功效与抗皱捆绑出现（油形态的天然卖点）。舒缓修护 11 条不算挤，是敏感肌/医美场景的口子。美白提亮（黑眼圈方向）只有 7 条，验证尚浅。',
    eff_groups))

# 2 形态
FORM_ORDER = ['纯油', '液体', '水', '霜', '乳', '凝胶', '膏', '喷雾']
form_groups = [(v, stat_text('产品内料形态', v, len(ps)), ps, '产品内料形态') for v, ps in group_by('产品内料形态', FORM_ORDER)]
secs.append(section('form', '② 内料形态：纯油 39.4% 是哪些品牌在做',
    '纯油（精华油）<b>39.4%</b>（36 条）· 液体精华 14.1%（14 条）· 水状 10.8%（12 条）· 其余霜/乳/凝胶/膏/喷雾合计 <10%',
    '判读：「油养眼」心智已经教育完成——效妆、雏菊的天空、林清轩、玫瑰颂、澳莉曼等品牌共同把纯油推成第一形态，且头部（Top10 里 6 席是油）已被油占据。新品牌做油是顺势而为，不是冒险。液体/水状精华主要由次抛、原液形态构成（薇旖美、Dr.Duncan、帝百珂）。',
    form_groups))

# 3 价格带
BAND_ORDER = ['<60 元', '60-100 元', '100-200 元', '200-400 元', '400+ 元']
band_g = {}
for p in prods.values():
    b = band_of(price_lo(p))
    if b:
        band_g.setdefault(b, []).append(p)
band_groups = []
BAND_NOTE = {
    '<60 元': '走量带：效妆一家独大（榜一，周销中值 17.5 万件），拼的是投流与供应链成本。',
    '60-100 元': '过渡带：多为白牌/工厂店，缺品牌叙事。',
    '100-200 元': '供给最薄（12 条）：夹在走量与品牌之间，反而是竞争压力最小的区间。',
    '200-400 元': '主流成交带（32 条）：雏菊的天空、林清轩、专妍、Kessetti 入门款都挤在这里，成分故事与套组结构是胜负手。',
    '400+ 元': '高端品牌带（26 条）：雏菊 2.0、Kessetti ¥2180、薇旖美 ¥1380——靠原料商背书与品牌调性支撑溢价。',
}
for b in BAND_ORDER:
    ps = sorted(band_g.get(b, []), key=lambda p: p.get('rank') or 999)
    band_groups.append((b, BAND_NOTE.get(b, ''), ps, '价格带'))
secs.append(section('band', '③ 价格带：每个价位段里都是谁',
    '&lt;60 元 <b>20</b> 条 · 60-100 元 <b>10</b> 条 · 100-200 元 <b>12</b> 条 · 200-400 元 <b>32</b> 条 · 400+ 元 <b>26</b> 条（按标价下界，n=100）',
    '判读：眼油不是低价品类——200 元以上合计 58 条。价格呈「哑铃」：一头是效妆 ¥59 的极致走量（一个链接吃掉类目约 1/4 的 GMV 热度），一头是 200-516 元的品牌带（雏菊系列 6 条链接）。中间 100-200 元反而空。',
    band_groups))

# 4 成分
ING_ORDER = ['PDRN', '乌斯曼草', '精油', '胶原蛋白', '多肽', '山茶花', '咖啡因', '重组胶原蛋白', '胜肽', '蓝铜肽', '密罗木', '乳酸', '叶黄素', '卵磷脂', '晚香玉', '发酵']
ing_groups = [(v, stat_text('主打成分', v, len(ps)), ps, '主打成分') for v, ps in group_by('主打成分', ING_ORDER)]
secs.append(section('ing', '④ 主打成分：成分阵营拆分',
    '精油 7 条 · 乌斯曼草 7 条 · PDRN 5 条（加权 6.2%）· 胶原蛋白 5 条 · 多肽 4 条｜成分覆盖率 40/100',
    '判读：成分故事三分天下——<b>PDRN</b>（再生医学叙事，效妆带火后 5 家快速跟进，说明跟进成本已被摊薄）；<b>乌斯曼草</b>（新疆产地叙事，7 条但同质化严重、标题互相抄）；<b>经典多肽/重组胶原</b>（Dr.Duncan、薇旖美/锦波生物、帝百珂，走原料商背书路线）。山茶花（林清轩）、密罗木、蓝铜肽、叶黄素是单点差异化。注：只抽标题与详情显性词，60 条没写成分 ≠ 没有成分。',
    ing_groups))

# 5 包装
PACK_ORDER = ['贴片', '盒装', '滚珠', '胶囊', '次抛', '瓶装', '袋装']
pack_groups = [(v, stat_text('包装形式', v, len(ps)), ps, '包装形式') for v, ps in group_by('包装形式', PACK_ORDER)]
secs.append(section('pack', '⑤ 包装形式：滚珠/次抛/胶囊都是谁',
    '贴片 7 条 · 盒装/礼盒 6 条 · 滚珠 5 条（加权 5.3%）· 胶囊 5 条 · 次抛 4 条｜文本覆盖率 21/100（标题很少写包装，实际瓶装是默认形态）',
    '判读：包装是眼油品类最活跃的创新点——<b>滚珠</b>（丸美小红笔、雏菊滚珠版，按摩+便携补涂场景）、<b>次抛</b>（薇旖美 ¥1380 也成立，锁鲜叙事）、<b>胶囊</b>（CEMOY 反重力系列 5 条）、<b>盒装/礼盒</b>（中秋节点，雏菊礼盒）。滚珠与「快速吸收」体验诉求天然绑定。',
    pack_groups))

# 6 香型
SCENT_ORDER = ['东方调', '木质', '草本植物', '玫瑰', '茉莉', '茶香']
scent_groups = [(v, stat_text('香型', v, len(ps)), ps, '香型') for v, ps in group_by('香型', SCENT_ORDER)]
secs.append(section('scent', '⑥ 香型：打香的 25 条都是谁',
    '东方调（琥珀）15 条（加权 15.7%）· 木质 3 · 草本 3 · 玫瑰 2 · 茉莉 1 · 茶香 1｜75 条未提香型',
    '判读：眼油品类<b>不打香是主流</b>（75% 没写香型，眼周产品「无香=温和」是默认预期）。打香的几乎以东方调（琥珀）为主——但那基本是雏菊的天空「琥珀时光」一个系列的产品名在贡献；玫瑰（玫瑰颂）、檀香（澳莉曼）、茶香（俊平龙井）是单点。结论：香型不是这个品类的决策要素，新品做无香或植物油本味即可。',
    scent_groups))

# 7 规格
spec_groups = [(v, '', ps, '规格') for v, ps in group_by('规格')[:10]]
secs.append(section('spec', '⑦ 规格：容量拆分',
    '8ml <b>8 条</b>（加权 7.9%，眼油基准规格）· 20ml 4 条 · 10ml 3 条 · 2ml 3 条（滚珠/随行装）｜文本覆盖率 21/100',
    '判读：<b>8ml 是雏菊的天空全系列确立的眼油基准规格</b>（双瓶 8ml×2 是其主力 SKU 结构），配合「小容量+高频复购」打法。10-20ml 多为性价比叙事（澳莉曼 20ml×2 支 ¥99）。2ml 是滚珠随行装规格，与便携场景绑定。眼部产品用量小，大规格（>30ml）在这个榜单里完全缺席。',
    spec_groups))

# 8 SKU
sku_groups = [(v, '', ps, 'SKU') for v, ps in group_by('SKU')]
secs.append(section('sku', '⑧ SKU 结构：套组打法',
    '套装/套组 2 条 · 多件装 2 条 · 试用/旅行装 1 条 · 家庭装/大容量 1 条｜文本覆盖率仅 6/100（SKU 明细在详情页交互区，标题只能看到线索）',
    '判读：头部 SKU 打法已收敛成两类——<b>「双瓶/多瓶装」拉客单</b>（雏菊 8ml 双瓶、澳莉曼 20ml×2）、<b>「眼油+滚珠/眼膜」组合装</b>（雏菊 8ml+滚珠 2ml、孙坚专属套组）。派样装（1ml）被用作短视频引流款。SKU 覆盖率低是数据源限制，不代表现状。',
    sku_groups))

# 9 体验
exp_groups = [(v, stat_text('使用体验', v, len(ps)), ps, '使用体验') for v, ps in group_by('使用体验')]
secs.append(section('exp', '⑨ 使用体验：评价标签里的真实体验点',
    '肤感滋润 11 条（加权 13.7%）· 快速吸收 2 条（<b>空白格第一</b>：份额 3.6% 供给仅 2 条）· 温和不刺激 1 条',
    '判读：榜一效妆的 18.1w 条评价给出了体验铁三角——<b>很滋润(1.7w) / 不油腻(7532) / 好吸收(5229)</b>，这五个字就是眼油肤感开发的验收标准；「会回购(7428)」说明 59 元价位也能做出复购。「快速吸收」在文本端供给极少但头部评价里被反复点名，是明确的体验空白。下方是 9 个头部商品的评价标签原文（罗盘详情页直取）。',
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
NAV = [('eff', '① 功效'), ('form', '② 形态'), ('band', '③ 价格带'), ('ing', '④ 成分'), ('pack', '⑤ 包装'),
       ('scent', '⑥ 香型'), ('spec', '⑦ 规格'), ('sku', '⑧ SKU'), ('exp', '⑨ 体验'), ('dir', '研发方向')]
nav_html = ''.join('<a href="#%s">%s</a>' % (a, t) for a, t in NAV)

page = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>眼油要素拆解 · 产品清单（抖音罗盘眼部精华榜 TOP100）</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Helvetica Neue",sans-serif;background:#f5f6f8;color:#1f2329;padding-bottom:60px}
.hd{background:linear-gradient(135deg,#1a1f36,#2d3561);color:#fff;padding:28px 20px 22px}
.hd h1{font-size:20px;margin-bottom:8px}
.hd .meta{font-size:12.5px;opacity:.85;line-height:1.7}
.hd .meta b{color:#ffd666}
nav{position:sticky;top:0;z-index:50;background:#fff;display:flex;gap:4px;overflow-x:auto;padding:10px 12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
nav a{flex:0 0 auto;font-size:13px;color:#4e5569;text-decoration:none;padding:7px 13px;border-radius:16px;background:#f0f1f5;white-space:nowrap}
nav a:active{background:#2d3561;color:#fff}
.tldr{background:#fff;margin:14px 12px 0;border-radius:12px;padding:16px}
.tldr h2{font-size:15px;margin-bottom:10px}
.tldr li{font-size:13px;line-height:1.8;margin-left:18px;margin-bottom:4px}
.tldr b{color:#c0392b}
section{margin:22px 12px 0}
section>h2{font-size:17px;margin-bottom:6px}
.share{font-size:12.5px;color:#8a4b08;background:#fff7e6;border:1px solid #ffe7ba;border-radius:8px;padding:8px 12px;line-height:1.7}
.share b{color:#c0392b}
.note{font-size:13px;color:#4e5569;line-height:1.85;background:#fff;border-radius:10px;padding:12px 14px;margin-top:8px}
.note b{color:#c0392b}
.grp{margin-top:16px}
.grp h3{font-size:14.5px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.gv{background:#2d3561;color:#fff;padding:3px 10px;border-radius:6px;font-size:13px}
.gs{font-size:12px;color:#c0392b;font-weight:600}
.gn{font-size:12px;color:#86909c;font-weight:400}
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
<div class="hd"><h1>眼油（眼部精华油）· 要素拆解与产品清单</h1>
<div class="meta">数据源：抖音电商罗盘 → 市场 → 商品榜单 → 个护家清/个人护理/眼部护理/<b>眼部精华</b>（总榜 TOP100）<br>
统计周期：<b>2026/09/14 - 2026/09/20</b>（近 7 天）｜样本 n=100，头部 15 商品附详情页评价标签（6 条达人专场链接已下架失效）｜份额 = 销量 0.5 + 评价 0.3 + GMV 0.2 归一加权</div></div>
<nav>__NAV__</nav>
<div class="tldr"><h2>核心判读（先看这个）</h2><ul>
<li><b>抗皱是入场券不是差异点</b>：65.5% 的热度在抗老抗皱上，63 条商品人人都在打——差异化必须落在成分故事（PDRN/重组胶原/产地植萃）与形态（油/滚珠/次抛）上。</li>
<li><b>纯油形态 39.4% 已成第一形态</b>：效妆、雏菊、林清轩、玫瑰颂共同完成市场教育，做油 = 顺势。</li>
<li><b>价格呈哑铃</b>：¥59 效妆走量（约吃 1/4 GMV 热度）vs 200-516 元品牌带（32 条）；100-200 元最空（12 条）。</li>
<li><b>体验铁三角</b>：滋润 + 不油腻 + 好吸收（效妆 18.1w 评价验证）；「快速吸收」供给仅 2 条，是最大体验空白。</li>
<li><b>规格基准 8ml</b>（雏菊确立）+ 双瓶套组拉客单 + 滚珠 2ml 便携装拓场景。</li>
</ul></div>
__SECS__
<section id="dir"><h2>研发方向（基于以上证据收敛）</h2>
<div class="dcards">__DIRS__</div></section>
<div class="foot">口径说明：要素只抽商品标题与详情页显性词，抽不到 = 「没写」而非「没有」（成分覆盖 40%、香型 25%、包装 21%、SKU 6%，低覆盖要素结论只作线索）。销量/GMV 为罗盘区间中值（周口径）。商品图走抖音 CDN，离线打开时缩略图不显示但不影响数据阅读。6 条失效链接为达人专场下架，非抓取失败。生成时间：__TIME__</div>
</body></html>"""

import time
page = (page.replace('__NAV__', nav_html)
        .replace('__SECS__', '\n'.join(secs) + tag_table.replace('<table', '<section id="evtag"><h2 style="margin-top:22px">附：头部商品评价标签（体验要素证据）</h2><table', 1).replace('</table>', '</table></section>', 1))
        .replace('__DIRS__', dir_html)
        .replace('__TIME__', time.strftime('%Y-%m-%d %H:%M')))

out = os.path.join(EYE, '眼油_要素拆解_产品清单.html')
open(out, 'w', encoding='utf-8').write(page)
print('SAVED %s (%.1f KB)' % (out, len(page) / 1024))
