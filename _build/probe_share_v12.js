/* 探测：未登录（全新浏览器上下文）打开公开链接时，页面能否拿到云端数据 */
const { chromium } = require('playwright');

const STABLE = 'https://workbuddy.link/p/lMO9EIAM8o5cIwqudwUDr1';
const ARTIFACT = 'https://workbuddy-space-static.codebuddy.work/page/lMO9EIAM8o5cIwqudwUDr1/12/index.html';

(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const b = await chromium.launch(proxy ? { proxy } : {});

  // ---- A) 公开稳定链接（全新上下文 = 未登录访客）----
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(String(e).slice(0, 160)));
  const frames = [];
  try {
    const r = await p.goto(STABLE, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await p.waitForTimeout(8000);
    const info = await p.evaluate(() => ({
      url: location.href,
      title: document.title,
      hasSmartPage: !!window.__SMART_PAGE__,
      hasDb: !!(window.__SMART_PAGE__ && window.__SMART_PAGE__.database),
      textLen: (document.body.innerText || '').length,
      head: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 300),
      iframes: Array.from(document.querySelectorAll('iframe')).map(f => f.src).slice(0, 5),
      loginHint: /登录|login|扫码/.test((document.body.innerText || ''))
    }));
    console.log('=== A) 稳定公开链接 / 未登录 ===');
    console.log('  HTTP', r && r.status());
    console.log('  ', JSON.stringify(info, null, 2).replace(/\n/g, '\n  '));
    for (const f of p.frames()) {
      if (f === p.mainFrame()) continue;
      frames.push(f.url());
      try {
        const fi = await f.evaluate(() => ({
          url: location.href,
          hasSmartPage: !!window.__SMART_PAGE__,
          hasDb: !!(window.__SMART_PAGE__ && window.__SMART_PAGE__.database),
          ONLINE: (typeof ONLINE !== 'undefined') ? ONLINE : null,
          rows: (typeof state !== 'undefined' && state.list) ? state.list.length : null,
          textLen: (document.body.innerText || '').length
        }));
        console.log('  [iframe]', JSON.stringify(fi));
      } catch (e) { console.log('  [iframe] 跨域不可读:', f.slice(0, 90)); }
    }
  } catch (e) {
    console.log('=== A) 失败:', String(e).slice(0, 200));
  }
  console.log('  JS错误', errs.length, errs.slice(0, 3));

  // ---- B) 直接打开发布产物（静态域，无平台壳）----
  const p2 = await ctx.newPage();
  const errs2 = [];
  p2.on('pageerror', e => errs2.push(String(e).slice(0, 160)));
  await p2.route('**/page_comm/inject.js', r => r.abort());
  try {
    await p2.goto(ARTIFACT, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await p2.waitForTimeout(4000);
    const info2 = await p2.evaluate(() => ({
      hasSmartPage: !!window.__SMART_PAGE__,
      ONLINE: (typeof ONLINE !== 'undefined') ? ONLINE : null,
      rows: (typeof state !== 'undefined' && state.list) ? state.list.length : null,
      bodyLen: (document.body.innerText || '').length
    }));
    console.log('=== B) 静态产物直开（无平台注入）===');
    console.log('  ', JSON.stringify(info2));
  } catch (e) { console.log('=== B) 失败:', String(e).slice(0, 160)); }
  console.log('  JS错误', errs2.length, errs2.slice(0, 3));

  await b.close();
})();
