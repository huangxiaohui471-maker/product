const { chromium } = require('playwright');
const path = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/全球选品平台.html';
const F = 'file://' + encodeURIComponent(path).replace(/%2F/g, '/');
const log = (...a) => console.log(...a);

(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('C:' + m.text()); });
  page.on('dialog', d => d.accept());

  await page.goto(F);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForTimeout(1200);

  /* ---------- 1. 数据通路体检 ---------- */
  const flow = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll('#view .mk-flow .mk-r'));
    return {
      rows: rows.length,
      items: rows.map(r => ({
        mk: r.querySelector('.mn').textContent,
        badge: r.querySelector('.badge').textContent,
        src: (r.querySelector('.mt b') || {}).textContent
      }))
    };
  });
  log('FLOW ' + JSON.stringify(flow, null, 1));

  /* ---------- 2. 覆盖度热力格 ---------- */
  const cov = await page.evaluate(() => ({
    cells: document.querySelectorAll('#view .cov .cell').length,
    zeroCells: document.querySelectorAll('#view .cov .cell.z').length,
    headers: Array.from(document.querySelectorAll('#view .cov .ch')).length
  }));
  log('COVERAGE ' + JSON.stringify(cov));

  /* ---------- 3. 来源筛选 chips ---------- */
  const srcChips = await page.evaluate(() =>
    Array.from(document.querySelectorAll('#chips .chip[data-f="src"]')).map(c => c.textContent.trim()));
  log('SRC-CHIPS ' + JSON.stringify(srcChips));

  await page.click('#chips .chip[data-f="src"][data-v="FastMoss"]');
  await page.waitForTimeout(400);
  const only = await page.evaluate(() => ({
    onSrc: (document.querySelector('#chips .chip[data-f="src"].on') || {}).textContent.trim(),
    kpi: (document.querySelector('#view .kpi .vl') || {}).textContent.trim()
  }));
  log('SRC-FILTER ' + JSON.stringify(only));
  await page.click('#chips .chip[data-f="src"][data-v="全部"]');
  await page.waitForTimeout(350);

  /* ---------- 4. 空态三分解：复现截图场景 东南亚+护肤+沐浴油 ---------- */
  await page.click('#chips .chip[data-f="market"][data-v="东南亚"]');
  await page.waitForTimeout(300);
  await page.click('#chips .chip[data-f="cat"][data-v="护肤"]');
  await page.waitForTimeout(300);
  await page.fill('#kw', '沐浴油');
  await page.waitForTimeout(700);

  const diag = await page.evaluate(() => {
    const d = document.querySelector('#view .diag');
    if (!d) return { hasDiag: false, html: document.querySelector('#view').textContent.slice(0, 200) };
    return {
      hasDiag: true,
      head: d.querySelector('.diag-hd b').textContent,
      items: Array.from(d.querySelectorAll('.diag-i')).map(i => ({
        t: i.querySelector('.dt').textContent,
        d: i.querySelector('.dd').textContent.slice(0, 120),
        acts: Array.from(i.querySelectorAll('.mini')).map(b => b.textContent.trim())
      }))
    };
  });
  log('DIAG-BOARD ' + JSON.stringify(diag, null, 1));

  /* 机会洞察也应是诊断而不是死胡同 */
  await page.click('#nav .nav-item[data-view="insight"]');
  await page.waitForTimeout(450);
  const diagIns = await page.evaluate(() => {
    const d = document.querySelector('#view .diag');
    return { hasDiag: !!d, items: d ? Array.from(d.querySelectorAll('.diag-i .dt')).map(x => x.textContent) : [] };
  });
  log('DIAG-INSIGHT ' + JSON.stringify(diagIns));

  /* 点「取消品类限制」应立刻出结果 */
  const btnCat = await page.$('#view .mini[data-f="cat"]');
  if (btnCat) { await btnCat.click(); await page.waitForTimeout(600); }
  const afterFix = await page.evaluate(() => {
    const d = document.querySelector('#view .diag');
    const s = document.querySelector('#chips .chip[data-f="cat"].on');
    return {
      stillDiag: !!d,
      onCat: s ? s.textContent.trim() : null,
      cards: document.querySelectorAll('#view .ins').length,
      firstCardTitle: (document.querySelector('#view .ins .ins-t') || {}).textContent || null
    };
  });
  log('AFTER-UNLOCK-CAT ' + JSON.stringify(afterFix));

  /* ---------- 5. 引擎体检 + 字段缺口告警 ---------- */
  await page.click('#chips .chip[data-f="market"][data-v="全部"]');
  await page.waitForTimeout(250);
  await page.fill('#kw', '');
  await page.waitForTimeout(600);
  const health = await page.evaluate(() => ({
    rows: Array.from(document.querySelectorAll('#view .mk-r')).map(r => ({
      n: r.querySelector('.mn').textContent,
      badge: r.querySelector('.badge').textContent
    })),
    warns: document.querySelectorAll('#view .rule-warn').length,
    cards: document.querySelectorAll('#view .ins').length
  }));
  log('ENGINE-HEALTH ' + JSON.stringify(health, null, 1));

  /* ---------- 6. 按源导入：源 → 市场 → 自动打来源 ---------- */
  await page.click('#btnImport');
  await page.waitForTimeout(450);
  const imp1 = await page.evaluate(() => ({
    title: document.querySelector('#modal .modal-hd, #modal h3, #modal .mtitle') ? (document.querySelector('#modal').textContent.match(/第 1 步[^·]*/) || [''])[0] : '',
    cards: document.querySelectorAll('#modal .src-card').length,
    nextDisabled: (document.querySelector('#impNext') || {}).disabled,
    cardNames: Array.from(document.querySelectorAll('#modal .src-card .sh')).map(x => x.textContent.trim())
  }));
  log('IMPORT-STEP1 ' + JSON.stringify(imp1, null, 1));

  await page.click('#modal .src-card[data-imp-src="Hwahae"]');
  await page.waitForTimeout(200);
  const picked = await page.evaluate(() => ({
    on: (document.querySelector('#modal .src-card.on .sh') || {}).textContent,
    nextDisabled: (document.querySelector('#impNext') || {}).disabled
  }));
  log('IMPORT-PICK ' + JSON.stringify(picked));

  await page.click('#impNext');
  await page.waitForTimeout(450);
  const imp2 = await page.evaluate(() => ({
    mkChips: Array.from(document.querySelectorAll('#modal .chip[data-imp-mkt]')).map(c => c.textContent.trim()),
    mkOn: (document.querySelector('#modal .chip[data-imp-mkt].on') || {}).textContent,
    hasCov: !!document.querySelector('#impCov'),
    banner: (document.querySelector('#modal .card.pad') || {}).textContent.slice(0, 120)
  }));
  log('IMPORT-STEP2 ' + JSON.stringify(imp2, null, 1));

  await page.fill('#impText', '商品名称\t销量\t销售额\t环比增速\t关联达人数\n测试品 A\t10000\t500万\t70\t6');
  await page.click('#impParse');
  await page.waitForTimeout(450);
  const parsed = await page.evaluate(() => ({
    status: document.querySelector('#impStatus').textContent.slice(0, 200),
    cov: document.querySelector('#impCov').textContent.slice(0, 160),
    goDisabled: (document.querySelector('#impGo') || {}).disabled
  }));
  log('IMPORT-PARSE ' + JSON.stringify(parsed, null, 1));

  /* 市场改成不覆盖的市场 → 应出警告 */
  await page.evaluate(() => {
    /* 造一个不覆盖的组合：手动把 impMkt 换成别的市场（Hwahae 只覆盖韩国） */
    window.impMkt = '东南亚';
  });
  await page.fill('#impText', '商品名称\t销量\n测试品 A\t10000');
  await page.click('#impParse');
  await page.waitForTimeout(400);
  const covWarn = await page.evaluate(() => document.querySelector('#impCov').textContent.slice(0, 200));
  log('IMPORT-COVWARN ' + JSON.stringify(covWarn));

  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  /* ---------- 7. 数据源地图 ---------- */
  await page.click('.side-map');
  await page.waitForTimeout(450);
  const map = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll('#modal .smap-tb tbody tr'));
    return {
      open: !!document.querySelector('#modal.on'),
      rows: rows.length,
      heads: Array.from(document.querySelectorAll('#modal .smap-tb th')).map(t => t.textContent),
      firstSrc: rows[0] ? rows[0].querySelector('td b').textContent : null,
      hasKoreaNote: document.querySelector('#modal').textContent.indexOf('TikTok Shop 韩国站') >= 0
    };
  });
  log('SRCMAP ' + JSON.stringify(map, null, 1));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(250);

  /* ---------- 8. 移动端 ---------- */
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  const mob = await page.evaluate(() => ({
    tabbar: document.querySelectorAll('.tabbar button').length,
    tabbarH: document.querySelector('.tabbar button') ? Math.round(document.querySelector('.tabbar button').getBoundingClientRect().height) : 0,
    hscroll: document.documentElement.scrollWidth > window.innerWidth + 2,
    sideHidden: getComputedStyle(document.querySelector('.side')).display === 'none',
    fontKw: getComputedStyle(document.querySelector('#kw')).fontSize
  }));
  log('MOBILE ' + JSON.stringify(mob));
  await page.screenshot({ path: '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/shot_src_mobile.png', fullPage: false });

  await page.setViewportSize({ width: 1440, height: 960 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/shot_flow.png', fullPage: false });

  log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
