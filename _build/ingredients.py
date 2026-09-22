#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成分库构建：从 360 条商品的**真实标题**里抽「显性出现的成分词」并聚合成排行。

为什么只做标题抽取：
  本次实测五条「详情页」通道全部不可用 —— FastMoss 详情页已回落游客态（字段全空）、
  抖音 haohuo 详情页要求 APP 扫码、淘宝/天猫/小红书未登录、TikTok 域名直连被重置、
  国家药监局备案查询返回 412 反爬挑战。
  所以成分来源只能是标题里被商家自己写出来的成分词 —— 这是**事实抽取，不是推测**。
  抓不到全成分表的商品一律留空，不猜。

用法：
  python3 ingredients.py            # 干跑，打印排行与命中率
  python3 ingredients.py --write    # 写出 data/ingredients.json 与回填后的 records
"""
import argparse
import collections
import io
import json
import os
import re

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# ---------------------------------------------------------------- 成分词表
# (规范中文名, 成分族/作用, [别名...])  别名里的英文用词边界匹配，中文用子串匹配
LEX = [
    # —— 美白 / 提亮
    ('烟酰胺', '美白提亮', ['niacinamide', 'nicotinamide', '烟酰胺', '维B3']),
    ('熊果苷', '美白提亮', ['arbutin', '熊果苷', '熊果素']),
    ('曲酸', '美白提亮', ['kojic acid', 'kojic', '曲酸']),
    ('传明酸', '美白提亮', ['tranexamic acid', 'tranexamic', '传明酸', '氨甲环酸']),
    ('谷胱甘肽', '美白提亮', ['glutathione', '谷胱甘肽']),
    ('维生素C', '美白抗氧化', ['vitamin c', 'ascorbic', 'ethyl ascorbic', '维C', '维生素C', 'vc衍生物']),
    ('光甘草定', '美白提亮', ['glabridin', '光甘草定', '甘草定']),
    ('壬二酸', '美白祛痘', ['azelaic', '壬二酸', '杜鹃花酸']),
    ('二氧化钛', '物理美白遮盖', ['titanium dioxide', '二氧化钛', 'ci 77891']),
    # —— 抗老 / 紧致
    ('视黄醇', '抗老', ['retinol', 'retinal', 'retinyl', '视黄醇', 'A醇', 'a醇', '维A']),
    ('补骨脂酚', '抗老', ['bakuchiol', '补骨脂酚']),
    ('多肽', '抗老', ['peptide', 'matrixyl', 'argireline', 'palmitoyl', '多肽', '胜肽', '乙酰基六肽', '六胜肽', '五肽', '蓝铜肽', '铜肽']),
    ('玻色因', '抗老', ['pro-xylane', '玻色因']),
    ('胶原蛋白', '抗老弹润', ['collagen', '胶原蛋白', '胶原']),
    ('辅酶Q10', '抗氧抗老', ['coenzyme q10', 'coq10', 'ubiquinone', '辅酶Q10']),
    ('麦角硫因', '抗氧抗老', ['ergothioneine', '麦角硫因']),
    ('虾青素', '抗氧', ['astaxanthin', '虾青素']),
    ('白藜芦醇', '抗氧', ['resveratrol', '白藜芦醇']),
    ('维生素E', '抗氧', ['vitamin e', 'tocopherol', 'tocopheryl', '维生素E', '维E']),
    ('依克多因', '修护抗老', ['ectoin', '依克多因']),
    ('二裂酵母', '修护', ['bifida', '二裂酵母', '酵母发酵']),
    ('PDRN', '修护', ['pdrn', 'salmon dna', '三文鱼']),
    ('EGF', '修护', ['egf', '表皮生长因子']),
    ('燕窝酸', '修护', ['sialic acid', '燕窝酸', '唾液酸', '燕窝']),
    # —— 保湿 / 屏障
    ('玻尿酸', '保湿', ['hyaluronic', 'hyaluron', 'sodium hyaluronate', '玻尿酸', '透明质酸', '透明质酸钠']),
    ('神经酰胺', '屏障修护', ['ceramide', '神经酰胺']),
    ('角鲨烷', '保湿', ['squalane', '角鲨烷', '角鲨烯']),
    ('甘油', '保湿', ['glycerin', 'glycerol', '甘油']),
    ('泛醇', '保湿修护', ['panthenol', 'provitamin b5', '泛醇', '维生素B5', '维B5', 'b5', 'B5']),
    ('尿囊素', '舒缓保湿', ['allantoin', '尿囊素']),
    ('氨基酸', '温和清洁/保湿', ['amino acid', '氨基酸']),
    ('乳木果', '滋润', ['shea', '乳木果', '牛油果树果脂']),
    ('霍霍巴', '滋润', ['jojoba', '霍霍巴']),
    ('摩洛哥油', '滋润', ['argan', 'moroccan oil', '摩洛哥油', '阿甘油']),
    ('山茶花', '滋润', ['camellia', '山茶花', '茶花']),
    ('角蛋白', '修护', ['keratin', '角蛋白']),
    ('燕麦', '舒缓保湿', ['oat', 'colloidal oatmeal', '燕麦']),
    ('蜂蜜', '滋润', ['honey', 'manuka', '蜂蜜', '麦卢卡']),
    ('牛奶', '滋润', ['milk', 'goat milk', '牛奶', '羊奶', '山羊奶']),
    ('大米', '温和提亮', ['rice', 'fermented rice', '大米', '米糠']),
    ('椰子油', '滋润', ['coconut', '椰子油', '椰油']),
    ('橄榄', '滋润', ['olive', '橄榄']),
    # —— 酸类 / 清洁 / 祛痘
    ('果酸', '去角质', ['aha', 'aha/bha', '果酸', '羟基乙酸', '乳酸', 'lactic acid', 'glycolic', '甘醇酸', '杏仁酸', 'mandelic']),
    ('水杨酸', '祛痘去角质', ['bha', 'salicylic', '水杨酸']),
    ('PHA', '温和去角质', ['pha', '葡萄糖酸内酯', '葡糖酸内酯']),
    ('木瓜酶', '酶解清洁', ['papain', '木瓜酶', '木瓜蛋白酶']),
    ('菠萝酶', '酶解清洁', ['bromelain', '菠萝酶', '菠萝蛋白酶']),
    ('茶树', '控油祛痘', ['tea tree', '茶树']),
    ('积雪草', '舒缓修护', ['centella', 'cica', 'madecassoside', '积雪草', '羟基积雪草']),
    ('马齿苋', '舒缓', ['portulaca', '马齿苋']),
    ('金盏花', '舒缓', ['calendula', '金盏花', '金盏']),
    ('洋甘菊', '舒缓', ['chamomile', '矩阵洋甘菊', '洋甘菊']),
    ('芦荟', '舒缓保湿', ['aloe', '芦荟']),
    ('绿茶', '控油抗氧', ['green tea', 'egcg', '绿茶', '茶多酚']),
    ('艾草', '舒缓', ['mugwort', 'artemisia', '艾草', '艾叶']),
    ('甘草', '舒缓美白', ['licorice', '甘草', '光果甘草']),
    ('金缕梅', '收敛控油', ['witch hazel', 'hamamelis', '金缕梅']),
    ('咖啡因', '紧致消肿', ['caffeine', '咖啡因']),
    ('硫磺', '祛痘控油', ['sulfur', 'sulphur', '硫磺', '硫']),
    ('水杨酸盐', '控油', ['salicylate', '水杨酸盐']),
    ('活性炭', '吸附清洁', ['charcoal', 'activated carbon', '活性炭', '竹炭']),
    ('矿泥', '吸附清洁', ['mud', 'clay', 'bentonite', 'kaolin', '高岭土', '膨润土', '矿泥', '死海泥']),
    ('海盐', '去角质清洁', ['sea salt', 'dead sea salt', '海盐', '死海盐', '矿盐']),
    ('皂基', '清洁', ['soap base', '皂基', '皂粒']),
    # —— 头皮 / 头发
    ('生物素', '强韧发丝', ['biotin', '生物素', '维生素H']),
    ('生姜', '头皮养护', ['ginger', '生姜', '姜']),
    ('何首乌', '乌发养发', ['polygonum', 'he shou wu', '何首乌', '首乌']),
    ('人参', '头皮养护', ['ginseng', '红参', '人参']),
    ('米诺地尔', '防脱', ['minoxidil', '米诺地尔']),
    ('酮康唑', '去屑', ['ketoconazole', '酮康唑']),
    ('吡硫翁锌', '去屑', ['zinc pyrithione', '吡硫翁锌', 'zpt']),
    ('二硫化硒', '去屑', ['selenium sulfide', '二硫化硒']),
    ('水杨酸去屑', '去屑', ['salicylic acid']),
    # —— 口腔
    ('氟化钠', '防蛀', ['sodium fluoride', 'fluoride', '氟化钠', '单氟磷酸钠']),
    ('小苏打', '清洁亮白', ['baking soda', 'sodium bicarbonate', '小苏打', '碳酸氢钠']),
    ('木糖醇', '口腔护理', ['xylitol', '木糖醇']),
    ('益生菌', '口腔/皮肤微生态', ['probiotic', 'lactobacillus', '益生菌', '乳酸菌', '益生元', 'prebiotic']),
    # —— 香水 / 香氛
    ('香精', '调香', ['fragrance', 'parfum', '香精', '香氛']),
    ('精油', '调香', ['essential oil', '精油']),
    ('玫瑰', '花香', ['rose', '玫瑰']),
    ('薰衣草', '花香', ['lavender', '薰衣草']),
    ('白麝香', '调香', ['musk', '麝香', '白麝香']),
    ('檀香', '木质香', ['sandalwood', '檀香']),
    ('柑橘', '果香', ['citrus', 'bergamot', '柑橘', '佛手柑', '柠檬']),
    ('香草', '甜香', ['vanilla', '香草', '香荚兰']),
    # —— 其他功效
    ('锌', '控油', ['zinc pca', 'zinc oxide', '氧化锌', '锌']),
    ('尿素', '软化角质', ['urea', '尿素']),
    ('薄荷', '清凉', ['menthol', 'peppermint', 'mint', '薄荷', '薄荷醇']),
    ('樟脑', '清凉', ['camphor', '樟脑']),
    ('桉树', '清凉', ['eucalyptus', '桉树', '尤加利']),
    ('维生素', '营养', ['vitamin', '维生素']),
    ('香茅', '驱虫', ['citronella', 'lemongrass', '香茅']),
    ('避蚊胺', '驱虫', ['deet', '避蚊胺']),
    ('视黄酸酯', '抗老', ['retinyl palmitate', '视黄酸酯']),
    ('二甲基硅油', '顺滑', ['dimethicone', '二甲基硅氧烷']),
    ('凡士林', '封闭保湿', ['petrolatum', '凡士林', '矿脂']),
    ('羊毛脂', '滋润', ['lanolin', '羊毛脂']),
]

# 命中判定：英文词用词边界，中文词直接子串。下面这些短词太容易误命中，单独限死
STRICT_EN = {
    'aha': r'\baha\b', 'bha': r'\b(?:bha)\b', 'pha': r'\bpha\b', 'mud': r'\bmud\b',
    'b5': r'\bb5\b', 'vc': r'\bvc\b', 'zpt': r'\bzpt\b', 'milk': r'\bmilk\b',
    'rice': r'\brice\b', 'oat': r'\boat\b', 'mint': r'\bmint\b', 'deet': r'\bdeet\b',
}


def build_matchers():
    out = []
    for canon, family, alias in LEX:
        pats = []
        for a in alias:
            if re.fullmatch(r'[A-Za-z0-9 /\.\-]+', a):
                key = a.lower()
                rx = STRICT_EN.get(key)
                pats.append(('re', re.compile(rx or (r'(?<![a-z0-9])' + re.escape(key) + r'(?![a-z0-9])'), re.I)))
            else:
                pats.append(('sub', a))
        out.append({'canon': canon, 'family': family, 'pats': pats})
    return out


def find_ings(text, matchers):
    """返回 {规范名: 命中的原词}"""
    t = text or ''
    tl = t.lower()
    hit = {}
    for m in matchers:
        for kind, p in m['pats']:
            if kind == 're':
                mm = p.search(tl)
                if mm:
                    hit[m['canon']] = mm.group(0)
                    break
            else:
                if p and p in t:
                    hit[m['canon']] = p
                    break
    return hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', default=os.path.join(D, 'records_cat.json'))
    ap.add_argument('--out', dest='dst', default=os.path.join(D, 'ingredients.json'))
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()

    d = json.load(io.open(args.src, encoding='utf-8'))
    recs = d['records'] if isinstance(d, dict) else d
    matchers = build_matchers()
    fam = {m['canon']: m['family'] for m in matchers}

    per = {}                 # canon -> 聚合
    covered = 0
    for r in recs:
        text = '%s %s' % (r.get('商品名称') or '', r.get('名称中文') or '')
        hits = find_ings(text, matchers)
        if hits:
            covered += 1
        r['_ings'] = list(hits.keys())
        for canon in hits:
            a = per.setdefault(canon, {
                '成分': canon, '成分族': fam[canon], '商品数': 0,
                '三级类目': collections.Counter(), '二级类目': collections.Counter(),
                '一级类目': collections.Counter(), '国家': collections.Counter(),
                '增速': [], '销量': [], '样例': [], '证据': collections.Counter(),
            })
            a['商品数'] += 1
            if r.get('三级类目'):
                a['三级类目'][r['三级类目']] += 1
            if r.get('二级类目'):
                a['二级类目'][r['二级类目']] += 1
            if r.get('一级类目'):
                a['一级类目'][r['一级类目']] += 1
            if r.get('国家/地区'):
                a['国家'][r['国家/地区']] += 1
            g = r.get('环比增速')
            if isinstance(g, (int, float)):
                a['增速'].append(float(g))
            s = r.get('销量')
            if isinstance(s, (int, float)):
                a['销量'].append(float(s))
            if len(a['样例']) < 3:
                a['样例'].append('%s（%s）' % (str(r.get('商品名称'))[:34], r.get('国家/地区') or '—'))
            a['证据'][hits[canon]] += 1

    print('总记录 %d，标题含显性成分词 %d 条（%.0f%%）' % (len(recs), covered, 100.0 * covered / len(recs)))
    print()
    rows = []
    for canon, a in per.items():
        g = sorted(a['增速'])
        med = g[len(g) // 2] if g else None
        rows.append({
            '成分': canon, '成分族': a['成分族'], '商品数': a['商品数'],
            '主要一级类目': a['一级类目'].most_common(1)[0][0] if a['一级类目'] else '',
            '主要二级类目': ' / '.join(k for k, _ in a['二级类目'].most_common(3)),
            '主要三级类目': ' / '.join(k for k, _ in a['三级类目'].most_common(3)),
            '覆盖类目数': len(a['三级类目']),
            '覆盖国家': ' / '.join(k for k, _ in a['国家'].most_common(4)),
            '中位增速': round(med, 1) if med is not None else None,
            '最大增速': round(max(g), 1) if g else None,
            '合计销量': int(sum(a['销量'])) if a['销量'] else None,
            '代表商品': ' | '.join(a['样例']),
            '命中写法': ' / '.join(k for k, _ in a['证据'].most_common(4)),
        })
    rows.sort(key=lambda x: (-x['商品数'], -(x['中位增速'] or -999)))
    print('=== 成分排行 TOP 30（按出现商品数）===')
    for i, r in enumerate(rows[:30], 1):
        print('  %2d. %-8s %-10s 商品 %-3d 类目 %-3d 中位增速 %-8s 国家 %s'
              % (i, r['成分'], r['成分族'], r['商品数'], r['覆盖类目数'],
                 ('%.0f%%' % r['中位增速']) if r['中位增速'] is not None else '—', r['覆盖国家'][:24]))
    print()
    print('成分总数 %d 个（去重）' % len(rows))

    if args.write:
        json.dump({'source': '商品标题显性成分词抽取（非推测）',
                   'coverage': {'记录数': len(recs), '含成分记录': covered},
                   'rows': rows},
                  io.open(args.dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # 回填「核心功效成分」到记录
        for r in recs:
            if r.get('_ings'):
                r['核心功效成分'] = ' / '.join(r['_ings'][:4])
        json.dump({'records': recs}, io.open(args.src, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('写出 %s；并把成分回填进记录（%d 条）' % (args.dst, covered))


if __name__ == '__main__':
    main()
