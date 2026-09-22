const { chromium } = require('playwright-core');
const F = 'file:///Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/%E5%85%A8%E7%90%83%E6%96%B0%E5%93%81%E9%80%89%E5%93%81%E5%8F%B0.html';
(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 940 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('C:' + m.text()); });
  await page.goto(F); await page.waitForTimeout(400);
  await page.evaluate(() => localStorage.clear());
  await page.reload(); await page.waitForTimeout(900);

  const base = await page.evaluate(() => ({
    nav: document.querySelectorAll('#nav .nav-item').length,
    tabs: document.querySelectorAll('#tabbar .tab').length,
    cards: document.querySelectorAll('#productBody .card').length,
    scores: Array.from(document.querySelectorAll('#productBody .score-pill b')).map(e => e.textContent),
    lvs: Array.from(document.querySelectorAll('#productBody .card .tag')).filter(t => ['打样评估', '候选池', '留档'].includes(t.textContent)).map(t => t.textContent),
    today: document.querySelectorAll('#todayList .today-row').length,
    todayMeta: Array.from(document.querySelectorAll('#todayList .today-meta')).map(e => e.textContent.trim()),
    banner: !document.querySelector('#offBanner').classList.contains('hide')
  }));
  console.log('BASE ' + JSON.stringify(base, null, 1));

  await page.click('.nav-item[data-go="score"]'); await page.waitForTimeout(400);
  const scoreView = await page.evaluate(() => ({
    ranges: document.querySelectorAll('#scoreBody input[type=range]').length,
    sum: document.querySelector('.wt-sum b') ? document.querySelector('.wt-sum b').textContent : '',
    bench: document.querySelectorAll('#scoreBody table tbody tr').length,
    legend: document.querySelectorAll('#scoreBody .lv-legend span').length
  }));
  console.log('SCORE ' + JSON.stringify(scoreView));
  await page.screenshot({ path: '_build/shot_p_score.png', fullPage: true });

  await page.click('.nav-item[data-go="board"]'); await page.waitForTimeout(400);
  const boardView = await page.evaluate(() => ({
    kpis: document.querySelectorAll('#boardBody .kpi').length,
    dips: Array.from(document.querySelectorAll('#boardBody .kpi-v')).map(e => e.textContent),
    dots: document.querySelectorAll('#boardBody svg circle').length,
    bands: document.querySelectorAll('#boardBody .pb-row').length,
    picks: document.querySelectorAll('#boardBody .rows .row').length
  }));
  console.log('BOARD ' + JSON.stringify(boardView));
  await page.screenshot({ path: '_build/shot_p_board.png', fullPage: true });

  await page.click('.nav-item[data-go="product"]'); await page.waitForTimeout(300);
  await page.screenshot({ path: '_build/shot_p_product.png', fullPage: true });

  await page.click('.nav-item[data-go="score"]'); await page.waitForTimeout(300);
  await page.evaluate(() => {
    const r = document.querySelectorAll('#scoreBody input[type=range]')[0];
    r.value = 30; r.dispatchEvent(new Event('input', { bubbles: true }));
    r.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForTimeout(500);
  const wt = await page.evaluate(() => ({
    sum: document.querySelector('.wt-sum b').textContent,
    first: document.querySelector('#scoreBody table tbody tr td:nth-child(2)').textContent
  }));
  console.log('WEIGHT-ADJUST ' + JSON.stringify(wt));
  await page.click('#btnResetWt'); await page.waitForTimeout(400);

  await page.click('.nav-item[data-go="product"]'); await page.waitForTimeout(300);
  await page.click('#btnNew'); await page.waitForTimeout(350);
  await page.fill('[data-f="商品名称"]', '交互验收测试商品');
  await page.fill('[data-f="价格"]', '259');
  await page.fill('[data-f="环比增速"]', '45');
  await page.click('[data-of="与我方 SKU 重合度"][data-opt="全新"]');
  await page.click('[data-of="技术壁垒"][data-opt="独家原料"]');
  await page.click('[data-of="备案路径"][data-opt="普通化妆品备案"]');
  await page.waitForTimeout(300);
  await page.click('#formSave'); await page.waitForTimeout(900);
  await page.reload(); await page.waitForTimeout(1000);
  const after = await page.evaluate(() => {
    const t = Array.from(document.querySelectorAll('#productBody .card-title')).map(e => e.textContent);
    return { n: t.length, found: t.includes('交互验收测试商品'), first: t[0],
      firstScore: document.querySelector('#productBody .score-pill b') ? document.querySelector('#productBody .score-pill b').textContent : '' };
  });
  console.log('SAVE-RELOAD ' + JSON.stringify(after));

  await page.click('#btnImport'); await page.waitForTimeout(350);
  await page.fill('#impText', '商品名称\t品牌\t价格\t销量\t环比增速\t关联达人数\t退货率\n导入测试A\tBrandX\t159\t8800\t55\t6\t3.2\n导入测试B\tBrandY\t420\t2300\t22\t34\t6.5\n交互验收测试商品\tDupe\t1\t1\t1\t1\t1');
  await page.click('#impDo'); await page.waitForTimeout(500);
  console.log('IMPORT-PARSE ' + JSON.stringify(await page.evaluate(() => ({ stat: document.querySelector('#impStat').textContent }))));
  await page.click('#impDo'); await page.waitForTimeout(1800);
  const imported = await page.evaluate(() => ({
    stat: document.querySelector('#impStat').textContent,
    n: document.querySelectorAll('#productBody .card').length,
    files: Array.from(document.querySelectorAll('#productBody .card-title')).map(e => e.textContent)
  }));
  console.log('IMPORT-DONE ' + JSON.stringify(imported));
  await page.click('#impClose'); await page.waitForTimeout(300);

  await page.click('#btnSettings'); await page.waitForTimeout(300);
  await page.click('#btnClearDemo'); await page.waitForTimeout(1500);
  console.log('CLEAR-DEMO ' + JSON.stringify(await page.evaluate(() => ({
    n: document.querySelectorAll('#productBody .card').length,
    empty: !!document.querySelector('#productBody .empty')
  }))));
  await page.click('#setClose'); await page.waitForTimeout(300);

  await page.click('#btnSettings'); await page.waitForTimeout(250);
  page.on('dialog', d => d.accept());
  await page.click('#btnClearAll'); await page.waitForTimeout(1800);
  console.log('BLANK-STATE ' + JSON.stringify(await page.evaluate(() => ({
    empty: !!document.querySelector('#productBody .empty'),
    board: document.querySelectorAll('#boardBody .kpi').length,
    score: !!document.querySelector('#scoreBody .empty'),
    today: document.querySelector('#todayList').textContent.trim().slice(0, 22)
  }))));
  await page.click('#setClose'); await page.waitForTimeout(250);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: '_build/shot_p_mobile.png', fullPage: true });
  const mob = await page.evaluate(() => {
    const g = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().height) : 0; };
    return { tabH: g('.tab'), newBtn: g('#btnNew'), impBtn: g('#btnImport'),
      tabbar: getComputedStyle(document.querySelector('.tabbar')).display,
      scrollW: document.documentElement.scrollWidth, winW: window.innerWidth };
  });
  console.log('MOBILE ' + JSON.stringify(mob));
  console.log('ERRORS ' + JSON.stringify(errs.slice(0, 6)));
  await browser.close();
})();
