/* 核实 CDP(9222) 里三个平台的登录态 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  const ctxs = browser.contexts();
  const pages = [];
  for (const c of ctxs) for (const p of c.pages()) pages.push(p);

  for (const p of pages) {
    let info = { url: '', title: '', probe: {} };
    try {
      info.url = p.url();
      info.title = await p.title();
      info.probe = await p.evaluate(() => {
        const t = (document.body ? document.body.innerText : '') || '';
        const has = (re) => re.test(t);
        return {
          len: t.length,
          loginWord: has(/登录|登入|Sign in|Log in/i),
          logoutWord: has(/退出|退出登录|Log\s*out|Sign\s*out|我的|个人中心/i),
          bodyHead: t.replace(/\s+/g, ' ').slice(0, 120)
        };
      });
    } catch (e) {
      info.err = e.message;
    }
    console.log(JSON.stringify(info));
  }
  await browser.close();
})();
