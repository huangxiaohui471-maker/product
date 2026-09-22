/* FastMoss 销量榜（含销量环比）抽取 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const START = Number(process.argv[2] || 1);
const END = Number(process.argv[3] || 4);
const CID = process.argv[4] || '14';
const OUT = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/data/fastmoss_sales.json';
const BASE = 'https://www.fastmoss.com/zh/e-commerce/saleslist';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const ps = [];
  for (const c of browser.contexts()) for (const p of c.pages()) ps.push(p);
  const page = ps.find(p => p.url().includes('fastmoss.com'));

  const all = [];
  let heads = [];
  for (let n = START; n <= END; n++) {
    await page.goto(`${BASE}?page=${n}&l1_cid=${CID}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    let got = null;
    for (let k = 0; k < 3; k++) {
      await sleep(3000);
      got = await page.evaluate(() => {
        const h = [...document.querySelectorAll('thead th')].map(t => (t.innerText || '').replace(/\s+/g, ' ').trim());
        const rows = [...document.querySelectorAll('.ant-table-row')].map(tr => {
          const tds = [...tr.querySelectorAll('td')];
          const a = tr.querySelector('a[href*="/e-commerce/detail/"]');
          const href = a ? a.getAttribute('href') : '';
          const m = href.match(/detail\/(\d+)/);
          return { cells: tds.map(td => (td.innerText || '').replace(/\s+/g, ' ').trim()), productId: m ? m[1] : '' };
        });
        return { h, rows };
      });
      if (got && got.rows.length) break;
    }
    if (!got || !got.rows.length) { console.log('page ' + n + ' empty'); continue; }
    heads = got.h;
    got.rows.forEach(r => all.push({ page: n, ...r }));
    console.log('page ' + n + ' -> ' + got.rows.length);
  }
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({
    source: 'FastMoss', list: '销量榜', listUrl: BASE, l1_cid: CID,
    fetchedAt: new Date().toISOString(), heads, count: all.length, rows: all
  }, null, 1), 'utf8');
  console.log('SAVED ' + OUT + ' n=' + all.length);
  console.log('HEADS ' + JSON.stringify(heads));
  await browser.close();
})();
