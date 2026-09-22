/* FastMoss 全字段抽取器（走 React fiber，拿到表格上看不到的字段）
   用法: node fm_fiber_fetch.js <sales|new> <startPage> <endPage> [l1cid] */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const KIND = process.argv[2] || 'sales';
const START = Number(process.argv[3] || 1);
const END = Number(process.argv[4] || 4);
const CID = process.argv[5] || '14';
const BASE = KIND === 'new'
  ? 'https://www.fastmoss.com/zh/e-commerce/newProducts'
  : 'https://www.fastmoss.com/zh/e-commerce/saleslist';
const OUT = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/data/fastmoss_' + KIND + '_fiber.json';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const KEEP = ['product_id', 'title', 'region', 'region_name', 'currency', 'real_price', 'commission_rate',
  'all_category_name', 'category_name', 'sold_count', 'sold_count_inc_rate', 'sale_amount',
  'total_sold_count', 'total_sale_amount', 'aweme_count', 'live_count', 'author_count',
  'total_author_count', 'launch_time', 'off_shelves', 'detail_url'];

function extractor() {
  const row = document.querySelector('.ant-table-row');
  if (!row) return null;
  const fk = Object.keys(row).find(x => x.startsWith('__reactFiber'));
  if (!fk) return null;
  let f = row[fk], found = null, d = 0;
  while (f && d < 80 && !found) {
    const mp = f.memoizedProps;
    if (mp && typeof mp === 'object') {
      for (const k of Object.keys(mp)) {
        const v = mp[k];
        if (Array.isArray(v) && v.length > 3 && v[0] && typeof v[0] === 'object' &&
            ('product_id' in v[0] || 'sold_count' in v[0])) { found = v; break; }
      }
    }
    f = f.return; d++;
  }
  if (!found) return null;
  return found.map(o => {
    const o2 = {};
    for (const k of ['product_id', 'title', 'region', 'region_name', 'currency', 'real_price', 'commission_rate',
      'all_category_name', 'category_name', 'sold_count', 'sold_count_inc_rate', 'sale_amount',
      'total_sold_count', 'total_sale_amount', 'aweme_count', 'live_count', 'author_count',
      'total_author_count', 'launch_time', 'off_shelves', 'detail_url']) {
      o2[k] = o[k] === undefined ? null : o[k];
    }
    o2.shop_name = (o.shop_info && o.shop_info.name) || '';
    return o2;
  });
}

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const ps = [];
  for (const c of browser.contexts()) for (const p of c.pages()) ps.push(p);
  const page = ps.find(p => p.url().includes('fastmoss.com'));
  if (!page) { console.log('NO_TAB'); await browser.close(); return; }

  const all = [];
  for (let n = START; n <= END; n++) {
    await page.goto(`${BASE}?page=${n}&l1_cid=${CID}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    let got = null;
    for (let k = 0; k < 4; k++) {
      await sleep(2500);
      got = await page.evaluate(extractor);
      if (got && got.length) break;
    }
    if (!got || !got.length) { console.log('page ' + n + ' empty'); continue; }
    got.forEach(r => all.push({ page: n, ...r }));
    console.log('page ' + n + ' -> ' + got.length);
  }
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({
    source: 'FastMoss', kind: KIND, listUrl: BASE, l1_cid: CID,
    fetchedAt: new Date().toISOString(), count: all.length, rows: all
  }, null, 1), 'utf8');
  const withAuthor = all.filter(r => r.author_count !== null).length;
  console.log('SAVED ' + OUT + ' n=' + all.length + ' 有作者数=' + withAuthor);
  await browser.close();
})();
