const { chromium } = require('playwright');
const path = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/全球选品平台.html';
const F = 'file://' + encodeURIComponent(path).replace(/%2F/g, '/');
const OUT = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/';
const log = (...a) => console.log(...a);

(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('C:' + m.text()); });
  page.on('dialog', d => d.accept());

  await page.goto(F);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForTimeout(1300);

  // 1) 看板：数据通路体检 + 覆盖度
  await page.screenshot({ path: OUT + 'shot_a_board.png', fullPage: false });
  const flowBox = await page.$('#view .sec:nth-of-type(2)');
  if (flowBox) await flowBox.screenshot({ path: OUT + 'shot_a_flow.png' });
  const covEl = await page.$('#view .cov-wrap');
  if (covEl) await covEl.screenshot({ path: OUT + 'shot_a_cov.png' });

  // 2) 机会洞察：引擎体检 + 字段缺口告警
  await page.click('#nav .nav-item[data-view="insight"]');
  await page.waitForTimeout(600);
  await page.screenshot({ path: OUT + 'shot_b_insight.png', fullPage: false });

  // 3) 空态诊断：复现截图场景
  await page.click('#nav .nav-item[data-view="board"]');
  await page.waitForTimeout(300);
  await page.click('#chips .chip[data-f="market"][data-v="东南亚"]');
  await page.waitForTimeout(250);
  await page.click('#chips .chip[data-f="cat"][data-v="护肤"]');
  await page.waitForTimeout(250);
  await page.fill('#kw', '沐浴油');
  await page.waitForTimeout(800);
  await page.screenshot({ path: OUT + 'shot_c_diag.png', fullPage: false });

  // 点「改搜沐浴」验证动作有效
  const fix = await page.$('#view .mini[data-f="kw"]');
  if (fix) { await fix.click(); await page.waitForTimeout(800); }
  const fixed = await page.evaluate(() => ({
    desc: document.querySelector('#viewDesc').textContent,
    cards: document.querySelectorAll('#view .card').length,
    diag: !!document.querySelector('#view .diag')
  }));
  log('SUGGEST-ACTION ' + JSON.stringify(fixed));
  await page.screenshot({ path: OUT + 'shot_d_after_suggest.png', fullPage: false });

  // 4) 导入第 1 步 / 第 2 步
  await page.evaluate(() => { state.cat = '全部'; state.kw = ''; });
  await page.click('#btnImport');
  await page.waitForTimeout(500);
  await page.screenshot({ path: OUT + 'shot_e_import1.png', fullPage: false });
  await page.click('#modal .src-card[data-imp-src="FastMoss"]');
  await page.waitForTimeout(250);
  await page.click('#impNext');
  await page.waitForTimeout(500);
  await page.screenshot({ path: OUT + 'shot_f_import2.png', fullPage: false });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // 5) 数据源地图
  await page.click('.side-map');
  await page.waitForTimeout(500);
  await page.screenshot({ path: OUT + 'shot_g_srcmap.png', fullPage: false });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // 6) 移动端
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: OUT + 'shot_h_mobile.png', fullPage: false });
  await page.click('.tabbar button[data-view="insight"]');
  await page.waitForTimeout(600);
  await page.screenshot({ path: OUT + 'shot_h_mobile_ins.png', fullPage: false });

  log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
