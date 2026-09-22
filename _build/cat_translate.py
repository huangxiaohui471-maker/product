#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 FastMoss 英文类目树译成中文，并用平台自身产出的 66 条真实中文路径反向校验。

要点：AI 直译会与平台官方译法不一致（Skincare→「护肤」而平台是「美容护肤」），
所以把平台真实中文类目名当「官方词表」喂给模型，要求同义项必须原样复用。
剩余不一致的由 MANUAL 字典收口。

产物 data/fm_cat_zh.json
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kimi  # noqa: E402

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SRC = os.path.join(D, 'fm_cat_tree.json')
OBS = os.path.join(D, 'fm_cat_observed.json')
OUT = os.path.join(D, 'fm_cat_zh.json')
CACHE = os.path.join(D, 'cat_zh_cache_v2.json')

MANUAL = {'14': '美妆个护'}

# 平台官方译名收口：以「英文原名」为键（英文名在美妆个护子树内唯一），
# 消除 AI 用词与平台官方用词的细微差异（如 AI「乳霜与喷雾」vs 平台「保湿乳液、乳霜与喷雾」）
NAME_OVERRIDE = {
    # 洗浴与身体护理
    'Body Care Kits': '身体护理套装',
    'Body Creams & Lotions': '身体霜、乳',
    'Body Wash & Soap': '沐浴露与香皂',
    'Hair Removal Cream, Wax & Shave': '除毛乳、除毛蜜蜡&除毛器',
    'Body Scrubs & Peels': '身体磨砂膏、去角质',
    'Manual Massage Tools': '手动按摩用品',
    'Bathing Accessories': '洗澡工具',
    'Body & Massage Oil': '保湿油、按摩油',
    # 美容护肤
    'Facial Sunscreen & Sun Care': '脸部防晒霜与晒后修复',
    'Toners': '爽肤水、化妆水',
    'Facial Cleansers': '洗面乳',
    'Skin Care Kits': '面部护理套装',
    'Moisturizers & Mists': '保湿乳液、乳霜与喷雾',
    'Face Masks': '面膜',
    'Serums & Essences': '面部精华液',
    'Eye Treatments': '眼部护理',
    'Skincare Tools': '面部护理工具',
    'Acne Treatments': '痘痘、粉刺护理',
    'Lip Treatments': '唇部护理',
    'Face Scrubs & Peels': '面部磨砂膏与去角质',
    'Nasal Treatment': '鼻部清洁用品',
    # 手足及指甲护理
    'Hand & Foot Masks': '手足膜',
    'Hand Lotions, Creams & Scrubs': '护手足霜、乳液与磨砂膏',
    'Manicure & Pedicure Tools': '手足工具与配件',
    'Nail Art & Nail Polish': '指甲油',
    'Nail Treatments': '指甲护理',
    # 美妆
    'Lipstick & Lip Gloss': '口红与唇彩',
    'Concealer & Foundation': '遮瑕与粉底',
    'False Eyelashes & Adhesives': '假睫毛与胶水',
    'Makeup Tools': '化妆工具',
    'Makeup Fixing Spray': '定妆喷雾',
    'Eyebrow Pencils/Powder/Paste': '眉笔&眉粉&眉胶',
    'Eyeliner & Lipliner': '眼线笔与唇线笔',
    'Makeup Remover': '卸妆',
    'Makeup Sets': '美妆套装',
    'Blush': '腮红',
    'Mascara': '睫毛膏',
    'Makeup Base and Primers': '妆前乳与眼影打底膏',
    'Blemish Balm and Color Control': 'BB霜与CC霜',
    'Powder Puffs': '粉扑',
    # 头部护理与造型
    'Shampoo & Conditioner': '洗发护发',
    'Hair Treatments/Scalp Treatments': '头发与头皮养护',
    'Hair Loss Products': '脱发产品',
    'Hair Dye': '染发用品',
    # 香水
    'Unisex Perfume': '男女通用香水',
    'Women\'s Fragrance': '女士香水',
    'Men\'s Fragrance': '男士香水',
    'Perfume Sets': '香水套装',
    # 鼻子口腔护理
    'Toothpastes': '牙膏',
    'Oral Spray': '口腔喷剂',
    'Toothbrushes': '手动牙刷',
    'Dental Floss & Picks': '牙线和牙签',
    'Nasal Cleaning': '鼻部清洁用品',
    # 女性私密处护理
    'Feminine Hygiene': '私密处清洁用品',
    'Sanitary Towels': '卫生巾',
    # 男士护理
    'Manual Shaving Accessories': '男士手动剃须工具',
    # 特殊个护
    'Heat Patches': '暖宝宝',
    'Adult Diapers': '成人纸尿裤',
    'Insect Repellents': '驱虫剂',
    # 个护电器
    'Massage Devices': '按摩器',
    'Curlers & Straighteners': '卷、直发器',
    'Hair Trimmers & Clippers': '理发器',
    # 二级
    'Personal Care Appliances': '美容、个护电器',
    # 眼镜耳朵护理
    'Sleep Masks': '眼罩',
    'Earwax Removal Products': '耳垢清洁产品和工具',
}


# 英文名有歧义时按 cid 精确指定（Men's Care 下的 Bath & Body Care 与二级同名）
CID_OVERRIDE = {
    '601520': '男士洗浴与身体护理',
    '849416': '美容、个护电器',
}


def apply_cid_override(node):
    if node.get('cid') in CID_OVERRIDE:
        node['zh'] = CID_OVERRIDE[node['cid']]
    for c in node.get('children') or []:
        apply_cid_override(c)
    return node


