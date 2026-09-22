const { chromium } = require('playwright');
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const ps=[]; for (const c of b.contexts()) for (const p of c.pages()) ps.push(p);
  const p = ps.find(x=>x.url().includes('fastmoss.com'));
  const r = await p.evaluate(() => {
    const out=[]; const seen=new Set();
    for (const a of document.querySelectorAll('a[href]')) {
      const h=a.getAttribute('href')||''; const t=(a.innerText||'').replace(/\s+/g,' ').trim();
      if(!h||h==='#'||seen.has(h))continue; seen.add(h);
      if(/e-commerce|rank|product|Product|hot/i.test(h) && t) out.push({t:t.slice(0,18),h:h.slice(0,70)});
    }
    return out.slice(0,30);
  });
  console.log(JSON.stringify(r,null,1));
  await b.close();
})();
