#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Kimi 给三平台真实数据做「有源增强」——只做转换与归纳，绝不生成没有来源的字段。

做两件事（都基于已抓到的真实字段）：
  A. 外文标题 → 中文品名 + 品类 + 细分品类
     东南亚/欧美榜单的标题是越南语／印尼语／泰语／英语，规则映射覆盖不全。
     中文品名与规范品类是选品决策的第一屏信息。
  B. 选品笔记追加「AI 速读」一句话
     严格限定「只能用给定的数字」，禁止引入任何未提供的信息（不编品牌、不编成分、不编评价）。

明确不做：
  - 不生成「好评关键词」「差评关键词」——没有真实评价文本就是造假。
    抓到评价原文后，用 `--reviews <file>` 走评价归纳模式（预留）。

缓存：data/ai_cache.json（按 商品ID + 任务版本 命中即跳过，日常重跑不重复烧 token）

用法:
    python3 ai_enrich.py                       # 处理 data/records_v4.json → data/records_ai.json
    python3 ai_enrich.py --in data/records_v4.json --out data/records_ai.json
    python3 ai_enrich.py --limit 40            # 只处理前 40 条（试跑）
"""
import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kimi  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, 'data')
CACHE_PATH = os.path.join(D, 'ai_cache.json')
TASK_VER = 'v2'          # 改了 prompt 就升版，缓存自动失效
BATCH = 12               # 任务A 每次调用送多少条（实测 12 条 / 1800 token 最稳）
MAXTOK = 1800            # 这模型是纯推理型，token 给太少会把输出全吃掉 → 返回空串
BATCH_B = 8              # 任务B 每批条数（速读比译名长，8 条 / 2500 token 实测稳）
MAXTOK_B = 2500

CATS = ['护肤', '彩妆', '个护', '身体', '香氛', '工具']

SYS_A = (
    '你是美妆个护选品分析师。用户给你一批来自 TikTok 榜单的商品，标题可能是越南语、印尼语、'
    '泰语、英语或中文。请对每条输出规范化的中文信息。\n'
    '严格规则：\n'
    '1. 只输出 JSON 数组，不要任何解释、不要 markdown 围栏。\n'
    '2. 数组长度必须与输入条数完全一致，顺序一致，每项含 name / cat / sub 三个字段。\n'
    '3. name 必须是**中文**品名（不超过 18 字），**严禁照抄原外文标题**；概括「品类 + 关键属性」，'
    '标题里明确写了品牌才带品牌。\n'
    '4. cat 必须严格取自这些值之一：' + ' / '.join(CATS) + '。\n'
    '5. sub = 中文细分品类（不超过 12 字，如「洗面奶」「面部精华」「睫毛膏」「沐浴露」「女士香水」）。\n'
    '6. 只依据标题字面意思判断，不要臆造成分、功效认证或品牌。'
)

SYS_B = (
    '你是选品分析师。用户给出一批商品的真实榜单数据（按编号排列）。请为每一条输出一句不超过 55 字的客观速读。\n'
    '铁律：\n'
    '1. 每句只能使用该条自己给出的数字与字段，严禁补充任何未提供的信息（不得提成分、功效、评价、退货、'
    '价格、竞品、销量预测、品牌背景）。\n'
    '2. 单句结构：市场/品类 + 规模（销量或销售额，有才写）+ 增速判断 + 达人渗透度判断。\n'
    '3. 达人渗透度按此口径：关联达人数 ≤50 记为「尚未铺开」，≤150 记为「正在起量」，>150 记为「已铺开」；'
    '字段缺失就直接写「达人渗透未披露」，不要猜。\n'
    '4. 只输出 JSON 数组，元素是**中文字符串**，长度与输入条数完全一致、顺序一致。'
    '不要 markdown 围栏、不要解释、不要额外字段。'
)


def key_of(rec, task):
    raw = '|'.join([TASK_VER, task, str(rec.get('商品ID') or ''), str(rec.get('商品名称') or '')])
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            return json.load(open(CACHE_PATH, encoding='utf-8'))
        except Exception:                                # noqa: BLE001
            pass
    return {}


def save_cache(c):
    json.dump(c, open(CACHE_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


def has_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in (s or ''))


def is_foreign(title):
    """标题基本没有中文 → 需要翻译"""
    t = title or ''
    if not t.strip():
        return False
    cjk = sum(1 for ch in t if '\u4e00' <= ch <= '\u9fff')
    return cjk < max(1, len(t) * 0.15)


def call_batch(chunk):
    """调一次模型；返回 list 或 None。条数不匹配 / 输出为空 → None，由上层拆半重试。"""
    lines = []
    for n, (_k, r) in enumerate(chunk, 1):
        l3 = r.get('细分品类') or ''
        lines.append('%d. %s%s' % (n, r.get('商品名称') or '',
                                   ('（源站类目：%s）' % l3) if l3 else ''))
    try:
        out = kimi.chat_json(SYS_A, '\n'.join(lines), max_tokens=MAXTOK)
    except Exception as e:                               # noqa: BLE001
        print('    调用失败：%s' % str(e)[:110])
        return None
    if not isinstance(out, list) or len(out) != len(chunk):
        print('    条数不匹配（%s vs %d）'
              % (len(out) if isinstance(out, list) else type(out).__name__, len(chunk)))
        return None
    # 校验：中文品名必须真的含中文，否则视为偷懒照抄
    for item in out:
        if not isinstance(item, dict) or not has_cjk(str(item.get('name') or '')):
            print('    校验不过：name 非中文 %s' % str(item)[:80])
            return None
    return out


def enrich_names(records, cache, limit=None):
    """任务 A：外文标题 → 中文品名 + 品类 + 细分品类"""
    todo = []
    for r in records:
        if not is_foreign(r.get('商品名称')):
            continue
        k = key_of(r, 'name')
        if k in cache:
            for f in ('名称中文', '品类', '细分品类'):
                if cache[k].get(f):
                    r[f] = cache[k][f]
            continue
        todo.append((k, r))
    if limit:
        todo = todo[:limit]
    print('[A] 需要翻译的外文标题 %d 条' % len(todo))

    done = 0
    queue = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    while queue:
        chunk = queue.pop(0)
        out = call_batch(chunk)
        if out is None:
            if len(chunk) > 1:                           # 拆半重试，直到单条
                half = len(chunk) // 2
                queue.insert(0, chunk[half:])
                queue.insert(0, chunk[:half])
                print('    拆为 %d + %d 条重试' % (half, len(chunk) - half))
                continue
            print('    单条仍失败，跳过')
            continue
        for (k, r), item in zip(chunk, out):
            name = str(item.get('name') or '').strip()
            cat = str(item.get('cat') or '').strip()
            sub = str(item.get('sub') or '').strip()
            if cat not in CATS:
                cat = ''
            rec = {'名称中文': name, '品类': cat, '细分品类': sub}
            cache[k] = rec
            for f, v in rec.items():
                if v:
                    r[f] = v
            done += 1
        print('  完成一批 %d 条（累计 %d，剩 %d 批）' % (len(chunk), done, len(queue)))
        save_cache(cache)
        time.sleep(0.8)
    return done


def note_bits(r):
    """把一条记录压缩成给模型看的事实串（只含真实字段）。"""
    bits = []
    for f in ('名称中文', '商品名称', '品类', '细分品类', '所属市场', '数据来源'):
        if r.get(f):
            bits.append('%s：%s' % (f, r[f]))
    for f, unit in (('销量', ''), ('环比增速', '%'), ('关联达人数', '个'), ('销售额', '元')):
        v = r.get(f)
        if v is not None:
            bits.append('%s：%s%s' % (f, v, unit))
    if r.get('榜单排名'):
        bits.append('榜单：%s' % r['榜单排名'])
    return '；'.join(bits)


def notes_batch(chunk):
    """调一次模型生成一批速读；返回 list[str] 或 None（由上层拆半重试）。"""
    lines = ['%d. %s' % (n, note_bits(r)) for n, (_k, r) in enumerate(chunk, 1)]
    try:
        out = kimi.chat_json(SYS_B, '\n'.join(lines), max_tokens=MAXTOK_B)
    except Exception as e:                               # noqa: BLE001
        print('    调用失败：%s' % str(e)[:110])
        return None
    if not isinstance(out, list) or len(out) != len(chunk):
        print('    条数不匹配（%s vs %d）'
              % (len(out) if isinstance(out, list) else type(out).__name__, len(chunk)))
        return None
    res = []
    for item in out:
        s = item if isinstance(item, str) else (
            item.get('note') or item.get('text') or '' if isinstance(item, dict) else '')
        s = (s or '').strip().replace('\n', ' ')
        if not s or not has_cjk(s):
            print('    校验不过：%s' % str(item)[:70])
            return None
        res.append(s[:140])
    return res


def enrich_notes(records, cache, limit=None):
    """任务 B：选品笔记的「AI 速读」——批量生成，拆半重试"""
    todo = []
    for r in records:
        k = key_of(r, 'note')
        if k in cache:
            r['_note_ai'] = cache[k]
            continue
        todo.append((k, r))
    if limit:
        todo = todo[:limit]
    print('[B] 需要生成速读 %d 条' % len(todo))

    done = 0
    queue = [todo[i:i + BATCH_B] for i in range(0, len(todo), BATCH_B)]
    total_batches = len(queue)
    while queue:
        chunk = queue.pop(0)
        out = notes_batch(chunk)
        if out is None:
            if len(chunk) > 1:
                half = len(chunk) // 2
                queue.insert(0, chunk[half:])
                queue.insert(0, chunk[:half])
                print('    拆为 %d + %d 条重试' % (half, len(chunk) - half))
                continue
            print('    单条仍失败，跳过')
            continue
        for (k, r), txt in zip(chunk, out):
            cache[k] = txt
            r['_note_ai'] = txt
            done += 1
        print('  速读完成 %d 条（累计 %d，剩 %d 批/%d）'
              % (len(chunk), done, len(queue), total_batches))
        save_cache(cache)
        time.sleep(0.8)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', default=os.path.join(D, 'records_v4.json'))
    ap.add_argument('--out', dest='dst', default=os.path.join(D, 'records_ai.json'))
    ap.add_argument('--limit', type=int, default=0, help='限制处理条数（试跑用）')
    ap.add_argument('--no-note', action='store_true', help='跳过速读生成（只翻译标题）')
    args = ap.parse_args()

    src = json.load(open(args.src, encoding='utf-8'))
    records = src['records'] if isinstance(src, dict) else src
    print('读入 %d 条：%s' % (len(records), args.src))

    cache = load_cache()
    print('缓存已有 %d 条' % len(cache))

    n_at = enrich_names(records, cache, args.limit or None)
    n_bt = 0 if args.no_note else enrich_notes(records, cache, args.limit or None)

    # 把 AI 速读并进选品笔记（不覆盖原有事实性笔记，只追加一行）
    merged = 0
    for r in records:
        ai = r.pop('_note_ai', None)
        if ai and ai not in (r.get('选品笔记') or ''):
            r['选品笔记'] = ((r.get('选品笔记') or '').rstrip() + '\nAI 速读：' + ai).strip()
            merged += 1
        old = r.get('商品名称') or ''
        new = r.get('名称中文') or ''
        if new and new != old and ('中文品名：' + new) not in (r.get('选品笔记') or ''):
            r['选品笔记'] = ('中文品名：%s\n' % new + (r.get('选品笔记') or '')).strip()
        r.pop('名称中文', None)

    json.dump({'count': len(records), 'records': records},
              open(args.dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写入 %s：%d 条' % (args.dst, len(records)))
    print('  任务A 新翻译 %d 条 | 任务B 新速读 %d 条 | 笔记合并 %d 条' % (n_at, n_bt, merged))
    cat_empty = sum(1 for r in records if not r.get('品类'))
    print('  品类为空 %d 条（AI 已兜底）' % cat_empty)


if __name__ == '__main__':
    main()
