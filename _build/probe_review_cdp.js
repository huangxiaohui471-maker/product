// 在 SageSurf(54982) 上探测评价渠道登录态
const { chromium } = require('playwright');
const CAND = [
  ['xiaohongshu', 'https://www.xiaohongshu.com/search_result?keyword=' + encodeURIComponent('防晒霜')],
  ['douyin_shop', 'https://www.douyin.com/'],
  ['taobao', 'https://www.taobao.com/'],
  ['tmall', 'https://www.tmall.com/'],
  ['tiktok', 'https://www.tiktok.com/'],
];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:54982');
  const ctx = b.contexts()[0];
  const out = {};
  for (const [name, url] of CAND) {
    let p;
    try {
      p = await ctx.newPage();
      await p.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await sleep(4000);
      const info = await p.evaluate(() => {
        const t = document.body ? document.body.innerText.replace(/\s+/g, ' ').slice(0, 1200) : '';
        return {
          url: location.href,
          title: document.title,
          needLogin: /登录|注册|扫码|登陆|Sign in|Log in|请先登录/.test(t),
          hasUserCenter: /创作中心|个人中心|我的主页|退出|账户|我的|profile|avatar/i.test(document.body ? document.body.innerHTML.slice(0, 60000) : ''),
          sample: t.slice(0, 300),
        };
      });
      out[name] = info;
      console.log('== ' + name + ' ==');
      console.log('   url:', info.url.slice(0, 90));
      console.log('   needLogin:', info.needLogin, '| title:', (info.title || '').slice(0, 40));
      console.log('   sample:', info.sample.slice(0, 220));
      await p.close();
    } catch (e) {
      console.log('== ' + name + ' == ERR ' + String(e).slice(0, 120));
      try { if (p) await p.close(); } catch (_) {}
    }
  }
  require('fs').writeFileSync(__dirname + '/data/review_probe.json', JSON.stringify(out, null, 1), 'utf8');
  await b.close();
})();
