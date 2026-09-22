(() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href]')) {
    const h = a.getAttribute('href') || '';
    const t = (a.innerText || '').replace(/\s+/g, ' ').trim();
    if (!h || h === '#') continue;
    if (seen.has(h)) continue;
    seen.add(h);
    if (/market|compet|industry|rank|goods|product|trend|cate/i.test(h)) out.push({ t: t.slice(0, 20), h: h.slice(0, 100) });
  }
  return JSON.stringify({
    url: location.href,
    title: document.title,
    links: out.slice(0, 35),
    navText: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 300)
  });
})()
