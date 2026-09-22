// 通过 SageSurf CDP(54982) 取 FastMoss 登录态全字段（React fiber）
// 用法: node fm_cdp_fetch.js <sales|new> <startPage> <endPage> [l1_cid]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const PORT = process.env.CDP_PORT || '54982';
const KIND = process.argv[2] || 'sales';
const START = parseInt(process.argv[3] || '1', 10);
const END = parseInt(process.argv[4] || '4', 10);
const CID = process.argv[5] || '14';

const SUB = KIND === 'new' ? 'newProducts' : 'saleslist';
const EXTRACT = fs.readFileSync(path.join(__dirname, 'js', 'fm_fiber_rows.js'), 'utf8');
const OUT = path.join(__dirname, 'data', `fastmoss_${KIND}_fiber.json`);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:' + PORT);
  const ctx = b.contexts()[0];
  let page = ctx.pages().find((p) => /fastmoss\.com/.test(p.url()));
  if (!page) page = await ctx.newPage();

  const rows = [];
  for (let n = START; n <= END; n++) {
    const url = `https://www.fastmoss.com/zh/e-commerce/${SUB}?page=${n}&l1_cid=${CID}`;
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    } catch (e) {
      console.log('page ' + n + ' goto err ' + String(e).slice(0, 60));
      continue;
    }
    let got = null;
    for (let k = 0; k < 6; k++) {
      await sleep(2500);
      try {
        const raw = await page.evaluate(EXTRACT);
        const o = typeof raw === 'string' ? JSON.parse(raw) : raw;
        if (o && o.ok && o.rows && o.rows.length) { got = o.rows; break; }
      } catch (e) { /* retry */ }
    }
    if (!got) { console.log('page ' + n + ' -> 空'); continue; }
    got.forEach((r) => { r.page = n; });
    rows.push(...got);
    console.log('page ' + n + ' -> ' + got.length + ' 行');
  }

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({
    source: 'FastMoss', kind: KIND, l1_cid: CID, channel: 'SageSurf-CDP-' + PORT,
    fetchedAt: new Date().toISOString(), count: rows.length, rows
  }, null, 1), 'utf8');

  const wa = rows.filter((r) => r.author_count != null).length;
  const ids = new Set(rows.map((r) => r.product_id));
  console.log(`SAVED ${OUT} | 共 ${rows.length} 条 | 唯一 ${ids.size} | 含达人数 ${wa}`);
  const cats = {};
  rows.forEach((r) => {
    const k = (r.all_category_name || [])[0] || '(空)';
    cats[k] = (cats[k] || 0) + 1;
  });
  console.log('一级类目:', JSON.stringify(cats, null, 0));
  const regions = {};
  rows.forEach((r) => { regions[r.region] = (regions[r.region] || 0) + 1; });
  console.log('国家分布:', JSON.stringify(regions));
  await b.close();
})();
