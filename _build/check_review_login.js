// 探测各评价源在 SageSurf 浏览器里的登录态（只看信号，不做写入）
// 用法: node check_review_login.js [cdpPort]
const { chromium } = require('playwright');
const PORT = process.argv[2] || '65362';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const SITES = [
  { name: 'FastMoss', url: 'https://www.fastmoss.com/zh/e-commerce/detail/1729412750691563818', probe: `(function(){
      var t=document.body?document.body.innerText:'';
      return JSON.stringify({login:/退出|个人中心|我的收藏/.test(t), needLogin:/登录|注册/.test(t)&&!/退出/.test(t), len:t.length});
    })()` },
  { name: '抖音电商罗盘', url: 'https://compass.jinritemai.com/shop', probe: `(function(){
      var t=document.body?document.body.innerText:'';
      return JSON.stringify({login:/罗盘|概览|实时|店铺/.test(t), url:location.href, len:t.length});
    })()` },
  { name: '蝉妈妈', url: 'https://www.chanmama.com/', probe: `(function(){
      var t=document.body?document.body.innerText:'';
      return JSON.stringify({login:!/登录|注册/.test(t), user:/会员|退出/.test(t), len:t.length});
    })()` },
  { name: '小红书', url: 'https://www.xiaohongshu.com/explore', probe: `(function(){
      var t=document.body?document.body.innerText:'';
      return JSON.stringify({login:/发布|创作中心|我/.test(t)&&!/扫码登录/.test(t), needLogin:/扫码登录|登录/.test(t), len:t.length});
    })()` },
  { name: '淘宝/天猫', url: 'https://www.taobao.com/', probe: `(function(){
      var t=document.body?document.body.innerText:'';
      return JSON.stringify({login:/我的淘宝|退出|千牛/.test(t), needLogin:/请登录|亲，请登录/.test(t), nick:(document.querySelector('.site-nav-user')||{}).innerText||'', len:t.length});
    })()` },
  { name: 'TikTok Shop', url: 'https://www.tiktok.com/', probe: `(function(){
      var t=document.body?document.body.innerText:'';
      return JSON.stringify({login:/Profile|Upload|Log out/.test(t), needLogin:/Log in|Sign up/.test(t), len:t.length});
    })()` },
];

(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:' + PORT);
  const ctx = b.contexts()[0];
  for (const s of SITES) {
    const p = await ctx.newPage();
    try {
      await p.goto(s.url, { waitUntil: 'domcontentloaded', timeout: 25000 });
      await sleep(3500);
      const raw = await p.evaluate(s.probe);
      console.log(s.name + ' :: ' + (typeof raw === 'string' ? raw : JSON.stringify(raw)));
    } catch (e) {
      console.log(s.name + ' :: ERR ' + String(e).slice(0, 90));
    }
    await p.close();
  }
  await b.close();
})();
