#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Olive Young 榜单映射成本库的类目体系，产出可直接入云表的记录。

映射目标词表 = 本库 FastMoss 美妆个护三级类目（含 cid 链），
这样韩国数据与中/东南亚/欧美数据能落到同一套「二级类目 / 三级类目」上做聚合。

Olive Young 的 L1 恒为 "01"（美妆个护大类），L2/L3 是韩文小类目。
非美妆（食品/保健品）显式剔除。

输入: data/oliveyoung_rank.json + data/oy_zh.json
输出: data/oy_records.json
用法: python3 oy_map.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')

# 复用主映射脚本的两张表，保证口径一致
sys.path.insert(0, HERE)
import map_cats  # noqa: E402

FUNC_OF_L3 = map_cats.FUNC_OF_L3
L1_OF_PLATFORM_L2 = map_cats.L1_OF_PLATFORM_L2

# ---------------------------------------------------------------- Olive Young 类目 -> 本库三级类目
# 值 = 本库三级类目名；None = 非美妆，剔除
OY_MAP = {
    ('스킨케어', '에센스'): '面部精华液',
    ('스킨케어', '크림'): '保湿乳液、乳霜与喷雾',
    ('스킨케어', '로션'): '保湿乳液、乳霜与喷雾',
    ('스킨케어', '페이셜미스트'): '保湿乳液、乳霜与喷雾',
    ('스킨케어', '스킨/토너'): '爽肤水、化妆水',
    ('스킨케어', '스킨케어기기'): '面部美容仪',
    ('마스크팩', '시트팩'): '面膜',
    ('마스크팩', '패드'): '面膜',          # 토너패드 爽肤棉片，Olive Young 归在面膜组
    ('마스크팩', '페이셜팩'): '面膜',
    ('마스크팩', '패치'): '痘痘、粉刺护理',
    ('패치/국소케어', '집중관리패치/겔'): '痘痘、粉刺护理',
    ('베이스 메이크업', '쿠션'): '遮瑕与粉底',
    ('베이스 메이크업', 'BB/CC'): 'BB霜与CC霜',
    ('베이스 메이크업', '프라이머/베이스'): '妆前乳与眼影打底膏',
    ('베이스 메이크업', '블러셔'): '腮红',
    ('립 메이크업', '립틴트'): '口红与唇彩',
    ('립 메이크업', '립글로스'): '口红与唇彩',
    ('립 메이크업', '립라이너'): '眼线笔与唇线笔',
    ('아이 메이크업', '아이섀도우'): '眼影',
    ('아이 메이크업', '아이라이너'): '眼线笔与唇线笔',
    ('아이 메이크업', '아이브로우'): '眉笔&眉粉&眉胶',
    ('아이 소품(Eye)', '속눈썹'): '假睫毛与胶水',
    ('선케어', '선블록'): '脸部防晒霜与晒后修复',
    ('클렌징', '클렌징폼'): '洗面乳',
    ('클렌징', '클렌징밀크'): '卸妆',
    ('클렌징', '클렌징워터'): '卸妆',
    ('클렌징', '클렌징오일'): '卸妆',
    ('헤어 세정류', '샴푸'): '洗发护发',
    ('헤어 트리트먼트', '헤어토닉/앰플'): '头发与头皮养护',
    ('헤어 트리트먼트', '헤어트리트먼트'): '头发与头皮养护',
    ('헤어 트리트먼트', '헤어에센스'): '头发与头皮养护',
    ('바디 보습류', '바디로션'): '身体霜、乳',
    ('바디 세정류', '바디스크럽'): '身体磨砂膏、去角质',
    ('헤어 가전', '헤어세팅기기'): '卷、直发器',
    ('생리/위생용품', '패드형 생리대'): '卫生巾',
    ('구강보조용품', '가글'): '漱口水',
    # 非美妆，剔出本库
    ('과자류', '스낵'): None,
    ('건강기능식품', '단일비타민(기능식품)'): None,
    ('기능성/건강음료류', '프로틴음료(고형)'): None,
}


def build_index():
    """三级类目名 -> (cid 链, 平台二级中文名)。"""
    tree = json.load(open(os.path.join(D, 'fm_cat_zh.json'), encoding='utf-8'))['tree']
    idx = {}

    def walk(nodes, path, cidp):
        for n in nodes:
            cid = str(n.get('cid') or '')
            p = cidp + [cid] if cid else cidp
            ch = n.get('children') or []
            if ch:
                walk(ch, path + [n.get('zh')], p)
            else:
                idx[n.get('zh')] = ('/'.join(p), path[-1] if path else '')

    walk(tree, [], [])
    return idx


def main():
    rank = {x['no']: x for x in json.load(open(os.path.join(D, 'oliveyoung_rank.json'), encoding='utf-8'))}
    zh = json.load(open(os.path.join(D, 'oy_zh.json'), encoding='utf-8'))
    idx = build_index()

    recs, dropped, unresolved = [], [], []
    for m in zh:
        rk = rank.get(m['no'], {})
        cat = rk.get('c') or ''
        parts = [p.strip() for p in cat.split('>')]
        key = (parts[1], parts[2]) if len(parts) >= 3 else None
        if key not in OY_MAP:
            unresolved.append((cat, m['name_ko'][:30]))
            continue
        target = OY_MAP[key]
        if target is None:
            dropped.append((cat, m['name_zh'] or m['name_ko']))
            continue
        hit = idx.get(target)
        if not hit:
            unresolved.append(('本库无此类目: ' + target, m['name_ko'][:30]))
            continue
        cid, plat_l2 = hit
        recs.append({
            '商品名称': '%s（%s）' % (m['name_zh'] or m['name_ko'], m['name_ko']),
            '品牌': m['brand_zh'] or m['brand_ko'],
            '商品ID': m['no'],
            '品类': L1_OF_PLATFORM_L2.get(plat_l2, '其他'),
            '二级类目': FUNC_OF_L3.get(target, '其他'),
            '三级类目': target,
            '类目ID': cid,
            '国家/地区': '韩国',
            '所属市场': '韩国',
            '数据来源': 'Olive Young',
            '榜单排名': str(m['r']),
            '价格': int(m['p']) if str(m['p']).isdigit() else None,
            '数据标记': '真实',
            '_oy_cat': cat,
            '_oy_price_krw': int(m['p']) if str(m['p']).isdigit() else None,
        })

    json.dump(recs, open(os.path.join(D, 'oy_records.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('入表候选 %d 条 | 剔除(非美妆) %d 条 | 未映射 %d 条' % (len(recs), len(dropped), len(unresolved)))
    if dropped:
        print('  剔除:', dropped)
    if unresolved:
        print('  未映射:', unresolved[:8])
    import collections
    print('  一级业务大类:', dict(collections.Counter(r['品类'] for r in recs)))
    print('  二级类目:', dict(collections.Counter(r['二级类目'] for r in recs)))
    print('  三级类目数:', len({r['三级类目'] for r in recs}))
    print('前 6 条:')
    for r in recs[:6]:
        print('  #%-3s %-14s %-42s %-10s %-14s %s' % (
            r['榜单排名'], r['品牌'][:12], r['商品名称'][:40], r['品类'], r['二级类目'], r['三级类目']))


if __name__ == '__main__':
    main()
