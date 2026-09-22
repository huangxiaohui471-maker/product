// 探测 FastMoss 商品详情页是否含评价数据
const { chromium } = require('playwright');
const fs = require('fs');
const PID = process.argv[2] || '1736482358295496010';
const CANDS = [
  'https://www.fastmoss.com/zh/e-commerce/product/' + PID,
  'https://www.fastmoss.com/zh/e-commerce/productDetail?id=' + PID,
  'https://www.fastmoss.com/zh/product/' + PID,
];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:54982');
  const ctx = b.contexts()[0];
  const p = await ctx.newPage();
  for (const url of CANDS) {
    try {
      await p.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await sleep(4000);
      const info = await p.evaluate(() => {
        const t = document.body ? document.body.innerText.replace(/\s+/g, ' ') : '';
        return {
          url: location.href, title: document.title,
          hasReview: /评价|评论|review|评分|好评|差评/i.test(t),
          sample: t.slice(0, 400),
        };
      });
      console.log('== ' + url);
      console.log('   -> ' + info.url.slice(0, 100));
      console.log('   title: ' + info.title.slice(0, 60) + ' | hasReview: ' + info.hasReview);
      console.log('   sample: ' + info.sample.slice(0, 300));
    } catch (e) {
      console.log('== ' + url + ' ERR ' + String(e).slice(0, 90));
    }
  }
  await p.close();
  await b.close();
})();
