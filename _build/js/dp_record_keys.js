(function () {
  var row = document.querySelector('tr.aurora-table-row');
  if (!row) return JSON.stringify({ ok: false });
  var fk = Object.keys(row).find(function (x) { return x.indexOf('__reactFiber') === 0; });
  var f = row[fk], rec = null, d = 0;
  while (f && d < 90 && !rec) {
    var mp = f.memoizedProps;
    if (mp && typeof mp === 'object') {
      var ks = Object.keys(mp);
      for (var i = 0; i < ks.length; i++) { var v = mp[ks[i]]; if (v && typeof v === 'object' && v.record && v.record.product_info) { rec = v.record; break; } }
    }
    f = f.return; d++;
  }
  if (!rec) return JSON.stringify({ ok: false, err: 'no record' });
  var info = rec.product_info || {};
  return JSON.stringify({
    ok: true,
    recordKeys: Object.keys(rec),
    infoKeys: Object.keys(info),
    info: {
      id: info.id, name: info.name, price_bin: info.price_bin, rank: info.rank,
      leaf_category_id: info.leaf_category_id, newly_on_ranking: info.newly_on_ranking,
      brand_type: info.brand_type
    },
    shopListKeys: (info.shop_list && info.shop_list[0]) ? Object.keys(info.shop_list[0]) : [],
    shopCount: (info.shop_list || []).length,
    authorInfoKeys: (info.shop_list && info.shop_list[0] && info.shop_list[0].author_info) ? Object.keys(info.shop_list[0].author_info) : []
  });
})()
