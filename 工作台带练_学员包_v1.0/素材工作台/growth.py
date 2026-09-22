"""Account reviews over the original growth ledger; inference belongs to the host Agent."""
from __future__ import annotations
import copy
import hashlib
import json
import uuid
from datetime import datetime
from workspace import read, write, now, load_engine


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ledger(w):
    return read(w.engine / 'growth/content_ledger.json', {'items': []})


def review_path(w, rid):
    if not isinstance(rid, str) or not rid or any(c not in '0123456789abcdef-' for c in rid):
        raise ValueError('复盘编号无效')
    return w.engine / 'growth/reviews' / (rid + '.json')


def get_review(w, rid):
    result = read(review_path(w, rid))
    if not result:
        raise ValueError('这份复盘不存在')
    return result


def current_scope(w, review):
    refs = {(x['channel'], x['content_id']) for x in review['scope']}
    return [x for x in ledger(w)['items'] if (x['channel'], x['content_id']) in refs]


def stale(w, review):
    return review.get('context_revision') != w.context_revision() or fingerprint(current_scope(w, review)) != review['scope_revision']


def state(w):
    reviews = [read(p) for p in sorted((w.engine / 'growth/reviews').glob('*.json'))]
    reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    for r in reviews:
        r['stale'] = stale(w, r)
    return {'reviews': reviews, 'ledger_revision': fingerprint(ledger(w)),
            'handoff': read(w.engine / 'handoffs/growth_to_strategy.json')}


def request_review(w, message, review_id=None):
    with w.lock:
        if review_id:
            get_review(w, review_id)
            for path in (w.engine / 'requests').glob('*.json'):
                previous = read(path)
                if previous.get('kind') == 'next_cycle' and previous.get('review_id') == review_id and previous.get('status') == 'queued':
                    previous.update({'status': 'needs_review', 'reason': '复盘收到新资料或纠正，先更新判断'})
                    write(path, previous)
            handoff = read(w.engine / 'handoffs/growth_to_strategy.json')
            if handoff.get('review_id') == review_id and handoff.get('status') == 'ready_for_strategy':
                handoff['status'] = 'needs_review'
                write(w.engine / 'handoffs/growth_to_strategy.json', handoff)
        r = w.request('growth_review', message or '读取已有内容、数据与评论，完成复盘并提出下一轮建议')
        r.update({'review_id': review_id, 'ledger_revision': fingerprint(ledger(w))})
        write(w.engine / 'requests' / (r['id'] + '.json'), r)
        return r


def save_review(w, request, result):
    """Persist Agent-authored diagnosis only after validating its actual source records."""
    existing = next((read(p) for p in (w.engine / 'growth/reviews').glob('*.json') if read(p).get('request_id') == request['id']), None)
    if existing:
        return {'review_id': existing['id'], 'summary': existing['diagnosis']['summary']}
    before = ledger(w)
    if result.get('ledger_revision') != fingerprint(before):
        raise ValueError('数据已变化，请重新读取数据和评论再复盘')
    merged = copy.deepcopy(before)
    if result.get('batch'):
        # Reuse original incremental ledger. Every row keeps the actual channel and source.
        merged = load_engine('operate-content-growth-lead', 'update_content_ledger').update(merged, result['batch'])
    d = copy.deepcopy(result.get('diagnosis') or {})
    scope = result.get('scope') or []
    refs = {(x.get('channel'), x.get('content_id')) for x in scope}
    rows = [x for x in merged['items'] if (x['channel'], x['content_id']) in refs]
    if not rows or len(rows) != len(refs):
        raise ValueError('复盘需要对应已导入的具体内容与来源')
    if len({x['content_id'] for x in rows}) != len(rows):
        raise ValueError('本轮作品编号重复，请分渠道复盘')
    if d.get('schema_version') != 'batch_diagnosis/v1' or not d.get('items') or not d.get('summary'):
        raise ValueError('需要完整复盘、整体判断和逐条依据')
    errors = load_engine('operate-content-growth-lead', 'validate_diagnosis').validate(d, {'items': rows})
    if errors:
        raise ValueError('复盘依据不完整：' + '；'.join(errors))
    plans = d.get('next_actions') or []
    seen = set()
    for p in plans:
        if not p.get('id') or p['id'] in seen or not all(p.get(k) for k in ['title', 'change', 'keep', 'start_condition', 'source_ids']):
            raise ValueError('下一轮需要具体依据、保持项、改变项和开始条件')
        if not set(p['source_ids']).issubset({x['content_id'] for x in rows}):
            raise ValueError('下一轮引用了本轮之外的内容')
        seen.add(p['id'])
    rid = uuid.uuid4().hex
    review = {'id': rid, 'request_id': request['id'], 'created_at': datetime.now().astimezone().isoformat(), 'label': result.get('label') or '内容复盘',
              'context_revision': w.context_revision(), 'scope': scope, 'scope_revision': fingerprint(rows),
              'ledger_snapshot': {'schema_version': 'content_ledger/v1', 'items': rows}, 'diagnosis': d,
              'source_note': result.get('source_note') or '', 'previous_review_id': request.get('review_id')}
    # A corrected review supersedes its predecessor but preserves the prior document and observations.
    write(w.engine / 'growth/content_ledger.json', merged)
    write(review_path(w, rid), review)
    write(w.engine / 'growth/batch_diagnosis.json', d)
    return {'review_id': rid, 'summary': d['summary']}


