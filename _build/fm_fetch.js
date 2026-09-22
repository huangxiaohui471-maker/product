/* FastMoss 新品榜抽取器：SageSurf CDP 53126 → data/fastmoss_*.json
   用法: node fm_fetch.js <startPage> <endPage> <outFile> [l1cid] */
const { chromium } = require('playwright');
const fs = require('fs');

const [, , sp, ep, outFile, l1cid] = process.argv;
const START = Number(sp || 1), END = Number(ep || 3);
const OUT = outFile || '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/data/fastmoss_new.json';
const CID = l1cid || '14';
const BASE = 'https://www.fastmoss.com/zh/e-commerce/newProducts';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function extract(page) {
  return page.evaluate(() => {
    const heads = [...document.querySelectorAll('thead th')].map(th => (th.innerText || '').trim());
    const rows = [...document.querySelectorAll('.ant-table-row, tbody tr')]
      .filter(r => !r.className.includes('measure-row'));
    return {
      heads,
      rows: rows.map(r => {
        const tds = [...r.querySelectorAll('td')];
        const cells = tds.map(td => (td.innerText || '').replace(/\s+/g, ' ').trim());
        const a = r.querySelector('a[href*="/e-commerce/detail/"]');
        const href = a ? a.getAttribute('href') : '';
        const m = href.match(/detail\/(\d+)/);
        return { cells, productId: m ? m[1] : '', href };
      }).filter(o => o.cells.some(c => c.length > 0))
    };
  });
}

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const pages = [];
  for (const c of browser.contexts()) for (const p of c.pages()) pages.push(p);
  const page = pages.find(p => p.url().includes('fastmoss.com'));
  if (!page) { console.log(JSON.stringify({ error: 'no fastmoss tab' })); await browser.close(); return; }

  const all = [];
  let heads = [];
  for (let n = START; n <= END; n++) {
    await page.goto(`${BASE}?page=${n}&l1_cid=${CID}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    let got = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      await sleep(2500);
      const d = await extract(page);
      if (d.rows.length) { got = d; break; }
      await sleep(1500);
    }
    if (!got) { console.log('page ' + n + ' -> no rows (gave up after 3 tries)'); continue; }
    heads = got.heads;
    got.rows.forEach(r => all.push({ page: n, ...r }));
    console.log('page ' + n + ' -> ' + got.rows.length + ' rows');
  }

  fs.mkdirSync(require('path').dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({
    source: 'FastMoss', listUrl: BASE, l1_cid: CID,
    fetchedAt: new Date().toISOString(), heads, count: all.length, rows: all
  }, null, 1), 'utf8');
  console.log('SAVED ' + OUT + ' rows=' + all.length);
  console.log('HEADS ' + JSON.stringify(heads));
  await browser.close();
})();
