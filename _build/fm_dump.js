/* FastMoss 行内容探测 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const pages = [];
  for (const c of browser.contexts()) for (const p of c.pages()) pages.push(p);
  const page = pages.find(p => p.url().includes('fastmoss.com'));

  const info = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.ant-table-row, tbody tr')];
    const dump = rows.slice(0, 3).map(r => ({
      cls: r.className,
      text: (r.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 300),
      html: (r.outerHTML || '').replace(/\s+/g, ' ').slice(0, 900)
    }));
    return { count: rows.length, dump };
  });
  console.log(JSON.stringify(info, null, 1));
  await browser.close();
})();
