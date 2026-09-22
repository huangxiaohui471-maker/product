/* 检查 Chrome 9222 上 fastmoss / chanmama / compass 的登录态 */
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
  const ps = [];
  for (const c of b.contexts()) for (const p of c.pages()) ps.push(p);
  const out = [];
  for (const p of ps) {
    const u = p.url();
    if (!/fastmoss|chanmama|jinritemai|compass/.test(u)) continue;
    let info = {};
    try {
      info = await p.evaluate(() => {
        const t = (document.body ? document.body.innerText : '').slice(0, 600);
        const rows = document.querySelectorAll('.ant-table-row, tr.aurora-table-row').length;
        return { hasLoginWord: /登录\/注册|注册\/登录|请登录|登录后查看|立即登录/.test(t), rows: rows, head: (document.title || '').slice(0, 40) };
      });
    } catch (e) { info = { err: String(e).slice(0, 60) }; }
    out.push({ url: u.slice(0, 90), ...info });
  }
  console.log(JSON.stringify(out, null, 1));
  await b.close();
})();
