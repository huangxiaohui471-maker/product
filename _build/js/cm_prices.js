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
  const rows = t._data.dataList.slice(0, 3).map(o => {
    const o2 = {};
    ['title', 'shop_name', 'market_price', 'amount', 'coupon_price', 'sku_union_price',
      'sku_union_price_text', 'trade_price', 'trade_price_text', 'day_amount', 'day_order_count_text_cmm_ind',
      'first_crawl_time', 'month_conversion_rate_text', 'update_time', 'platform', 'promotion_id']
      .forEach(k => { o2[k] = (o[k] && typeof o[k] === 'object') ? JSON.stringify(o[k]).slice(0, 80) : o[k]; });
    return o2;
  });
  return JSON.stringify({ ok: true, rows: rows });
})()
