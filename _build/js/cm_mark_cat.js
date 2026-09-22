(() => {
  const all = [...document.querySelectorAll('*')];
  const cand = all.filter(e => {
    const t = (e.innerText || '').trim();
    return t === '美妆护肤' && e.children.length <= 1;
  });
  if (!cand.length) return JSON.stringify({ ok: false, why: 'chip not found' });
  const el = cand[cand.length - 1];
  const chain = [];
  let t = el;
  for (let i = 0; i < 5 && t; i++) {
    const cs = getComputedStyle(t);
    chain.push({ tag: t.tagName, cls: String(t.className || '').slice(0, 70), cursor: cs.cursor });
    t = t.parentElement;
  }
  let clickable = el, hops = 0;
  let p = el;
  while (p && hops < 5) {
    const cs = getComputedStyle(p);
    if (cs.cursor === 'pointer') { clickable = p; break; }
    p = p.parentElement; hops++;
  }
  clickable.setAttribute('data-wbtmp', 'cat');
  return JSON.stringify({ ok: true, chain: chain, picked: { tag: clickable.tagName, cls: String(clickable.className || '').slice(0, 70) } });
})()
