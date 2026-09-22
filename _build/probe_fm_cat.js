// 一次性探两件事：
//  1) FastMoss 榜单接口原始响应里的类目结构（拿 cid 链，让三级类目可复现取数）
//  2) FastMoss 商品详情接口有哪些字段（看有没有成分表）
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

  const saved = [];
  const urls = [];
  page.on('response', async (res) => {
    const u = res.url();
    if (/\.(js|css|png|jpg|jpeg|svg|woff2?|gif|webp)(\?|$)/i.test(u)) return;
    urls.push(res.status() + '  ' + u);
    try {
      const ct = res.headers()['content-type'] || '';
      if (!/json/i.test(ct)) return;
      const t = await res.text();
      if (t.length < 300) return;
      if (!/api\//i.test(u)) return;
      saved.push({ url: u, len: t.length, body: t.slice(0, 200000) });
    } catch (e) { /* ignore */ }
  });

  await page.goto('https://www.fastmoss.com/zh/e-commerce/saleslist?page=1&l1_cid=14', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
  await sleep(13000);

  console.log('=== 非静态请求 ' + urls.length + ' 条（前 50）===');
  urls.slice(0, 50).forEach((u) => console.log('  ' + u.slice(0, 150)));
  console.log('\n=== JSON 响应 ' + saved.length + ' 条 ===');
  saved.forEach((s) => console.log('  ' + String(s.len).padStart(7) + 'B  ' + s.url.slice(0, 140)));

  // 2) 探详情接口
  const detail = await page.evaluate(async () => {
    const id = '1736482358295496010';
    const paths = [
      '/api/goods/v3/baseInfo?product_id=' + id,
      '/api/goods/v3/base?product_id=' + id,
      '/api/goods/v3/detail?product_id=' + id,
      '/api/goods/v2/detail?product_id=' + id,
      '/api/product/detail?product_id=' + id,
    ];
    const out = {};
    for (const p of paths) {
      try {
        const r = await fetch(p, { credentials: 'include' });
        const j = await r.json();
        const d = j.data || {};
        out[p] = { code: j.code, msg: j.msg || j.message, keys: Object.keys(d), preview: JSON.stringify(d).slice(0, 700) };
      } catch (e) { out[p] = { err: String(e).slice(0, 100) }; }
    }
    return out;
  });

  fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });
  fs.writeFileSync(path.join(__dirname, 'data', 'fm_api_probe2.json'), JSON.stringify({ saved, detail, urls }, null, 1), 'utf8');
  console.log('\n=== 详情接口探测 ===');
  console.log(JSON.stringify(detail, null, 1).slice(0, 3500));

  await b.close().catch(() => {});
  process.exit(0);
})();