def start_next(w, rid, plan_id):
    with w.lock:
        review = get_review(w, rid)
        if stale(w, review):
            raise ValueError('数据或业务已更新，先让 AI 更新这份复盘')
        if any(read(p).get('previous_review_id') == rid for p in (w.engine / 'growth/reviews').glob('*.json')):
            raise ValueError('已有更新的复盘，请从新版继续')
        requests = [read(p) for p in (w.engine / 'requests').glob('*.json')]
        if any(r.get('kind') == 'growth_review' and r.get('review_id') == rid and r.get('status') == 'queued' for r in requests):
            raise ValueError('这份复盘有待处理的纠正，先让 AI 更新判断')
        for r in requests:
            if r.get('review_id') == rid and r.get('plan_id') == plan_id and r.get('kind') == 'next_cycle':
                return r
        if any(r.get('kind') == 'next_cycle' and r.get('growth_handoff_ref') and r.get('status') == 'queued' for r in requests):
            raise ValueError('已有一项下一轮任务待处理，先接完这一项')
        plan = next((p for p in review['diagnosis'].get('next_actions', []) if p['id'] == plan_id), None)
        if not plan:
            raise ValueError('没有这项下一轮建议')
        r = w.request('next_cycle', plan['title'])
        handoff = {'schema_version': 'growth_to_strategy/v1', 'status': 'ready_for_strategy', 'created_at': now(),
                   'review_id': rid, 'plan_id': plan_id, 'request_id': r['id'], 'context_revision': w.context_revision(),
                   'direction': plan['title'], 'change': plan['change'], 'keep': plan['keep'],
                   'start_condition': plan['start_condition'], 'measurement': plan.get('measurement'),
                   'source_content': [x for x in review['ledger_snapshot']['items'] if x['content_id'] in plan['source_ids']],
                   'source_review_ref': 'growth/reviews/' + rid + '.json'}
        ref = 'handoffs/growth_to_strategy_' + r['id'] + '.json'
        r.update({'review_id': rid, 'plan_id': plan_id, 'growth_handoff_ref': ref})
        write(w.engine / ref, handoff)
        write(w.engine / 'handoffs/growth_to_strategy.json', handoff)
        write(w.engine / 'requests' / (r['id'] + '.json'), r)
        return r


