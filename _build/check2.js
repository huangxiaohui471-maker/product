const { chromium } = require('playwright-core');
const F = 'file:///Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/%E7%BE%8E%E5%A6%86%E6%83%85%E6%8A%A5%E5%8F%B0.html';
(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 940 } });
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  await page.goto(F); await page.waitForTimeout(700);

  // 1) 各栏目截图
  for (const k of ['content','review','source']) {
    await page.click(`.nav-item[data-go="${k}"]`);
    await page.waitForTimeout(400);
    await page.screenshot({ path: `_build/shot_${k}.png`, fullPage: true });
    const n = await page.evaluate(k => ({
      board: document.querySelectorAll('#contentBody .col').length,
      kpi: document.querySelectorAll('#reviewBody .kpi').length,
      bars: document.querySelectorAll('#reviewBody .bar-row').length,
      rows: document.querySelectorAll('#sourceBody .row').length,
      bind: document.querySelectorAll('[data-sp-bindable="database"]').length
    }), k);
    console.log('VIEW ' + k + ' ' + JSON.stringify(n));
  }

  // 2) 新建一条情报 -> 保存 -> 刷新 -> 找回
  await page.click('.nav-item[data-go="intel"]'); await page.waitForTimeout(300);
  await page.click('#btnNew'); await page.waitForTimeout(350);
  await page.fill('[data-f="标题"]', '交互验收测试条目');
  await page.click('[data-of="情报类型"][data-opt="竞品动态"]');
  await page.click('[data-of="来源平台"][data-opt="抖音"]');
  await page.fill('[data-f="拆解笔记"]', '这是一条验收写入的记录');
  await page.waitForTimeout(500);
  await page.click('#formSave'); await page.waitForTimeout(700);
  const afterSave = await page.evaluate(() => document.querySelectorAll('#intelBody .card').length);
  await page.reload(); await page.waitForTimeout(900);
  const afterReload = await page.evaluate(() => {
    const t = Array.from(document.querySelectorAll('#intelBody .card-title')).map(e => e.textContent);
    return { n: t.length, found: t.includes('交互验收测试条目'), titles: t };
  });
  console.log('SAVE ' + JSON.stringify({ afterSave, afterReload }));

  // 3) 逾期一键处理（顺延到今天）
  await page.click('#todayList [data-act="postpone"]'); await page.waitForTimeout(800);
  const afterPostpone = await page.evaluate(() => {
    const r = Array.from(document.querySelectorAll('#todayList .today-row'))
      .map(e => e.querySelector('.today-meta').textContent.trim());
    return r;
  });
  console.log('POSTPONE ' + JSON.stringify(afterPostpone));

  // 4) 移动端
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: '_build/shot_mobile.png', fullPage: true });
  const mob = await page.evaluate(() => {
    const tb = getComputedStyle(document.querySelector('.tabbar')).display;
    const sb = getComputedStyle(document.querySelector('.sidebar')).display;
    const card = document.querySelector('.card');
    const btn = document.querySelector('#todayList .btn');
    return { tabbar: tb, sidebar: sb, cardW: card ? Math.round(card.getBoundingClientRect().width) : 0,
             btnH: btn ? Math.round(btn.getBoundingClientRect().height) : 0 };
  });
  console.log('MOBILE ' + JSON.stringify(mob));
  console.log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