def apply_name_override(node):
    """按英文原名对齐平台官方中文名，逐层递归。"""
    if node.get('name') in NAME_OVERRIDE:
        node['zh'] = NAME_OVERRIDE[node['name']]
    for c in node.get('children') or []:
        apply_name_override(c)
    return node


SYS = (
    '你是 TikTok Shop / FastMoss 的类目本地化专家，任务是给英文商品类目选定**该平台官方中文站使用的类目名**。\n'
    '铁律：\n'
    '1. 只输出 JSON 对象，键是用户给的编号（原样字符串），值是中文类目名；不要解释、不要 markdown 代码块。\n'
    '2. 用户会给一份「平台官方词表」。若某个英文类目与词表中某词语义相同，**必须原样照抄该词**，不得换用别的说法。\n'
    '3. 词表里没有的，用跨境电商美妆行业通用译法，简洁（2-10 字），不加「类」「其他」等冗余词。\n'
    '4. 严格按给定英文原名翻译，不合并、不拆分、不漏项。\n'
)


def load_cache():
    try:
        return json.load(io.open(CACHE, encoding='utf-8'))
    except Exception:                       # noqa: BLE001
        return {}


def save_cache(c):
    json.dump(c, io.open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def translate(items, cache, glossary, tag, batch=90):
    """items = [(cid, english)] -> {cid: 中文}；分批调用，术语表随包附上。"""
    todo = [(k, e) for k, e in items if k not in cache]
    if todo:
        gl = '平台官方词表（同义必须原样复用）：' + '、'.join(sorted(set(glossary)))
        for i in range(0, len(todo), batch):
            part = todo[i:i + batch]
            lines = '\n'.join('%s\t%s' % (k, e) for k, e in part)
            user = (gl + '\n\n把下面英文类目译成中文，输出 JSON：{"编号":"中文名", ...}\n\n' + lines)
            got = None
            for mt in (5000, 8000):
                try:
                    got = kimi.chat_json(SYS, user, max_tokens=mt)
                except Exception as e:      # noqa: BLE001
                    print('  [%s] 调用失败 %s' % (tag, str(e)[:120]))
                    continue
                if isinstance(got, dict) and len(got) >= len(part) * 0.8:
                    break
            if not isinstance(got, dict):
                got = {}
            ok = 0
            for k, e in part:
                v = got.get(k) or got.get(str(k))
                if v and any('\u4e00' <= ch <= '\u9fff' for ch in str(v)):
                    cache[k] = str(v).strip()
                    ok += 1
                else:
                    cache[k] = e               # 兜底英文，后续 MANUAL 或人工收口
            save_cache(cache)
            print('  [%s] 第 %d 批：%d/%d 拿到中文' % (tag, i // batch + 1, ok, len(part)))
    return {k: cache.get(k, e) for k, e in items}


def main():
    tree = json.load(io.open(SRC, encoding='utf-8'))['tree']
    obs = json.load(io.open(OBS, encoding='utf-8'))
    cache = load_cache()

    bpc = [c for c in tree if c['cid'] == '14'][0]
    l1 = [(c['cid'], c['name']) for c in tree]
    l2 = [(c['cid'], c['name']) for c in bpc['children']]
    l3 = [(s['cid'], s['name']) for c in bpc['children'] for s in c['children']]

    glossary = set()
    for p in obs:
        _, a, b = p.split(' > ')
        glossary.add(a)
        glossary.add(b)
    print('官方词表 %d 个词' % len(glossary))

    zh1 = translate(l1, cache, glossary, 'L1')
    zh2 = translate(l2, cache, glossary, 'L2')
    zh3 = translate(l3, cache, glossary, 'L3')

    # MANUAL 收口（最高优先级）
    zh1.update({k: v for k, v in MANUAL.items() if k in zh1})
    zh2.update({k: v for k, v in MANUAL.items() if k in zh2})
    zh3.update({k: v for k, v in MANUAL.items() if k in zh3})

    out = []
    for c in tree:
        node = {'cid': c['cid'], 'name': c['name'], 'zh': zh1.get(c['cid'], c['name']), 'children': []}
        if c['cid'] == '14':
            for s2 in c['children']:
                n2 = {'cid': s2['cid'], 'name': s2['name'], 'zh': zh2.get(s2['cid'], s2['name']), 'children': []}
                for s3 in s2['children']:
                    n2['children'].append({'cid': s3['cid'], 'name': s3['name'], 'zh': zh3.get(s3['cid'], s3['name'])})
                node['children'].append(n2)
        out.append(node)

    f = [c for c in out if c['cid'] == '14'][0]
    apply_name_override(f)
    apply_cid_override(f)
    bnode = f
    zh_paths = set((n2['zh'], n3['zh']) for n2 in bnode['children'] for n3 in n2['children'])
    match, miss = 0, []
    for p in obs:
        _, a, b = p.split(' > ')
        if (a, b) in zh_paths:
            match += 1
        else:
            miss.append(p)
    print()
    print('=== 校验：观测 %d 条，命中 %d 条（%.0f%%）===' % (len(obs), match, 100.0 * match / len(obs)))
    for m in miss:
        print('   未命中：' + m)

    json.dump({'source': 'FastMoss filterInfo + Kimi 译名（平台真实中文路径校验）',
               'validate': {'total': len(obs), 'match': match, 'mismatch': miss},
               'tree': out},
              io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('SAVED ' + OUT)
    print()
    print('=== 美妆个护（中文）===')
    for n2 in bnode['children']:
        print('  %s [%s] 三级 %d' % (n2['zh'], n2['cid'], len(n2['children'])))
        print('      ' + ' / '.join(x['zh'] for x in n2['children']))


if __name__ == '__main__':
    main()
