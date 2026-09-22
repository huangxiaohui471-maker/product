(() => {
  const as = [...document.querySelectorAll('a[href]')];
  const out = [];
  const seen = new Set();
  for (const a of as) {
    const h = a.getAttribute('href') || '';
    const t = (a.innerText || '').replace(/\s+/g, ' ').trim();
    if (!h || h === '#' || h.startsWith('javascript')) continue;
    const key = h;
    if (seen.has(key)) continue;
    seen.add(key);
    if (/rank|Rank|goods|Goods|product|Product/i.test(h) || /榜|排行|商品库|选品/.test(t)) {
      out.push({ t: t.slice(0, 22), h: h.slice(0, 90) });
    }
  }
  return JSON.stringify({ url: location.href, links: out.slice(0, 45) });
})()
