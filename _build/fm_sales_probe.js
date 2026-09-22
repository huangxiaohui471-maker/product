const { chromium } = require('playwright');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:53126');
  const ps=[]; for (const c of b.contexts()) for (const p of c.pages()) ps.push(p);
  const p = ps.find(x=>x.url().includes('fastmoss.com'));
  await p.goto('https://www.fastmoss.com/zh/e-commerce/saleslist', {waitUntil:'domcontentloaded',timeout:60000});
  await sleep(6000);
  const r = await p.evaluate(() => {
    const heads=[...document.querySelectorAll('thead th')].map(t=>(t.innerText||'').replace(/\s+/g,' ').trim());
    const rows=[...document.querySelectorAll('.ant-table-row')].slice(0,3).map(tr=>
      [...tr.querySelectorAll('td')].map(td=>(td.innerText||'').replace(/\s+/g,' ').trim().slice(0,70)));
    return {url:location.href, heads, rows, bodyLen:(document.body.innerText||'').length};
  });
  console.log(JSON.stringify(r,null,1));
  await b.close();
})();
