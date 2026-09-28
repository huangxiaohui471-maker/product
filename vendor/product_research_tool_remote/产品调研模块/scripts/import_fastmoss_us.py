import csv
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ZIP_PATH = Path('/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/FastMoss_US美妆Top20_数据包_20260928.zip')
OUT_PATH = Path(__file__).resolve().parents[1] / 'data' / 'fastmoss-us-top20.js'
ROOT = 'FastMoss_US美妆Top20_数据包_20260928/'


def read_json(z, name, default=None):
    try:
        return json.loads(z.read(ROOT + name))
    except Exception:
        return default


def read_csv(z, name):
    return list(csv.DictReader(io.StringIO(z.read(ROOT + name).decode('utf-8-sig'))))


def num(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(',', '')
    if not text or text in {'-', '—', '/', 'None', 'null'}:
        return None
    try:
        return float(re.sub(r'[^0-9.+-]', '', text))
    except ValueError:
        return None


def compact(value, currency=''):
    value = num(value)
    if value is None:
        return '—'
    sign = '-' if value < 0 else ''
    value = abs(value)
    if value >= 100000000:
        text = f'{value / 100000000:.2f}亿'
    elif value >= 10000:
        text = f'{value / 10000:.2f}万'
    elif value >= 1000:
        text = f'{value / 1000:.2f}k'
    else:
        text = f'{value:.0f}'
    return ('$' + sign + text) if currency == 'USD' else sign + text


def money_label(value):
    value = num(value)
    if value is None:
        return '—'
    return '$' + (f'{value:.2f}' if value < 100 else f'{value:,.0f}')


def rank_of(value):
    match = re.search(r'(?:第\s*)?(\d+)\s*名', str(value or ''))
    if match:
        return int(match.group(1))
    match = re.search(r'\d+', str(value or ''))
    return int(match.group()) if match else 0


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def tokens(text):
    stop = set('the and for with this that from your you are our to of in on a an is it its as or at by be have has had was were will can just not but more less very new official shop serum skin care beauty product use using get got all one two pack'.split())
    return [word for word in re.findall(r'[a-z][a-z0-9-]{2,}', clean(text).lower()) if word not in stop]


def percent_items(items):
    total = sum(item['count'] for item in items)
    return [
        {'k': item['name'], 'c': item['count'], 'r': f"{item['count'] / total * 100:.2f}%" if total else '—'}
        for item in items[:12]
    ]


def distribution(data):
    names = {
        'common.goods.product_card': '商品卡',
        'common.goods.shop_account': '品牌自营',
        'common.goods.affiliate': '达人推广',
        'video.name': '视频',
        'live.name': '直播',
    }
    result = []
    for item in ((data or {}).get('gmv') or {}).get('list', []):
        name = item.get('source') or item.get('category') or ''
        result.append({
            'name': names.get(name, name.split('.')[-1] if '.' in name else name),
            'gmv': item.get('sale_amount_show') or item.get('sold_count_show') or '—',
            'pct': item.get('propotion') or '—',
        })
    return result


def video_row(item, authors):
    video_id = str(item.get('video_id') or '')
    author = item.get('author_name') or '—'
    unique_id = authors.get(author, '')
    share = f'https://www.tiktok.com/@{unique_id}/video/{video_id}' if unique_id else f'https://www.tiktok.com/video/{video_id}'
    description = clean(item.get('desc') or '（无视频文案）')
    duration = str(item.get('duration') or '—')
    seconds = '—'
    match = re.match(r'(\d+):([0-5]?\d)', duration)
    if match:
        seconds = int(match.group(1)) * 60 + int(match.group(2))
    return {
        'awemeId': video_id, 'share': share, 'cover': item.get('cover') or '',
        'desc': description, 'dur': duration, 'durs': seconds,
        'gmv': compact(item.get('sale_amount'), 'USD'), 'volume': compact(item.get('sold_count')),
        'gpm': '—', 'blogger': author, 'bt': 'TikTok Creator', 'fans': '—', 'tier': '—',
        'pub': item.get('create_date') or '—', 'keep': True, 'excluded': [],
        'hook': description[:90], 'painC': [], 'beneC': [], 'crowdC': [], 'sceneC': [],
        'frameType': '原始视频数据',
        'analysis': {'亮点': '保留 FastMoss 视频原文与互动/成交指标。', '转化点': '以实际成交量和销售额判断，不补写画面信息。', '爆点': '—'},
        'lines': [], 'displayId': unique_id, 'home': f'https://www.tiktok.com/@{unique_id}' if unique_id else '',
        'source': 'FastMoss',
    }


def detail_fields(raw, voc_rows, coverage, summary):
    if not raw:
        return {'detailAvailable': False, 'coverage': coverage}

    dimensions = {'when': '使用时机', 'who': '人群', 'where': '场景', 'what': '诉求'}
    groups = {}
    for prefix, label in dimensions.items():
        items = []
        for row in voc_rows:
            if row.get('画像维度', '').lower().startswith(prefix):
                items.append({
                    'name': row.get('标签') or '未提及',
                    'count': int(num(row.get('提及数')) or 0),
                    'negative': int(num(row.get('负向提及数')) or 0),
                })
        items.sort(key=lambda item: item['count'], reverse=True)
        groups[label] = items

    def names(items, limit=8):
        return [item['name'] for item in items[:limit] if item['name'] != '未提及']

    def audience(items):
        total = sum(item['count'] for item in items)
        return [{'n': item['name'], 'r': f"{item['count'] / total * 100:.2f}%" if total else '—', 'tgi': '—'} for item in items[:10]]

    audience_detail = [{'label': label, 'items': audience(groups[label])} for label in ['人群', '使用时机', '场景', '诉求'] if groups[label]]
    audience_line = '；'.join(filter(None, [
        '人群 ' + '、'.join(names(groups['人群'], 2)) if names(groups['人群'], 2) else '',
        '时机 ' + '、'.join(names(groups['使用时机'], 2)) if names(groups['使用时机'], 2) else '',
        '场景 ' + '、'.join(names(groups['场景'], 2)) if names(groups['场景'], 2) else '',
        '诉求 ' + '、'.join(names(groups['诉求'], 3)) if names(groups['诉求'], 3) else '',
    ])) or '消费者画像待补'

    good, bad = [], []
    for items in groups.values():
        for item in items:
            if item['name'] == '未提及':
                continue
            (bad if item['negative'] else good).append((item['negative'] or item['count'], item['name']))
    good = [item[1] for item in sorted(good, reverse=True)[:12]]
    bad = [item[1] for item in sorted(bad, reverse=True)[:12]]
    cats = {label: percent_items(items) for label, items in groups.items() if items}

    review = raw.get('review') or {}
    review_total = int(num(review.get('total')) or num(summary.get('评价数')) or 0)
    bad_rate = num(review.get('rate')) if review_total else None
    review_samples = []
    review_rows = review.get('list') or []
    positive = [item for item in review_rows if (num(item.get('rating')) or 0) >= 4][:6]
    negative = [item for item in review_rows if 0 < (num(item.get('rating')) or 0) <= 2][:6]
    if positive:
        review_samples.append({'kw': '正向评价原文', 'items': [{'t': item.get('text', ''), 'd': item.get('time', '')} for item in positive]})
    if negative:
        review_samples.append({'kw': '负向评价原文', 'items': [{'t': item.get('text', ''), 'd': item.get('time', '')} for item in negative]})

    author_rows = (raw.get('author') or {}).get('list') or []
    author_ids = {item.get('nickname', ''): item.get('unique_id', '') for item in author_rows}
    video_rows = (raw.get('video') or {}).get('list') or []
    videos = [video_row(item, author_ids) for item in video_rows[:10]]
    word_counts = Counter(tokens(' '.join(item.get('desc', '') for item in video_rows) + ' ' + raw.get('title', '')))
    cloud = [{'k': key, 'c': count} for key, count in word_counts.most_common(30)]
    video_groups = []
    for label, vocabulary in [
        ('卖点', {'growth', 'lash', 'lashes', 'hydrating', 'brightening', 'peptide', 'retinol', 'collagen', 'cleanser', 'mask'}),
        ('使用场景', {'morning', 'night', 'daily', 'week', 'month', 'routine', 'before', 'after'}),
        ('转化表达', {'buy', 'shop', 'link', 'deal', 'sale', 'discount', 'viral', 'recommend'}),
    ]:
        words = [{'k': key, 'c': word_counts[key]} for key in vocabulary if word_counts[key]]
        words.sort(key=lambda item: item['c'], reverse=True)
        if words:
            examples = [clean(item.get('desc', '')) for item in video_rows if any(word['k'] in clean(item.get('desc', '')).lower() for word in words[:3])][:2]
            video_groups.append({'name': label, 'nVid': len(examples), 'words': words[:8], 'egs': examples})
    if not video_groups and cloud:
        video_groups = [{'name': '视频原文高频表达', 'nVid': len(video_rows), 'words': cloud[:8], 'egs': [clean(item.get('desc', '')) for item in video_rows[:2]]}]

    total_gmv = sum(num(item.get('sale_amount')) or 0 for item in author_rows)
    bloggers = []
    for item in author_rows[:20]:
        followers = num(item.get('follower_count')) or 0
        level = '头部' if followers >= 100000 else ('腰部' if followers >= 10000 else '长尾')
        unique_id = item.get('unique_id') or ''
        bloggers.append({'n': item.get('nickname') or '—', 'lvl': level, 'fans': compact(followers), 'cert': 'TikTok Creator', 'gmv': compact(item.get('sale_amount'), 'USD'), 'vol': compact(item.get('sold_count')), 'aw': '—', 'lv': '—', 'lgmv': compact(item.get('sale_amount'), 'USD'), 'home': f'https://www.tiktok.com/@{unique_id}' if unique_id else ''})
    concentration = []
    for item in author_rows[:5]:
        gmv = num(item.get('sale_amount')) or 0
        concentration.append({'uid': item.get('unique_id', ''), 'name': item.get('nickname') or '—', 'gmv': compact(gmv, 'USD'), 'rate': f'{gmv / total_gmv * 100:.1f}%' if total_gmv else '—'})

    sku = raw.get('sku') or {}
    sku_names = []
    for item in (sku.get('list') or [])[:8]:
        sku_names.extend(name.get('prop_value') for name in item.get('name') or [] if name.get('prop_value'))
    core = {
        '内料形态': '—', '包装形式': '—', '功效': names(groups['诉求']), '主打成分': [], '香型/气味': [], '质地/肤感': [],
        '技术/工艺': [], '规格': sku_names[:8], '目标受众词': names(groups['人群']), '使用场景': names(groups['使用时机'], 4) + names(groups['场景'], 4),
        '用户痛点词': bad[:8], '外观/包装词': [], '美妆概念': [],
    }
    core_from = {key: ('FastMoss 消费者画像 VOC' if key in {'功效', '目标受众词', '使用场景', '用户痛点词'} else ('FastMoss SKU 明细' if key == '规格' else '该数据包未提供')) for key in core}
    rating = num(raw.get('rating'))
    overview = raw.get('overview') or {}
    distributions = raw.get('dist') or {}
    return {
        'detailAvailable': True, 'coverage': coverage, 'audienceDetail': audience_detail, 'audienceLine': audience_line,
        'goodWords': good, 'badWords': bad, 'words': cloud, 'cats': cats, 'core': core, 'coreFrom': core_from,
        'reviewsSample': review_samples, 'badRate': bad_rate, 'midRate': 0 if bad_rate is not None else None,
        'goodRate': 100 - bad_rate if bad_rate is not None else None, 'nReviews': review_total, 'viral': videos,
        'viralAll': int(num((raw.get('video') or {}).get('total')) or len(videos)), 'viralExcluded': 0,
        'videosTotal': int(num((raw.get('video') or {}).get('total')) or len(videos)),
        'vsummary': {'n': int(num((raw.get('video') or {}).get('total')) or len(videos)), 'cloud': cloud, 'groups': video_groups},
        'wordcloud': cloud, 'bloggers': bloggers, 'bloggersTotal': len(author_rows), 'conc': concentration, 'btypes': [],
        'channel': distribution(distributions.get('channel')), 'selltype': distribution(distributions.get('content')),
        'attr': 'FastMoss 美国站商品详情；原始接口数据已随数据包保存。',
        'sell': {'功能': '／'.join(names(groups['诉求'], 6)) or '—', '一句话卖点': clean(raw.get('title') or summary.get('商品名称')), '主打技术': '—', '主打成分': '—', '香味': '—', '背书': '—', '备案成分': '—'},
        'shelf': {'现行价（原币）': money_label(raw.get('floor_price') or summary.get('价格')), '佣金': raw.get('commission_rate') or summary.get('佣金率') or '—', '统计周期': summary.get('采集周期') or '—', '榜单来源': 'FastMoss 美国站美妆 Top20', '规格信号': '、'.join(sku_names[:4]) or '详情未提供', 'SKU 形态': str(sku.get('count') or '—') + ' 个 SKU', '货架定位': '美国站周榜商品', '上架时间': raw.get('launch_time') or summary.get('上市日期') or '—', '累计评价': str(review_total) if review_total else '—', '评分': str(rating) if rating is not None else '—'},
        'overview': {'sold_count': overview.get('sold_count'), 'sale_amount': overview.get('sale_amount'), 'author_count': overview.get('author_count'), 'aweme_count': overview.get('aweme_count'), 'live_count': overview.get('live_count')},
    }


with zipfile.ZipFile(ZIP_PATH) as z:
    summary_rows = read_csv(z, '03_汇总表_CSV/00_商品总表_80条.csv')
    voc_rows = read_csv(z, '03_汇总表_CSV/01_消费者画像_VOC.csv')
    coverage_rows = read_csv(z, '03_汇总表_CSV/10_数据覆盖情况.csv')
    review_rows = read_csv(z, '03_汇总表_CSV/08_商品评论.csv')
    voc_by = defaultdict(list)
    review_by = defaultdict(list)
    for row in voc_rows:
        voc_by[row.get('商品ID')].append(row)
    for row in review_rows:
        review_by[row.get('商品ID')].append(row)
    coverage_by = {row.get('商品ID'): row for row in coverage_rows}
    details = read_json(z, '04_汇总_JSON/商品详情包_含消费者画像.json', {})
    products = []
    for index, row in enumerate(summary_rows, 1):
        product_id = row.get('商品ID') or row.get('id')
        raw = details.get(product_id)
        leaf = row.get('三级类目') or row.get('品类') or '其他'
        l2 = {'眼部护理': '眼部护理', '洗面乳': '面部护理', '面膜': '面部护理', '面部精华液': '面部护理'}.get(leaf, '面部护理')
        cate = {'眼部护理': '眼部护理', '洗面乳': '洁面', '面膜': '面膜', '面部精华液': '面部精华'}.get(leaf, leaf)
        rank = rank_of(row.get('榜单排名')) or int(num(row.get('排位')) or index)
        price = num(row.get('价格')) or (num(raw.get('floor_price')) if raw else None)
        sales = num(row.get('销售额'))
        volume = num(row.get('销量'))
        video_count, live_count, author_count = num(row.get('视频数')), num(row.get('直播数')), num(row.get('关联达人数'))
        details_for_product = detail_fields(raw, voc_by[product_id], coverage_by.get(product_id, {}), row)
        brand = row.get('品牌') or row.get('店铺') or '未标品牌'
        shop = row.get('店铺') or brand
        title = clean(row.get('商品名称'))
        selling = details_for_product.get('sell', {}).get('一句话卖点') or title
        sortkey = {'sv': sales or 0, 'vol': volume or 0, 'vw': 0, 'cv': 0, 'vid': video_count or 0, 'tal': author_count or 0, 'pr': price or 0, 'cm': num(row.get('佣金率')) or (num(raw.get('commission_rate')) if raw else 0) or 0, 'bad': details_for_product.get('badRate') if details_for_product.get('badRate') is not None else 999}
        products.append({
            'i': 66 + index, 'gid': product_id, 'title': title, 'brand': brand, 'shop': shop, 'shopScore': str((raw or {}).get('rating') or row.get('评分') or '—'),
            'cate': cate, 'cateRaw': leaf, 'l1': '美妆个护', 'l2': l2, 'l3': leaf, 'rank': rank, 'rankAll': rank, 'rankNo': rank, 'rankPeriod': '周榜',
            'price': price, 'currency': 'USD', 'market': '美国', 'source': 'FastMoss', 'region': '美国', 'site': '美国站', 'rawL2': row.get('二级类目') or '美容护肤',
            'cover': (raw or {}).get('cover') or row.get('商品图') or '', 'link': (raw or {}).get('detail_url') or row.get('商品链接') or '', 'fg': '',
            'sales': compact(sales, 'USD') if sales is not None else '—', 'salesRaw': sales, 'volume': compact(volume), 'volumeRaw': volume, 'orders': '—', 'views': '—', 'conv': '—',
            'nV': str(int(video_count)) if video_count is not None else '—', 'nL': str(int(live_count)) if live_count is not None else '—', 'nT': str(int(author_count)) if author_count is not None else '—',
            'onSale': (raw or {}).get('launch_time') or row.get('上市日期') or '—', 'reviews': str(details_for_product.get('nReviews') or row.get('评价数') or '—'), 'praise': (str((raw or {}).get('rating')) + '/5') if (raw or {}).get('rating') is not None else '—', 'upd': '2026-09-28',
            'channel': details_for_product.get('channel') or [], 'selltype': details_for_product.get('selltype') or [], 'sellingPoint': selling, 'audienceLine': details_for_product.get('audienceLine') or '消费者画像待补', 'audienceDetail': details_for_product.get('audienceDetail') or [],
            'nReviews': details_for_product.get('nReviews'), 'badRate': details_for_product.get('badRate'), 'midRate': details_for_product.get('midRate'), 'goodRate': details_for_product.get('goodRate'), 'goodWords': details_for_product.get('goodWords') or [], 'badWords': details_for_product.get('badWords') or [], 'words': details_for_product.get('words') or [], 'cats': details_for_product.get('cats') or [],
            'core': details_for_product.get('core') or {'内料形态': '—', '包装形式': '—'}, 'coreFrom': details_for_product.get('coreFrom') or {}, 'shelf': details_for_product.get('shelf') or {}, 'sell': details_for_product.get('sell') or {'功能': '—', '一句话卖点': selling, '主打技术': '—', '主打成分': '—', '香味': '—', '背书': '—', '备案成分': '—'},
            'painPoints': details_for_product.get('badWords') or [], 'gift': '数据包未提供', 'factory': shop, 'goodCmt': [], 'badCmt': details_for_product.get('badWords') or [], 'attr': details_for_product.get('attr') or '—', 'reviewsSample': details_for_product.get('reviewsSample') or [],
            'viral': details_for_product.get('viral') or [], 'viralAll': details_for_product.get('viralAll') or 0, 'viralExcluded': details_for_product.get('viralExcluded') or 0, 'vsummary': details_for_product.get('vsummary') or {'n': 0, 'cloud': [], 'groups': []}, 'videosTotal': details_for_product.get('videosTotal') or 0,
            'bloggersTotal': details_for_product.get('bloggersTotal') or 0, 'bloggers': details_for_product.get('bloggers') or [], 'conc': details_for_product.get('conc') or [], 'btypes': details_for_product.get('btypes') or [], 'wordcloud': details_for_product.get('wordcloud') or [], 'sortkey': sortkey,
            'coverage': {'detailAvailable': bool(raw), 'hasVoc': bool(voc_by[product_id]), 'hasReviews': bool((raw or {}).get('review')), 'hasSku': bool((raw or {}).get('sku')), 'missing': coverage_by.get(product_id, {}).get('缺失接口', '—'), 'source': 'FastMoss', 'snapshot': '2026-09-28'}, 'detailAvailable': bool(raw),
        })

payload = {'meta': {'source': 'FastMoss', 'market': '美国', 'site': '美国站', 'period': '2026-39周', 'fetchedAt': '2026-09-28 20:14', 'count': 80, 'detailCount': len(details), 'vocCount': sum(1 for row in summary_rows if row.get('商品ID') in voc_by), 'categories': ['眼部护理', '洁面', '面膜', '面部精华'], 'note': '外部 FastMoss 数据包导入；榜单 80 条，详情覆盖按商品标注。'}, 'products': products}
OUT_PATH.write_text('/* FastMoss 美国站美妆 Top20 · 2026-09-28 外部数据包导入（榜单 80 条；详情覆盖按商品标注） */\nwindow.FASTMOSS_US_DATA=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
print(f'wrote {OUT_PATH} · products={len(products)} details={len(details)} bytes={OUT_PATH.stat().st_size}')
