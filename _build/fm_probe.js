/* FastMoss 新品榜结构探测（SageSurf CDP 53126） */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const pages = [];
  for (const c of browser.contexts()) for (const p of c.pages()) pages.push(p);
  const page = pages.find(p => p.url().includes('fastmoss.com'));
  if (!page) { console.log('NO_FM_TAB'); await browser.close(); return; }

  console.log('URL ' + page.url());
  console.log('TITLE ' + (await page.title()));

  const struct = await page.evaluate(() => {
    const out = {};
    out.tables = [...document.querySelectorAll('table')].map((t, i) => ({
      i,
      rows: t.querySelectorAll('tbody tr').length,
      head: [...t.querySelectorAll('thead th')].map(th => (th.innerText || '').trim()).slice(0, 20)
    }));
    out.elTable = document.querySelectorAll('.el-table').length;
    out.antTable = document.querySelectorAll('.ant-table').length;
    const firstRow = document.querySelector('tbody tr');
    out.firstRowCells = firstRow ? [...firstRow.querySelectorAll('td')].map(td => (td.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 40)) : null;
    out.bodyLen = (document.body.innerText || '').length;
    return out;
  });
  console.log('STRUCT ' + JSON.stringify(struct, null, 1));

  await browser.close();
})();
