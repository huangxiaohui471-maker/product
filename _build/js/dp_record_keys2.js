(function () {
  var row = document.querySelector('tr.aurora-table-row');
  if (!row) return JSON.stringify({ ok: false, err: 'no row' });
  var fk = Object.keys(row).find(function (x) { return x.indexOf('__reactFiber') === 0; });
  var root0 = row[fk];
  var found = null, seen = 0;
  function scan(f, d) {
    if (!f || d > 40 || found || seen > 4000) return;
    seen++;
    var mp = f.memoizedProps;
    if (mp && typeof mp === 'object') {
      for (var k in mp) {
        var v = mp[k];
        if (v && typeof v === 'object') {
          if (v.product_info || (v.record && v.record.product_info)) { found = v.product_info ? v : v.record; return; }
        }
      }
    }
    scan(f.child, d + 1);
    scan(f.sibling, d);
    scan(f.return && null, d);
  }
  // 从 row 向上找几层，再向下扫
  var up = root0, dd = 0;
  while (up && dd < 25 && !found) { scan(up, 0); up = up.return; dd++; }
  if (!found) return JSON.stringify({ ok: false, err: 'not found', seen: seen });
  var info = found.product_info || {};
  var sh = (info.shop_list || [])[0] || {};
  return JSON.stringify({
    ok: true, seen: seen,
    recordKeys: Object.keys(found),
    infoKeys: Object.keys(info),
    price_bin: info.price_bin, id: info.id, rank: info.rank,
    newly_on_ranking: info.newly_on_ranking,
    shopListLen: (info.shop_list || []).length,
    shopKeys: Object.keys(sh),
    authorKeys: sh.author_info ? Object.keys(sh.author_info) : [],
    author: sh.author_info ? { nick: sh.author_info.author_nick_name, fans: sh.author_info.fans_count } : null
  });
})()
