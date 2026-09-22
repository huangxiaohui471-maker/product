// 从 FastMoss 列表页找商品详情链接格式
const { chromium } = require('playwright');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:54982');
  const ctx = b.contexts()[0];
  const p = await ctx.newPage();
  await p.goto('https://www.fastmoss.com/zh/e-commerce/saleslist?page=1&l1_cid=14', { waitUntil: 'domcontentloaded', timeout: 40000 });
  await sleep(6000);
  const out = await p.evaluate(() => {
    const links = [];
    document.querySelectorAll('a[href]').forEach((a) => {
      const h = a.getAttribute('href') || '';
      if (/product|goods|detail/i.test(h)) links.push(h);
    });
    const rows = document.querySelectorAll('.ant-table-row').length;
    return { links: Array.from(new Set(links)).slice(0, 12), rows };
  });
  console.log('rows', out.rows);
  console.log('商品链接样例:');
  out.links.forEach((x) => console.log('   ' + x));
  // 点击第一行商品名看跳哪
  try {
    const first = await p.$('.ant-table-row td:nth-child(2) a, .ant-table-row a');
    if (first) {
      await first.click();
      await sleep(4500);
      const info = await p.evaluate(() => {
        const t = document.body ? document.body.innerText.replace(/\s+/g, ' ') : '';
        return { url: location.href, title: document.title, hasReview: /评价|评论|review|评分|好评|差评/i.test(t), sample: t.slice(0, 300) };
      });
      console.log('点击后 ->', info.url.slice(0, 110));
      console.log('   title:', info.title.slice(0, 60), '| hasReview:', info.hasReview);
      console.log('   sample:', info.sample.slice(0, 260));
    } else { console.log('未找到可点击的商品链接'); }
  } catch (e) { console.log('click err', String(e).slice(0, 90)); }
  await p.close();
  await b.close();
})();
