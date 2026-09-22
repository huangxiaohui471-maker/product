const { chromium } = require('playwright');
const dir = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47';
const F = 'file://' + encodeURIComponent(dir + '/全球选品平台.html').replace(/%2F/g, '/');
(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('C:' + m.text()); });
  await page.goto(F);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForTimeout(1000);

  for (const v of ['board', 'rank', 'lib', 'insight']) {
    await page.click(`#nav .nav-item[data-view="${v}"]`);
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${dir}/_build/shot_${v}.png`, fullPage: true });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.click('#tabbar button[data-view="board"]');
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${dir}/_build/shot_mobile.png`, fullPage: false });
  await page.setViewportSize({ width: 1440, height: 1000 });

  /* 完全空表 */
  const empty = await page.evaluate(() => {
    state.list = []; state.market = '全部'; state.cat = '全部'; state.kw = '';
    const out = {};
    ['board', 'rank', 'lib', 'insight'].forEach(v => {
      state.view = v; refreshAll();
      const el = document.querySelector('#view');
      out[v] = { text: el.textContent.trim().slice(0, 46), cards: el.querySelectorAll('.card').length };
    });
    return out;
  });
  console.log('EMPTY ' + JSON.stringify(empty, null, 1));

  /* 打开导入弹窗后的空表再确认一次 */
  const afterImportOpen = await page.evaluate(() => {
    state.view = 'board'; refreshAll();
    document.querySelector('#btnImport').click();
    const m = document.querySelector('#modal');
    const r = { modalOn: m.classList.contains('on'), hasTextarea: !!m.querySelector('#impText'), hasParse: !!m.querySelector('#impParse') };
    document.querySelector('#modal [data-close]').click();
    return r;
  });
  console.log('MODAL ' + JSON.stringify(afterImportOpen, null, 1));

  console.log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
