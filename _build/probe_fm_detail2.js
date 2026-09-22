// 抓 FastMoss 商品详情页，找评价/评论数据（含页面接口）
const { chromium } = require('playwright');
const fs = require('fs');
const PID = process.argv[2] || '1736482358295496010';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:54982');
  const ctx = b.contexts()[0];
  const p = await ctx.newPage();
  const apis = [];
  p.on('response', (r) => {
    const u = r.url();
    if (/\/(api|v1|v2)\//.test(u) && !/\.(png|jpg|css|js|woff)/.test(u)) apis.push(u.slice(0, 150));
  });
  await p.goto('https://www.fastmoss.com/zh/e-commerce/detail/' + PID, { waitUntil: 'domcontentloaded', timeout: 40000 });
  await sleep(8000);
  const info = await p.evaluate(() => {
    const t = document.body ? document.body.innerText.replace(/\s+/g, ' ') : '';
    const tabs = Array.from(document.querySelectorAll('[role=tab],[class*=tab]')).map((e) => (e.innerText || '').trim()).filter(Boolean).slice(0, 25);
    // 找页面上的 tab / 区块标题
    const kw = ['评价', '评论', '评分', '好评', '差评', '口碑'];
    const hits = kw.filter((k) => t.includes(k));
    const around = {};
    kw.forEach((k) => {
      const i = t.indexOf(k);
      if (i >= 0) around[k] = t.slice(Math.max(0, i - 80), i + 140);
    });
    return { title: document.title, len: t.length, tabs, hits, around, head: t.slice(0, 700) };
  });
  console.log('title:', info.title.slice(0, 70));
  console.log('文本长度:', info.len);
  console.log('命中关键词:', info.hits);
  console.log('tabs:', JSON.stringify(info.tabs));
  Object.keys(info.around).forEach((k) => console.log('  [' + k + '] ' + info.around[k]));
  console.log('--- 页面开头 ---');
  console.log(info.head.slice(0, 600));
  console.log('--- 相关接口 ---');
  Array.from(new Set(apis)).slice(0, 25).forEach((x) => console.log('   ' + x));
  await p.close();
  await b.close();
})();
