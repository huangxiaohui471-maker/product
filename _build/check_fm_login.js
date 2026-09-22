// 检查指定 CDP 端口上 FastMoss 的登录态
const { chromium } = require('playwright');
const PORT = process.argv[2] || '9222';
(async () => {
  try {
    const b = await chromium.connectOverCDP('http://127.0.0.1:' + PORT);
    for (const ctx of b.contexts()) {
      for (const p of ctx.pages()) {
        const u = p.url();
        if (!/fastmoss|chanmama|jinritemai|xiaohongshu|tmall|taobao/.test(u)) continue;
        let info;
        try {
          info = await p.evaluate(() => {
            const t = document.body ? document.body.innerText.slice(0, 500) : '';
            return {
              hasLoginWord: /登录\/注册|立即登录|Log in|Sign in/.test(t),
              rows: document.querySelectorAll('.ant-table-row').length,
              nick: (document.querySelector('[class*=userName],[class*=nickname],[class*=avatar]') || {}).innerText || ''
            };
          });
        } catch (e) { info = { err: String(e).slice(0, 80) }; }
        console.log(PORT + ' | ' + u.slice(0, 78) + ' | ' + JSON.stringify(info));
      }
    }
    await b.close();
  } catch (e) {
    console.log(PORT + ' CONNECT_FAIL ' + String(e).slice(0, 120));
  }
})();
