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

  const scale = {
    day_order_count_text: 'day_order_count_text',
    order_exact: 'day_order_count_text_cmm_ind',
    year_exact: 'history_total_volume_text_cmm_ind',
    amount_exact: 'day_amount',
    amount_text: 'amount_text'
  };
  const rows = t._data.dataList.map(o => {
    const tr = Array.isArray(o.day30_volume_trend) ? o.day30_volume_trend.map(x => Number(x) || 0) : [];
    const last7 = tr.slice(-7).reduce((a, b) => a + b, 0);
    const prev7 = tr.slice(-14, -7).reduce((a, b) => a + b, 0);
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
      amount_cmm_ind: o.amount_text_cmm_ind,
      conv: o.month_conversion_rate_text,
      url: o.product_short_url,
      first_crawl_time: o.first_crawl_time,
      update_time: o.update_time,
      trend_len: tr.length,
      last7: Math.round(last7),
      prev7: Math.round(prev7)
    };
  });
  const filters = {};
  for (const k of Object.keys(t._data)) {
    const v = t._data[k];
    if (Array.isArray(v) || (v && typeof v === 'object')) continue;
    filters[k] = String(v).slice(0, 40);
  }
  return JSON.stringify({ ok: true, count: rows.length, filters: filters, rows: rows });
})()
