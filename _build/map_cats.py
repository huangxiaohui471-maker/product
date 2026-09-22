#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 360 条记录映射进「国家市场 × 三级品类」体系。

字段产出：
  一级类目  = 我方业务大类（护肤/彩妆/个护/身体/香氛/工具）
  二级类目  = 功能子类（底妆/面部清洁/身体清洁…），由平台三级类目归组而来
  三级类目  = 平台官方三级类目中文名（遮瑕与粉底/沐浴露与香皂…）
  平台类目路径 = 美妆个护 / 美妆 / 遮瑕与粉底（可溯源）
  类目ID   = 14/848648/601554（取数用，能按它精确复现抓取）
  国家/地区 = 平台 region 代码对应的中文国家名

用法：
  python3 map_cats.py            # 干跑，打印统计与待 AI 映射清单
  python3 map_cats.py --write    # 调 Kimi 补蝉妈妈映射并写出 data/records_cat.json
"""
import argparse
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# ---------------------------------------------------------------- 一级类目归组
# 平台二级类目 -> 我方业务大类
L1_OF_PLATFORM_L2 = {
    '美容护肤': '护肤', '美妆': '彩妆', '洗浴与身体护理': '身体', '香水': '香氛',
    '头部护理与造型': '个护', '鼻子口腔护理': '个护', '手足及指甲护理': '个护',
    '女性私密处护理': '个护', '男士护理': '个护', '特殊个护': '个护',
    '眼镜耳朵护理': '个护', '美容、个护电器': '工具',
}

# ---------------------------------------------------------------- 二级类目（功能子类）
# 平台三级类目 -> 功能子类。未列出的落到「其他」并会在干跑里点名。
FUNC_OF_L3 = {
    # 护肤线
    '洗面乳': '面部清洁', '面部磨砂膏与去角质': '面部清洁', '卸妆': '面部清洁',
    '爽肤水、化妆水': '爽肤水', '面部精华液': '精华', '乳霜与喷雾': '面部保湿',
    '保湿乳液、乳霜与喷雾': '面部保湿', '面部按摩霜': '面部保湿',
    '面膜': '面膜', '眼部护理': '眼部护理', '唇部护理': '唇部护理',
    '脸部防晒霜与晒后修复': '防晒', '痘痘、粉刺护理': '祛痘',
    '鼻部护理': '面部清洁', '鼻部清洁用品': '面部清洁',
    '面部护理套装': '护理套装', '面部护理工具': '美容工具', 'Skincare Tools': '美容工具',
    # 彩妆线
    '遮瑕与粉底': '底妆', 'BB霜与CC霜': '底妆', '妆前乳与眼影打底膏': '底妆',
    '散粉': '定妆', '定妆喷雾': '定妆', '粉扑': '美妆工具',
    '修容与高光': '修容', '腮红': '腮红',
    '口红与唇彩': '唇妆', '眼影': '眼妆', '睫毛膏': '眼妆', '眼线笔与唇线笔': '眼妆',
    '眉笔&眉粉&眉胶': '眉妆', '假睫毛与胶水': '眼妆', '睫毛夹': '美妆工具',
    '化妆工具': '美妆工具', '化妆刷': '美妆工具', '美妆蛋与海绵': '美妆工具',
    '棉签': '美妆工具', '美妆套装': '美妆套装', '身体彩妆': '身体彩妆',
    # 身体线
    '沐浴露与香皂': '身体清洁', '身体霜、乳': '身体保湿', '身体护理套装': '身体套装',
    '身体磨砂膏、去角质': '身体去角质', '身体磨砂膏': '身体去角质',
    '保湿油、按摩油': '身体油', '身体按摩油': '身体油', '身体膜': '身体护理',
    '止汗露': '止汗除臭', '除毛乳、除毛蜜蜡&除毛器': '脱毛', '除毛用品': '脱毛',
    '洗澡工具': '洗浴工具', '手动按摩用品': '按摩工具', '爽身粉': '身体护理',
    '塑形霜': '身体护理', '胸部护理': '身体护理', '颈部护理': '身体护理',
    '防晒与晒后护理': '防晒', '美黑油与自晒乳': '美黑',
    # 头发线
    '洗发护发': '头发清洁', '头发与头皮养护': '头发护理', '头皮护理': '头发护理',
    '脱发产品': '防脱', '染发用品': '染发', '造型粉': '头发造型',
    '摩丝与啫喱': '头发造型', '无热造型工具': '造型工具', '梳子与发刷': '造型工具',
    '直发膏': '头发造型', '烫发剂': '头发造型', '除虱产品': '头发护理',
    '发用香氛': '头发护理', '美发家具': '造型工具',
    # 口腔 / 鼻腔
    '牙膏': '口腔清洁', '手动牙刷': '口腔清洁', '漱口水': '口腔清洁',
    '牙线和牙签': '口腔清洁', '口腔喷剂': '口腔护理', '口腔护理套装': '口腔套装',
    '牙齿美白': '牙齿美白', '舌苔清洁器': '口腔清洁', '假牙护理': '口腔清洁',
    '正畸配件': '口腔护理', '防磨牙牙套': '口腔护理', '鼻部清洁用品': '鼻腔护理',
    # 手足甲
    '指甲油': '美甲', '指甲护理': '美甲', '美甲套装': '美甲',
    '美甲装饰和配饰': '美甲', '洗甲水': '美甲', '手足工具与配件': '手足工具',
    '手足膜': '手足护理', '护手足霜、乳液与磨砂膏': '手足护理',
    '乳液与磨砂膏': '手足护理', '洗手液': '手部清洁', '免洗洗手液': '手部清洁',
    '足部除臭': '止汗除臭',
    # 男士
    '剃须泡沫与须后护理': '剃须', '剃须刀': '剃须', '剃须工具套装': '剃须',
    '男士手动剃须工具': '剃须', '手动剃须配件': '剃须', '男士理容': '男士理容',
    '男士私密护理与湿巾': '男士理容', '男士止汗剂': '止汗除臭',
    '男士洗浴与身体护理': '身体清洁',
    # 女性
    '私密处清洁用品': '女性护理', '女性私密处护理': '女性护理', '卫生巾': '女性护理',
    '卫生棉条': '女性护理', '月经杯': '女性护理', '经期内裤': '女性护理',
    '私密除臭剂': '女性护理', '阴道护理霜': '女性护理', '更年期用品': '女性护理',
    '月经杯盒与消毒器': '女性护理',
    # 香水
    '香水': '香水', '女士香水': '香水', '男士香水': '香水',
    '男女通用香水': '香水', '香水套装': '香水',
    # 个护电器 / 工具
    '按摩器': '按摩工具', '按摩椅': '按摩工具', '身体美容仪': '美容仪器',
    '面部美容仪': '美容仪器', '电动修眉器': '美容仪器', '脱毛仪': '脱毛',
    '电动剃须刀': '剃须', '电动牙刷': '口腔清洁', '冲牙器': '口腔清洁',
    '吹风机': '美发工具', '卷、直发器': '美发工具', '理发器': '美发工具',
    '鼻耳毛修剪器': '男士理容', '体毛修剪器': '脱毛', '加热垫': '护理护理',
    '电子耳镜': '其他', '翻新护发电器': '美发工具', '配件': '其他',
    # 眼镜耳朵
    '眼罩': '睡眠护理', '耳塞': '睡眠护理', '隐形眼镜': '隐形眼镜',
    '彩色隐形眼镜': '隐形眼镜', '隐形眼镜护理液': '隐形眼镜',
    '隐形眼镜护理套装': '隐形眼镜', '老花镜': '其他', '滴耳液': '耳部护理',
    '耳垢清洁产品和工具': '耳部护理',
    # 特殊个护
    '暖宝宝': '特殊个护', '冰袋': '特殊个护', '成人纸尿裤': '特殊个护',
    '驱虫剂': '特殊个护', '隔尿垫': '特殊个护',
    # 男士护理下的同名三级、纹身/镜类
    '纹身后护理': '身体护理', '美妆': '男士理容', '美容护肤': '男士理容',
    '头发护理': '头发护理', '临时纹身': '纹身', '纹身机器与套装': '纹身',
    '纹身去除': '纹身', '化妆镜': '美妆工具', '睫毛增长液与打底膏': '眼妆',
    # 罗盘行业类目（中国侧）会归一到上面的平台三级
}

# 罗盘/蝉妈妈的中国行业类目 -> 平台三级类目
CN_CAT_TO_L3 = {
    '沐浴露·油·乳': '沐浴露与香皂', '沐浴露/油/乳': '沐浴露与香皂',
    '沐浴露': '沐浴露与香皂', '身体清洁': '沐浴露与香皂',
}

REGION_ZH = {
    'US': '美国', 'ID': '印度尼西亚', 'GB': '英国', 'VN': '越南', 'TH': '泰国',
    'MY': '马来西亚', 'PH': '菲律宾', 'ES': '西班牙', 'MX': '墨西哥', 'DE': '德国',
    'FR': '法国', 'IT': '意大利', 'BR': '巴西', 'JP': '日本', 'SG': '新加坡',
    'AT': '奥地利', 'BE': '比利时', 'NL': '荷兰', 'PL': '波兰', 'PT': '葡萄牙',
    'CN': '中国',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', default=os.path.join(D, 'records_ai.json'))
    ap.add_argument('--out', dest='dst', default=os.path.join(D, 'records_cat.json'))
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()

    # ---- 1. 类目树：三级中文名 -> (平台二级, 一级, cid 链)
    tree = json.load(io.open(os.path.join(D, 'fm_cat_zh.json'), encoding='utf-8'))['tree']
    bpc = [c for c in tree if c['cid'] == '14'][0]
    l3map = {}
    for n2 in bpc['children']:
        for n3 in n2['children']:
            l3map[n3['zh']] = {
                'l2p': n2['zh'], 'l1': L1_OF_PLATFORM_L2.get(n2['zh'], '个护'),
                'func': FUNC_OF_L3.get(n3['zh'], '待归类'),
                'path': '美妆个护 / %s / %s' % (n2['zh'], n3['zh']),
                'cid': '14/%s/%s' % (n2['cid'], n3['cid']),
            }
    print('类目树：平台三级 %d 个，其中已归功能子类 %d 个'
          % (len(l3map), sum(1 for v in l3map.values() if v['func'] != '待归类')))

    # ---- 2. FastMoss 原生路径 + region（按 product_id 回填，最权威）
    fm = {}
    for fn in ('fastmoss_sales_fiber.json', 'fastmoss_new_fiber.json'):
        for r in json.load(io.open(os.path.join(D, fn), encoding='utf-8'))['rows']:
            p = r.get('all_category_name') or []
            if isinstance(p, list) and len(p) == 3:
                fm[str(r['product_id'])] = {'l3': p[2], 'l2p': p[1], 'l1p': p[0], 'region': r.get('region')}
    print('FastMoss 原生类目路径映射 %d 条' % len(fm))

    # ---- 2b. Kimi 判定结果
    try:
        _ai = json.load(io.open(os.path.join(D, 'cat_ai_map.json'), encoding='utf-8'))
        ai_map = {k: v for k, v in _ai.items() if k != '_ver' and v != '未定'}
    except Exception:                                   # noqa: BLE001
        ai_map = {}
    print('Kimi 判定类目 %d 条' % len(ai_map))

    # ---- 3. 逐条映射
    recs = json.load(io.open(args.src, encoding='utf-8'))
    recs = recs['records'] if isinstance(recs, dict) else recs
    unknown_l3 = collections.Counter()
    need_ai = []
    stats = collections.Counter()

    for r in recs:
        pid = str(r.get('商品ID') or '')
        src = r.get('数据来源')
        l3 = None
        region = None

        if src == 'FastMoss' and pid in fm:
            l3 = fm[pid]['l3']
            region = fm[pid]['region']
            stats['fastmoss原生'] += 1
        elif src == '抖音罗盘':
            note = str(r.get('选品笔记') or '')
            import re
            m = re.search(r'行业类目：([^；]+)', note)
            cat = m.group(1).split('/')[-1].strip() if m else ''
            l3 = CN_CAT_TO_L3.get(cat)
            region = 'CN'
            stats['罗盘行业类目' if l3 else '罗盘未识别'] += 1
        # 兜底：Kimi 判定结果（蝉妈妈等无平台类目的源）
        if not l3 and pid in ai_map:
            l3 = ai_map[pid]
            region = region or 'CN'
            stats['Kimi 判定'] += 1
        if l3 and l3 not in l3map:
            unknown_l3[l3] += 1
            l3 = None
        if not l3:
            need_ai.append(r)
            continue

        info = l3map[l3]
        r['一级类目'] = info['l1']
        r['二级类目'] = info['func']
        r['三级类目'] = l3
        r['平台类目路径'] = info['path']
        r['类目ID'] = info['cid']
        r['国家/地区'] = REGION_ZH.get(region or '', region or '')

    print()
    print('=== 确定性映射 ===')
    for k, v in stats.most_common():
        print('  %-14s %d' % (k, v))
    if unknown_l3:
        print('  平台三级名对不上（需修表）：%s' % dict(unknown_l3))
    print('  待映射（交 AI）：%d 条' % len(need_ai))
    print()
    print('未归类功能子类的平台三级：')
    for k, v in collections.Counter(
            l3map[k]['l3' if False else 'func'] for k in l3map).items():
        pass
    miss = [(l3map[k]['func'], k) for k in l3map if l3map[k]['func'] == '待归类']
    if miss:
        print('  剩余 %d 个：%s' % (len(miss), ', '.join(m[1] for m in miss)))

    print()
    print('=== 已映射记录的分布 ===')
    done = [r for r in recs if r.get('三级类目')]
    print('  一级类目:', dict(collections.Counter(r['一级类目'] for r in done)))
    print('  二级类目:', collections.Counter(r['二级类目'] for r in done).most_common())
    print('  国家/地区:', dict(collections.Counter(r['国家/地区'] for r in done)))
    print()
    print('=== 待 AI 映射样例（蝉妈妈等）===')
    for r in need_ai[:12]:
        print('  [%s] %s' % (r.get('数据来源'), str(r.get('商品名称'))[:52]))

    if args.write:
        need = []
        for r in need_ai:
            need.append({
                'id': str(r.get('商品ID') or ''),
                '来源': r.get('数据来源'),
                '标题': str(r.get('商品名称') or '')[:110],
                '现有品类': r.get('品类') or '',
            })
        json.dump({'need': need}, io.open(os.path.join(D, 'cat_need_ai.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print()
        print('已写出待映射清单 data/cat_need_ai.json（%d 条）' % len(need))

    json.dump({'records': recs}, io.open(args.dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写出 %s' % args.dst)


if __name__ == '__main__':
    main()
