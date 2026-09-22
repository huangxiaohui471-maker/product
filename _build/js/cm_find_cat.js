(() => {
  const app = document.querySelector('#app');
  const root = app && app.__vue__;
  if (!root) return JSON.stringify({ ok: false });
  const hits = [];
  (function walk(c, d, path) {
    if (!c || d > 22 || hits.length > 10) return;
    const n = (c.$options && c.$options.name) || '';
    const p = path + '/' + (n || '?');
    let data = {};
    try { data = c._data || {}; } catch (e) { }
    for (const k of Object.keys(data)) {
      let v;
      try { v = data[k]; } catch (e) { continue; }
      if (v == null) continue;
      let s = '';
      try { s = typeof v === 'string' ? v : JSON.stringify(v); } catch (e) { continue; }
      if (!s || s.length > 60000) continue;
      if (s.indexOf('美妆') >= 0 || s.indexOf('护肤') >= 0) {
        const i = Math.max(0, s.indexOf('美妆') >= 0 ? s.indexOf('美妆') - 120 : s.indexOf('护肤') - 120);
        hits.push({ path: p, key: k, len: s.length, slice: s.slice(i, i + 400) });
      }
    }
    (c.$children || []).forEach(ch => walk(ch, d + 1, p));
  })(root, 0, '');
  return JSON.stringify({ ok: true, n: hits.length, hits: hits.slice(0, 8) });
})()
