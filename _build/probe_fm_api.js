// 测试 FastMoss baseInfo / base 接口能否带登录态直接取（含评分与评价数）
const { chromium } = require('playwright');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:54982');
  const ctx = b.contexts()[0];
  const pages = ctx.pages();
  let p = pages.find((x) => /fastmoss\.com/.test(x.url()));
  if (!p) p = await ctx.newPage();
  if (!/fastmoss\.com/.test(p.url())) {
    await p.goto('https://www.fastmoss.com/zh/e-commerce/saleslist?page=1&l1_cid=14', { waitUntil: 'domcontentloaded', timeout: 40000 });
    await sleep(5000);
  }
  const out = await p.evaluate(async () => {
    const ids = ['1736482358295496010', '1735304940106318937'];
    const res = {};
    for (const id of ids) {
      try {
        const r1 = await fetch('/api/goods/v3/baseInfo?product_id=' + id, { credentials: 'include' });
        const j1 = await r1.json();
        const r2 = await fetch('/api/goods/v3/base?product_id=' + id, { credentials: 'include' });
        const j2 = await r2.json();
        res[id] = {
          baseInfoCode: j1.code, baseInfoKeys: Object.keys(j1.data || {}),
          baseCode: j2.code, baseKeys: Object.keys(j2.data || {}),
          raw1: JSON.stringify(j1.data || {}).slice(0, 500),
          raw2: JSON.stringify(j2.data || {}).slice(0, 500),
        };
      } catch (e) { res[id] = { err: String(e).slice(0, 120) }; }
    }
    return res;
  });
  console.log(JSON.stringify(out, null, 1).slice(0, 3000));
  await b.close();
})();
