(function () {
  var row = document.querySelector('.ant-table-row');
  if (!row) return JSON.stringify({ err: 'no row' });
  var fk = Object.keys(row).find(function (x) { return x.indexOf('__reactFiber') === 0; });
  if (!fk) return JSON.stringify({ err: 'no fiber' });
  var f = row[fk], found = null, d = 0;
  while (f && d < 80 && !found) {
    var mp = f.memoizedProps;
    if (mp && typeof mp === 'object') {
      var ks = Object.keys(mp);
      for (var i = 0; i < ks.length; i++) {
        var v = mp[ks[i]];
        if (Object.prototype.toString.call(v) === '[object Array]' && v.length > 3 && v[0] && typeof v[0] === 'object' && ('product_id' in v[0] || 'sold_count' in v[0])) { found = v; break; }
      }
    }
    f = f.return; d++;
  }
  if (!found) return JSON.stringify({ err: 'no data array' });
  var s = found[0];
  var pick = {};
  ['product_id', 'title', 'region', 'currency', 'real_price', 'commission_rate', 'all_category_name',
    'category_name', 'sold_count', 'sold_count_inc_rate', 'sale_amount', 'total_sold_count',
    'total_sale_amount', 'aweme_count', 'live_count', 'author_count', 'total_author_count',
    'launch_time', 'off_shelves', 'detail_url'].forEach(function (k) { pick[k] = s[k]; });
  pick.shop_name = (s.shop_info && s.shop_info.name) || '';
  return JSON.stringify({ ok: true, len: found.length, depth: d, pick: pick });
})()
