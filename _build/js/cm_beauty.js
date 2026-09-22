(() => {
  const app = document.querySelector('#app');
  const root = app && app.__vue__;
  if (!root) return JSON.stringify({ ok: false });
  let t = null;
  (function walk(c, d) {
    if (!c || d > 20 || t) return;
    const n = (c.$options && c.$options.name) || '';
    if (n === 'volume-product-rank' && c._data && Array.isArray(c._data.dataList)) t = c;
    (c.$children || []).forEach(ch => walk(ch, d + 1));
  })(root, 0);
  if (!t) return JSON.stringify({ ok: false, why: 'not found' });

  const first = t._data.dataList[0] || {};
  const trendSample = JSON.stringify(first.day30_volume_trend || []).slice(0, 400);

  const rows = t._data.dataList.map(o => {
    let last7 = null, prev7 = null;
    const tr = o.day30_volume_trend;
    if (Array.isArray(tr) && tr.length) {
      const nums = tr.map(x => {
        if (typeof x === 'number') return x;
        if (x && typeof x === 'object') {
          const c1 = x.volume !== undefined ? x.volume : (x.value !== undefined ? x.value : (x.count !== undefined ? x.count : (x.order_count !== undefined ? x.order_count : null)));
          return Number(c1) || 0;
        }
        return Number(x) || 0;
      });
      if (nums.length >= 14) {
        last7 = Math.round(nums.slice(-7).reduce((a, b) => a + b, 0));
        prev7 = Math.round(nums.slice(-14, -7).reduce((a, b) => a + b, 0));
      }
    }
    return {
      rank: o.rank,
      rank_change: o.rank_change,
      title: o.title,
      shop: o.shop_name,
      day_order_text: o.day_order_count_text,
      day_order_exact: o.day_order_count_text_cmm_ind,
      year_order_exact: o.history_total_volume_text_cmm_ind,
      amount_text: o.amount_text,
      amount_exact: o.day_amount,
      conv: o.month_conversion_rate_text,
      url: o.product_short_url,
      first_crawl_time: o.first_crawl_time,
      last7: last7,
      prev7: prev7
    };
  });

  const idOf = (u) => {
    const m = String(u || '').match(/[?&]id=(\d+)/);
    return m ? m[1] : '';
  };
  rows.forEach(r => { r.product_id = idOf(r.url); });

  const filters = {};
  for (const k of ['multi_category_id', 'catShowValue', 'page', 'size', 'totalCount', 'rankType']) {
    try { filters[k] = String(t._data[k]); } catch (e) { }
  }
  return JSON.stringify({ ok: true, count: rows.length, filters: filters, trend_sample: trendSample, rows: rows });
})()
