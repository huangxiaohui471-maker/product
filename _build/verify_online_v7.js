// 用 SageSurf（CDP）打开线上 v7 页面，验证「口碑诊断」读到第二张云表
const { chromium } = require('playwright');
const { execSync } = require('child_process');
const path = require('path');

function findPort() {
  let out = '';
  try { out = execSync('lsof -nP -iTCP -sTCP:LISTEN | grep -i sagesurf', { encoding: 'utf8' }); } catch (e) {}
  const ports = [...new Set((out.match(/:(\d{4,5})\s+\(LISTEN\)/g) || []).map((s) => s.match(/:(\d+)/)[1]))];
  return ports;
}

(async () => {
  let port = null;
  for (const p of findPort()) {
    try {
      const r = await fetch('http://127.0.0.1:' + p + '/json/version');
      if (r.ok) { port = p; break; }
    } catch (e) {}
  }
  if (!port) { console.log('未找到 SageSurf CDP'); process.exit(1); }
  console.log('CDP ' + port);
  const b = await chromium.connectOverCDP('http://127.0.0.1:' + port);
  const ctx = b.contexts()[0];
  const p = await ctx.newPage();
  await p.goto('https://www.workbuddy.cn/space/d/lMO9EIAM8o5cIwqudwUDr1', { waitUntil: 'load', timeout: 60000 });
  await p.waitForTimeout(15000);
  const res = await p.evaluate(() => {
    const ONLINE = !!(window.__SMART_PAGE__ && window.__SMART_PAGE__.database);
    const navs = Array.from(document.querySelectorAll('#nav [data-view]')).map((x) => x.getAttribute('data-view'));
    const sync = (document.querySelector('#syncText') || {}).textContent;
    return { url: location.href.slice(0, 70), ONLINE, navs, sync, title: document.title.slice(0, 40) };
  });
  console.log(JSON.stringify(res, null, 1));

  // 点口碑诊断
  const click = await p.evaluate(() => {
    const btn = document.querySelector('#nav [data-view="review"]');
    if (!btn) return false;
    btn.click(); return true;
  });
  await p.waitForTimeout(3000);
  const res2 = await p.evaluate(() => {
    const v = document.querySelector('#view');
    return {
      title: (document.querySelector('#viewTitle') || {}).textContent,
      desc: (document.querySelector('#viewDesc') || {}).textContent,
      head: v ? v.innerText.slice(0, 420) : '(空)',
      ids: Array.from(document.querySelectorAll('[data-sp-database-id]')).map((x) => x.getAttribute('data-sp-database-id')),
    };
  });
  console.log(JSON.stringify(res2, null, 1));
  await p.screenshot({ path: path.join(__dirname, 'data', 'online_review.png') });
  await p.close();
  process.exit(0);
})();
