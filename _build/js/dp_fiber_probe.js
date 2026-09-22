(function () {
  var row = document.querySelector('tr.aurora-table-row') || document.querySelector('tr');
  if (!row) return JSON.stringify({ ok: false, err: 'no row' });
  var fk = Object.keys(row).find(function (x) { return x.indexOf('__reactFiber') === 0; });
  var out = { ok: true, url: location.href, hasFiber: !!fk, rowCls: String(row.className).slice(0, 60) };
  out.cells = [].slice.call(row.querySelectorAll('td')).map(function (c) { return (c.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 50); });
  if (!fk) return JSON.stringify(out);
  var f = row[fk], d = 0, hits = [];
  while (f && d < 90) {
    var mp = f.memoizedProps;
    if (mp && typeof mp === 'object') {
      var ks = Object.keys(mp);
      for (var i = 0; i < ks.length; i++) {
        var v = mp[ks[i]];
        if (Object.prototype.toString.call(v) === '[object Array]' && v.length > 2 && v[0] && typeof v[0] === 'object') {
          hits.push({ d: d, key: ks[i], len: v.length, fields: Object.keys(v[0]).slice(0, 40), sample: JSON.parse(JSON.stringify(v[0])) });
        }
      }
    }
    if (hits.length) break;
    f = f.return; d++;
  }
  out.hits = hits.slice(0, 2);
  return JSON.stringify(out);
})()
