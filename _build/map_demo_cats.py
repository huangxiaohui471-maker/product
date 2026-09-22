#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐 40 条示例记录的类目/国家，并修掉探测时污染的那条记录。

发现：示例用的是 v1 时期的「细分品类」词表（面部精华/洁面/洗发…），
与 FastMoss 三级类目词表不同名 → 不能靠同名词匹配，必须逐品名显式映射。
映射目标词表全部取自真实数据的 二级类目 / 三级类目 实际取值，保证可聚合。

用法:
    python3 map_demo_cats.py <token> [--write]
"""
import json
import os
import subprocess
import sys

LIB = '/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/library'
DB = 'Hu5q2PAyW17BmdP5JPQ9os'
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ''
WRITE = '--write' in sys.argv

# 商品名 -> (二级类目, 三级类目)   目标词表取自真实数据取值
MAP = {
    '米颂 蓝铜肽修护精华': ('精华', '面部精华液'),
    '织羽 玻尿酸次抛精华': ('精华', '面部精华液'),
    '珂熙 油痘肌控油洁面': ('面部清洁', '洗面乳'),
    '流明 早C晚A双管精华': ('精华', '面部精华液'),
    '白鹿 氨基酸洗发水': ('头发清洁', '洗发护发'),
    '沐野 头皮精华液': ('头发护理', '头发与头皮养护'),
    '岩青 冻干粉安瓶': ('精华', '面部精华液'),
    '花筏 香氛身体乳': ('身体保湿', '身体霜、乳'),
    '极昼 男士控油素颜霜': ('底妆', '遮瑕与粉底'),
    '织羽 唇部精华油': ('唇妆', '口红与唇彩'),
    '雪澄 屏障修护身体冷霜': ('身体保湿', '身体霜、乳'),
    '多温 积层保湿水乳套装': ('护理套装', '面部护理套装'),
    '雪澄 蜜光唇釉': ('唇妆', '口红与唇彩'),
    '花筏 头皮去角质磨砂膏': ('头发护理', '头发与头皮养护'),
    '素漾 妆前乳': ('底妆', '妆前乳与眼影打底膏'),
    '兰屿 海藻保湿面膜': ('面膜', '面膜'),
    '纽芙 益生菌身体喷雾': ('身体保湿', '身体霜、乳'),
    '松月 以油养肤精华油': ('精华', '面部精华液'),
    '羽白 米糠发酵洁面': ('面部清洁', '洗面乳'),
    '松月 温感按摩膏': ('身体油', '保湿油、按摩油'),
    '花筏 睫毛精华液': ('眼妆', '睫毛增长液与打底膏'),
    '岩兰 木质调香水': ('香水', '男女通用香水'),
    '素漾 头皮按摩梳': ('按摩工具', '手动按摩用品'),
    '奥芮 视黄醇紧致晚霜': ('面部保湿', '保湿乳液、乳霜与喷雾'),
    '岚德 神经酰胺修护霜': ('面部保湿', '保湿乳液、乳霜与喷雾'),
    '珂熙 A醇身体乳': ('身体保湿', '身体霜、乳'),
    '流明 蓝光防护精华': ('精华', '面部精华液'),
    '苔然 头皮微生态精华': ('头发护理', '头发与头皮养护'),
    '极昼 男士抗老精华': ('精华', '面部精华液'),
    '岩青 身体磨砂膏': ('身体去角质', '身体磨砂膏、去角质'),
    '白鹿 视黄醇眼霜': ('眼部护理', '眼部护理'),
    '纽芙 香氛洗手液': ('手足护理', '洗手液'),
    '米颂 控油防晒乳': ('防晒', '脸部防晒霜与晒后修复'),
    '织羽 椰子身体油': ('身体油', '保湿油、按摩油'),
    '珂熙 姜黄亮肤精华': ('精华', '面部精华液'),
    '流明 大米发酵水': ('爽肤水', '爽肤水、化妆水'),
    '沐野 驱蚊身体喷雾': ('特殊个护', '驱虫剂'),
    '素漾 防晒粉饼': ('定妆', '散粉'),
    '极昼 男士头皮洗发水': ('头发清洁', '洗发护发'),
    '岩兰 白桃香氛沐浴露': ('身体清洁', '沐浴露与香皂'),
}

# 大区取代表国家（用户口径 2026-09-20）：欧美以美国为准；东南亚仍是大区，不臆造具体国家
REGION_AS_COUNTRY = {'中国': '中国', '日本': '日本', '韩国': '韩国', '欧美': '美国'}

KOREA = '韩国'


def run(script, args, stdin):
    p = subprocess.run(['python3', os.path.join(LIB, 'database', script)] + args,
                       input=stdin, capture_output=True, text=True)
    return p.stdout or '', p.stderr or ''


def query_all():
    rows, cur = [], ''
    for _ in range(8):
        args = ['--token-stdin', '--database-id', DB, '--page-size', '200']
        if cur:
            args += ['--start-cursor', cur]
        out, _e = run('query_database_record.py', args, TOKEN + '\n')
        try:
            d = json.loads(out)
        except Exception:                                # noqa: BLE001
            print('查询解析失败：%s' % out[:200])
            break
        rows += d.get('results', [])
        cur = d.get('next_cursor') or ''
        if not d.get('has_more'):
            break
    return rows


def main():
    # ---- 0. 先给 国家/地区 补上「韩国」选项（Hwahae / Olive Young 所属市场）----
    out, _ = run('get_database_schema.py', ['--token-stdin', '--database-id', DB], TOKEN + '\n')
    sch = json.loads(out)
    fld = [p for p in sch['properties'] if p['name'] == '国家/地区'][0]
    opts = fld['config']['options']
    names = [o['text'] for o in opts]
    if KOREA not in names:
        if WRITE:
            new_opts = [{'id': o['id'], 'text': o['text'], 'style': o.get('style', 1)} for o in opts]
            new_opts.append({'text': KOREA, 'style': 1})
            prop = {'name': '国家/地区', 'config': {'select': {'options': new_opts}}}
            o2, e2 = run('update_database_field.py',
                         ['--token-stdin', '--database-id', DB, '--field-id', fld['id'],
                          '--property', json.dumps(prop, ensure_ascii=False)], TOKEN + '\n')
            print('加「韩国」选项：%s' % ('OK' if '"properties"' in o2 else (o2 or e2)[:120]))
        else:
            print('（dry-run）将给 国家/地区 加选项「韩国」')
    else:
        print('「韩国」选项已存在')

    # ---- 1. 组更新 ----
    rows = query_all()
    print('云表 %d 条' % len(rows))
    updates, miss, noc = [], [], 0
    for r in rows:
        name = (r.get('商品名称') or '').strip()
        hit = None
        for k, v in MAP.items():
            if name.startswith(k) or k in name:
                hit = v
                break
        props = {}
        if r.get('数据标记') == '示例':
            if hit:
                if r.get('二级类目') != hit[0]:
                    props['二级类目'] = {'text': hit[0]}
                if r.get('三级类目') != hit[1]:
                    props['三级类目'] = {'text': hit[1]}
                if r.get('类目ID'):
                    props['类目ID'] = {'text': None}      # 示例无平台 cid
            else:
                miss.append(name)
            cty = REGION_AS_COUNTRY.get((r.get('所属市场') or '').strip())
            if cty:
                if r.get('国家/地区') != cty:
                    props['国家/地区'] = {'select': cty}
            else:
                noc += 1
        else:
            # 真实记录：清掉探测脚本污染的值（若与本地不一致，本地值优先）
            local = LOCAL.get(r.get('商品ID') or '')
            if local:
                if r.get('二级类目') != local.get('二级类目'):
                    props['二级类目'] = {'text': local.get('二级类目')}
                if r.get('三级类目') != local.get('三级类目'):
                    props['三级类目'] = {'text': local.get('三级类目')}
                want_cid = local.get('类目ID') or ''
                if (r.get('类目ID') or '') != want_cid:
                    props['类目ID'] = {'text': want_cid or None}
        if props:
            updates.append({'record_id': r['record_id'], 'properties': props})

    print('待更新 %d 条 | 示例未命中映射 %d 条 %s | 示例大区无国家 %d 条' % (
        len(updates), len(miss), miss[:5], noc))
    if not WRITE:
        print('（dry-run；加 --write 实际写入）')
        return
    ok = 0
    for i in range(0, len(updates), 100):
        chunk = updates[i:i + 100]
        body = json.dumps({'database_id': DB, 'records': chunk}, ensure_ascii=False)
        out, err = run('batch_update_database_records.py', ['--token-stdin', '--stdin'],
                       TOKEN + '\n' + body)
        n = out.count('"success": true')
        ok += n
        print('  批次 %d：%d 条 → 成功 %d' % (i // 100 + 1, len(chunk), n))
        if n < len(chunk):
            print('    错误片段:', (out or err)[:300].replace('\n', ' '))
    print('合计成功 %d / %d' % (ok, len(updates)))


LOCAL = {}
_src = os.path.join(D, 'records_cat.json')
if os.path.exists(_src):
    _recs = json.load(open(_src, encoding='utf-8'))
    _recs = _recs['records'] if isinstance(_recs, dict) else _recs
    LOCAL = {str(r.get('商品ID') or ''): r for r in _recs if r.get('商品ID')}

if __name__ == '__main__':
    main()
