const { chromium } = require('playwright');
const F = 'file:///Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/.page_tmp/index.html';
(async () => {
  const errs = [];
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 950 } });
  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  p.on('console', m => { if (m.type() === 'error' && !/inject\.js|Failed to load/.test(m.text())) errs.push('C:' + m.text()); });
  await p.goto(F);
  await p.waitForTimeout(2500);
  const r1 = await p.evaluate(() => {
    const chips = [...document.querySelectorAll('#chips button')].map(e => (e.innerText || '').trim());
    return { sync: (document.querySelector('#syncText') || {}).textContent,
             onlineBtn: !!document.querySelector('#btnOnline'),
             onlineShown: !!((document.querySelector('#btnOnline') || {}).offsetParent),
             chips: chips };
  });
  console.log('LOCAL-MODE ' + JSON.stringify(r1, null, 1));
  // 点「只看真实」
  const ok = await p.evaluate(() => {
    const btn = [...document.querySelectorAll('#chips button')].find(e => (e.innerText || '').trim() === '只看真实');
    if (btn) { btn.click(); return true; } return false;
  });
  await p.waitForTimeout(800);
  const r2 = await p.evaluate(() => {
    const on = [...document.querySelectorAll('#chips button')].filter(e => e.className.includes('on')).map(e => (e.innerText || '').trim());
    const demoOn = [...document.querySelectorAll('#chips button')].find(e => (e.innerText || '').trim() === '只看示例');
    return { realClicked: true, onChips: on, demoChipStillOn: demoOn ? demoOn.className.includes('on') : null,
             body: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 200) };
  });
  console.log('AFTER-CLICK ' + JSON.stringify(r2, null, 1));
  console.log('ERRORS ' + JSON.stringify(errs.slice(0, 5)));
  await b.close();
})();
