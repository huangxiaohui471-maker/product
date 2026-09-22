(() => {
  const app = document.querySelector('#app');
  if (!app) return JSON.stringify({ ok: false, why: 'no #app' });
  const root = app.__vue__;
  if (!root) return JSON.stringify({ ok: false, why: 'no __vue__ on #app' });
  const comps = [];
  (function walk(c, d) {
    if (!c || d > 20 || comps.length > 60) return;
    const n = (c.$options && c.$options.name) || '';
    let keys = [];
    try { keys = Object.keys(c._data || {}); } catch (e) { }
    const big = keys.filter(k => {
      const v = c._data[k];
      return Array.isArray(v) && v.length > 5;
    });
    if (keys.length) comps.push({ name: n, depth: d, keys: keys.slice(0, 18), bigArrays: big });
    (c.$children || []).forEach(ch => walk(ch, d + 1));
  })(root, 0);
  return JSON.stringify({ ok: true, count: comps.length, comps: comps.slice(0, 40) });
})()
