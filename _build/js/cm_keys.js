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
  const first = t._data.dataList[0] || {};
  const keys = Object.keys(first);
  // 挑出疑似「达人 / 作者 / 直播 / 视频 / 退货」相关字段
  const suspect = {};
  for (const k of keys) {
    if (/author|aweme|live|video|daren|creator|influencer|refund|return|rate|count|num/i.test(k)) {
      const v = first[k];
      suspect[k] = (v && typeof v === 'object') ? '[obj]' + JSON.stringify(v).slice(0, 120) : v;
    }
  }
  return JSON.stringify({ ok: true, keyCount: keys.length, keys: keys, suspect: suspect });
})()
