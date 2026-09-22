// 拦截 FastMoss 类目树接口（SageSurf CDP）
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

  const hits = [];
  page.on('response', async (res) => {
    const u = res.url();
    if (!/categor|category|cat_|goodsCat/i.test(u)) return;
    if (hits.some((h) => h.url === u)) return;
    let body = null;
    try { body = await res.text(); } catch (e) { body = null; }
    hits.push({ url: u, status: res.status(), len: body ? body.length : 0, body: body ? body.slice(0, 400000) : null });
    console.log('[HIT] ' + res.status() + ' ' + u.slice(0, 150));
  });

  await page.goto('https://www.fastmoss.com/zh/e-commerce/saleslist?page=1&l1_cid=14', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch((e) => console.log('goto err ' + String(e).slice(0, 80)));
  await sleep(9000);

  // 尝试点开类目筛选
  try {
    const opened = await page.evaluate(() => {
      const els = Array.from(document.querySelectorAll('button,div,span,a'));
      const t = els.find((e) => /全部分类|类目|分类/.test((e.innerText || '').trim()) && (e.innerText || '').trim().length <= 8);
      if (t) { t.click(); return (t.innerText || '').trim(); }
      return null;
    });
    console.log('点开筛选：' + opened);
    await sleep(5000);
  } catch (e) { console.log('click err ' + String(e).slice(0, 80)); }

  fs.writeFileSync(path.join(__dirname, 'data', 'fm_cat_probe.json'), JSON.stringify(hits, null, 1), 'utf8');
  console.log('命中 ' + hits.length + ' 个类目接口');
  hits.forEach((h) => console.log('  ' + h.status + ' ' + h.len + 'B  ' + h.url.slice(0, 140)));
  await b.close().catch(() => {});
  process.exit(0);
})();
