(() => {
  const app = document.querySelector('#app');
  const root = app && app.__vue__;
  if (!root) return JSON.stringify({ ok: false });
  let target = null;
  (function walk(c, d) {
    if (!c || d > 20 || target) return;
    const n = (c.$options && c.$options.name) || '';
    if (n === 'volume-product-rank' && c._data && Array.isArray(c._data.dataList)) target = c;
    (c.$children || []).forEach(ch => walk(ch, d + 1));
  })(root, 0);
  if (!target) return JSON.stringify({ ok: false, why: 'component not found' });
  const one = target._data.dataList[0] || {};
  const out = {};
  for (const k of Object.keys(one)) {
    let v = one[k];
    if (Array.isArray(v)) v = '[array len=' + v.length + ']';
    else if (v && typeof v === 'object') v = JSON.stringify(v).slice(0, 120);
    out[k] = (v === null || v === undefined) ? null : String(v).slice(0, 120);
  }
  return JSON.stringify({ ok: true, total: target._data.dataList.length, item0: out });
})()
