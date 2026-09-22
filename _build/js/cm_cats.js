(() => {
  const app = document.querySelector('#app');
  const root = app && app.__vue__;
  if (!root) return JSON.stringify({ ok: false });
  const hits = [];
  (function walk(c, d, path) {
    if (!c || d > 20 || hits.length > 12) return;
    const n = (c.$options && c.$options.name) || '';
    const p = path + '/' + (n || '?');
    let data = {};
    try { data = c._data || {}; } catch (e) { }
    for (const k of Object.keys(data)) {
      let v;
      try { v = data[k]; } catch (e) { continue; }
      if (Array.isArray(v) && v.length > 2 && v[0] && typeof v[0] === 'object') {
        const ks = Object.keys(v[0]);
        if (ks.some(x => /cid|category|category_id|cat_id|name/i.test(x)) && !ks.some(x => /rank|rank_change|amount/i.test(x))) {
          hits.push({ path: p, key: k, len: v.length, sample: JSON.stringify(v.slice(0, 6)).slice(0, 500) });
        }
      }
    }
    (c.$children || []).forEach(ch => walk(ch, d + 1, p));
  })(root, 0, '');
  return JSON.stringify({ ok: true, hits: hits.slice(0, 8) });
})()
