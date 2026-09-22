// 从 FastMoss 类目下拉面板读三级类目树
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const PORT = process.env.CDP_PORT || '65362';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:' + PORT);
  const ctx = b.contexts()[0];
  let page = ctx.pages().find((p) => /fastmoss\.com/.test(p.url()));
  if (!page) page = await ctx.newPage();
  await page.goto('https://www.fastmoss.com/zh/e-commerce/saleslist?page=1&l1_cid=14', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
  await sleep(9000);

  // 1) 先找页面内嵌 JSON
  const embedded = await page.evaluate(() => {
    const out = [];
    const nd = document.getElementById('__NEXT_DATA__');
    if (nd) out.push({ src: '__NEXT_DATA__', len: nd.textContent.length });
    document.querySelectorAll('script[type="application/json"]').forEach((s, i) => out.push({ src: 'json-script-' + i, len: s.textContent.length }));
    return out;
  });
  console.log('内嵌 JSON：' + JSON.stringify(embedded));

  // 2) 点开「商品分类」并 dump 面板
  await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('button,div,span'));
    const t = els.find((e) => (e.innerText || '').trim() === '商品分类');
    if (t) t.click();
  });
  await sleep(4000);
  const panel = await page.evaluate(() => {
    // 找含大量类目词的浮层
    const cands = Array.from(document.querySelectorAll('div'));
    let best = null;
    for (const d of cands) {
      const t = d.innerText || '';
      if (t.length > 200 && t.length < 20000 && /美妆个护/.test(t) && /个护|护肤|彩妆/.test(t)) {
        if (!best || t.length < best.length) best = t;
      }
    }
    return best;
  });
  fs.writeFileSync(path.join(__dirname, 'data', 'fm_cat_panel.txt'), panel || '', 'utf8');
  console.log('面板长度 ' + (panel ? panel.length : 0));
  console.log((panel || '').slice(0, 2500));
  await b.close().catch(() => {});
  process.exit(0);
})();
