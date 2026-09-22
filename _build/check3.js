const { chromium } = require('playwright-core');
const F = 'file:///Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/%E7%BE%8E%E5%A6%86%E6%83%85%E6%8A%A5%E5%8F%B0.html';
(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 940 } });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  await page.goto(F); await page.waitForTimeout(500);
  await page.evaluate(() => localStorage.clear());
  await page.reload(); await page.waitForTimeout(800);

  // 新建 -> 保存 -> 刷新找回
  await page.click('#btnNew'); await page.waitForTimeout(300);
  await page.fill('[data-f="标题"]', '交互验收测试条目');
  await page.click('[data-of="情报类型"][data-opt="竞品动态"]');
  await page.fill('[data-f="拆解笔记"]', '这是一条验收写入的记录');
  await page.waitForTimeout(400);
  await page.click('#formSave'); await page.waitForTimeout(700);
  await page.reload(); await page.waitForTimeout(900);
  const titles = await page.evaluate(() => Array.from(document.querySelectorAll('#intelBody .card-title')).map(e => e.textContent));
  const tagOk = await page.evaluate(() => Array.from(document.querySelectorAll('#intelBody .card')).some(c => c.textContent.includes('竞品动态')));
  console.log('SAVE-RELOAD ' + JSON.stringify({ titles, found: titles.includes('交互验收测试条目'), tagOk }));

  // 逾期顺延
  const before = await page.evaluate(() => Array.from(document.querySelectorAll('#todayList .today-row')).map(e => e.querySelector('.today-meta').textContent.trim()));
  await page.click('#todayList [data-act="postpone"]'); await page.waitForTimeout(900);
  const after = await page.evaluate(() => Array.from(document.querySelectorAll('#todayList .today-meta')).map(e => e.textContent.trim()));
  console.log('OVERDUE-BEFORE ' + JSON.stringify(before));
  console.log('OVERDUE-AFTER  ' + JSON.stringify(after));

  // 看板推进状态
  await page.click('.nav-item[data-go="content"]'); await page.waitForTimeout(350);
  const mv = await page.$('[data-move="content"]');
  if (mv) { await mv.click(); await page.waitForTimeout(800); }
  const cols = await page.evaluate(() => Array.from(document.querySelectorAll('#contentBody .col')).map(c => c.querySelector('.col-head').textContent.trim()));
  console.log('BOARD ' + JSON.stringify(cols));

  // 删除一条
  await page.click('.nav-item[data-go="intel"]'); await page.waitForTimeout(300);
  page.once('dialog', d => d.accept());
  const delBtn = await page.$('#intelBody .card [data-del]');
  await delBtn.click(); await page.waitForTimeout(800);
  const nAfterDel = await page.evaluate(() => document.querySelectorAll('#intelBody .card').length);
  console.log('DELETE n=' + nAfterDel);

  // 清空示例
  await page.click('#btnSettings'); await page.waitForTimeout(300);
  await page.click('#btnClearDemo'); await page.waitForTimeout(1600);
  const left = await page.evaluate(() => ({
    intel: document.querySelectorAll('#intelBody .card').length,
    empty: !!document.querySelector('#intelBody .empty')
  }));
  console.log('CLEAR-DEMO ' + JSON.stringify(left));
  await page.click('#setClose'); await page.waitForTimeout(300);

  // 移动端尺寸
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: '_build/shot_mobile.png', fullPage: true });
  const mob = await page.evaluate(() => {
    const g = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().height) : 0; };
    return { tabH: g('.tab'), newBtn: g('#btnNew'), iconBtn: g('.icon-btn'), tabbar: getComputedStyle(document.querySelector('.tabbar')).display };
  });
  console.log('MOBILE ' + JSON.stringify(mob));

  await page.setViewportSize({ width: 1440, height: 940 });
  await page.evaluate(() => localStorage.clear());
  await page.reload(); await page.waitForTimeout(800);
  await page.screenshot({ path: '_build/shot_pc.png', fullPage: true });
  for (const k of ['content','review','source']) {
    await page.click(`.nav-item[data-go="${k}"]`); await page.waitForTimeout(400);
    await page.screenshot({ path: `_build/shot_${k}.png`, fullPage: true });
  }
  console.log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
