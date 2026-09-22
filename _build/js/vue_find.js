(() => {
  const app = document.querySelector('#app');
  const root = app && app.__vue__;
  if (!root) return JSON.stringify({ ok: false });
  const hits = [];
  (function walk(c, d, path) {
    if (!c || d > 20 || hits.length > 30) return;
    const n = (c.$options && c.$options.name) || '';
    const p = path + '/' + (n || '?');
    let data = {};
    try { data = c._data || {}; } catch (e) { }
    for (const k of Object.keys(data)) {
      let v;
      try { v = data[k]; } catch (e) { continue; }
      if (Array.isArray(v) && v.length > 3 && v[0] && typeof v[0] === 'object') {
        const ks = Object.keys(v[0]).slice(0, 32);
        const score = ks.filter(x => /sale|Sale|销量|销售额|price|title|goods|product|rank|Rank|inc|Inc|rate|Rate|name/.test(x)).length;
        if (score >= 2) hits.push({ path: p, key: k, len: v.length, keys: ks, score });
      }
    }
    (c.$children || []).forEach(ch => walk(ch, d + 1, p));
  })(root, 0, '');
  return JSON.stringify({ ok: true, n: hits.length, hits: hits.slice(0, 18) });
})()
