/* 从 FastMoss React fiber 挖出当前页完整原始记录数组（确认 author_count 等字段） */
const { chromium } = require('playwright');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const ps = [];
  for (const c of b.contexts()) for (const p of c.pages()) ps.push(p);
  const p = ps.find(x => x.url().includes('fastmoss.com'));
  if (!p) { console.log(JSON.stringify({ err: 'no fastmoss tab', urls: ps.map(x => x.url()).slice(0, 20) })); await b.close(); return; }
  console.log('URL ' + p.url());
  const r = await p.evaluate(() => {
    const row = document.querySelector('.ant-table-row');
    if (!row) return { err: 'no row' };
    const fk = Object.keys(row).find(x => x.startsWith('__reactFiber'));
    let f = row[fk], best = null, d = 0;
    while (f && d < 80) {
      const mp = f.memoizedProps;
      if (mp && typeof mp === 'object') {
        for (const kk of Object.keys(mp)) {
          const v = mp[kk];
          if (Array.isArray(v) && v.length > 3 && v[0] && typeof v[0] === 'object' && ('product_id' in v[0] || 'sold_count' in v[0] || 'title' in v[0])) {
            best = { depth: d, key: kk, len: v.length, fields: Object.keys(v[0]), sample: v[0] };
          }
        }
      }
      if (best) break;
      f = f.return; d++;
    }
    if (!best) return { err: 'no data array on fiber' };
    const s = best.sample;
    const picked = {};
    ['product_id','title','region','currency','real_price','commission_rate','all_category_name','category_name',
     'sold_count','sold_count_inc_rate','sale_amount','total_sold_count','total_sale_amount',
     'aweme_count','live_count','author_count','total_author_count','launch_time','shop_info','off_shelves','detail_url']
      .forEach(k => { picked[k] = s[k]; });
    return { depth: best.depth, key: best.key, len: best.len, fields: best.fields, picked: picked };
  });
  console.log(JSON.stringify(r, null, 1).slice(0, 4000));
  await b.close();
})();