def finish_strategy(w, request, result):
    if not request.get('growth_handoff_ref'):
        raise ValueError('旧版反馈须先由增长负责人复盘，再交回策略；不能直接改旧稿')
    review = get_review(w, request['review_id'])
    if stale(w, review):
        raise ValueError('复盘依据已变化，请重新核对后再继续')
    others = [read(p) for p in (w.engine / 'requests').glob('*.json')]
    if any(r.get('kind') == 'growth_review' and r.get('review_id') == review['id'] and r.get('status') == 'queued' for r in others):
        raise ValueError('这份复盘有新纠正，先接回增长负责人')
    if any(read(p).get('previous_review_id') == review['id'] for p in (w.engine / 'growth/reviews').glob('*.json')):
        raise ValueError('已有新复盘，不能继续提交旧判断')
    ref = result.get('strategy_handoff_ref')
    if not isinstance(ref, str) or not ref:
        raise ValueError('下一轮必须先形成策略到生产的交接，不能提交一段改稿冒充完成')
    s = read(w._inside(w.engine / ref))
    if s.get('schema_version') != 'strategy_to_production/v1' or s.get('growth_handoff_ref') != request['growth_handoff_ref']:
        raise ValueError('新策略必须引用这次真实复盘回流')
    errors = load_engine('operate-ai-content-flywheel', 'contract_gate').validate(s)
    if errors or s.get('status') != 'ready_for_production':
        raise ValueError('策略交接还未完整：' + '；'.join(errors))
    shared = read(w.engine / 'context/shared_enterprise_context.json')
    if not shared or s.get('context_id') != shared.get('context_id'):
        raise ValueError('新策略与当前企业不一致')
    handoff = read(w.engine / request['growth_handoff_ref'])
    if s.get('task_id') in {x.get('production_ref') for x in handoff['source_content']}:
        raise ValueError('下一轮策略需新建任务，不得覆盖原作品与结果')
    path = w._bundle_path(s.get('task_id'))
    existing = read(path)
    if existing and existing.get('growth_request_id') != request['id']:
        raise ValueError('这项任务已存在，请保留旧任务并建立新任务')
    if not existing:
        bundle = load_engine('operate-content-production-lead', 'init_production_run').initialize(s)
        bundle.update({'context_revision': w.context_revision(), 'workbench_versions': [], 'growth_request_id': request['id'],
                       'growth_review_id': review['id']})
        write(w.engine / 'handoffs' / ('strategy_to_production_' + s['task_id'] + '.json'), s)
        write(path, bundle)
    if not any(r.get('kind') == 'production' and r.get('task_id') == s['task_id'] for r in others):
        w.request('production', '按照复盘后更新的策略做出新内容；保留保持项，落实本轮改变项', task_id=s['task_id'])
    handoff.update({'status': 'strategy_completed', 'strategy_handoff_ref': ref, 'task_id': s['task_id']})
    write(w.engine / request['growth_handoff_ref'], handoff)
    current = read(w.engine / 'handoffs/growth_to_strategy.json')
    if current.get('request_id') == request['id']:
        write(w.engine / 'handoffs/growth_to_strategy.json', handoff)
    return {'task_id': s['task_id'], 'summary': '下一轮方向已形成，正在等待制作新内容'}


def request_data(w, message):
    """Data organization is a complete independent job, with no mandatory diagnosis."""
    r = w.request('growth_data', message or '读取并整理已有内容数据，保留来源、时间和历史记录')
    r['ledger_revision'] = fingerprint(ledger(w))
    write(w.engine / 'requests' / (r['id'] + '.json'), r)
    return r


def save_data(w, request, result):
    current = ledger(w)
    if result.get('ledger_revision') != fingerprint(current):
        raise ValueError('数据已更新，请重读后再合并')
    batch = result.get('batch') or {}
    if not batch.get('items'):
        raise ValueError('需要实际读取到的内容数据与来源')
    for row in batch['items']:
        if not row.get('observed_at'):
            raise ValueError('请保留实际采集时间，不能用导入时间代替')
    updated = load_engine('operate-content-growth-lead', 'update_content_ledger').update(copy.deepcopy(current), batch)
    write(w.engine / 'growth/content_ledger.json', updated)
    return {'data_imported': True, 'summary': '已整理并保存 ' + str(len(batch['items'])) + ' 条内容数据'}
