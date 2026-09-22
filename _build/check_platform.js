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
  await page.waitForTimeout(1000);

  /* ---------- BASE ---------- */
  const base = await page.evaluate(() => ({
    nav: document.querySelectorAll('#nav .nav-item').length,
    navOn: (document.querySelector('#nav .nav-item.on') || {}).textContent,
    title: document.querySelector('#viewTitle').textContent,
    desc: document.querySelector('#viewDesc').textContent,
    kpi: document.querySelectorAll('#view .kpi').length,
    kpiVals: Array.from(document.querySelectorAll('#view .kpi .vl')).map(e => e.textContent.trim()),
    svg: document.querySelectorAll('#view svg').length,
    scatterDots: document.querySelectorAll('#view circle').length,
    cmpRows: document.querySelectorAll('#view .cmp-r').length,
    chips: document.querySelectorAll('#chips .chip').length,
    sync: document.querySelector('#syncText').textContent,
    bindable: document.querySelectorAll('[data-sp-bindable="database"]').length
  }));
  log('BASE ' + JSON.stringify(base, null, 1));

  /* ---------- RANK ---------- */
  await page.click('#nav .nav-item[data-view="rank"]');
  await page.waitForTimeout(400);
  const rank = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll('#view .rk'));
    return {
      tabs: document.querySelectorAll('#view .rank-tab').length,
      onTab: (document.querySelector('#view .rank-tab.on') || {}).textContent,
      rows: rows.length,
      first: rows[0] ? rows[0].querySelector('.rk-name').textContent : null,
      firstVal: rows[0] ? rows[0].querySelector('.rk-val').textContent.trim() : null,
      title: document.querySelector('#viewTitle').textContent
    };
  });
  log('RANK ' + JSON.stringify(rank, null, 1));

  await page.click('#view .rank-tab[data-rank="kol"]');
  await page.waitForTimeout(350);
  const kol = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll('#view .rk'));
    const nums = rows.slice(0, 6).map(r => parseInt((r.querySelector('.rk-val').textContent.match(/(\d+)\s*个达人/) || [0, -1])[1], 10));
    return { onTab: document.querySelector('#view .rank-tab.on').textContent, first: rows[0].querySelector('.rk-name').textContent, firstVal: rows[0].querySelector('.rk-val').textContent.trim(), nums };
  });
  log('RANK-KOL ' + JSON.stringify(kol, null, 1));

  /* ---------- LIB ---------- */
  await page.click('#nav .nav-item[data-view="lib"]');
  await page.waitForTimeout(400);
  const lib = await page.evaluate(() => ({
    cards: document.querySelectorAll('#view .pc').length,
    svgs: document.querySelectorAll('#view svg').length,
    first: document.querySelector('#view .pc .pc-name').textContent,
    tags: document.querySelectorAll('#view .pc .tag').length,
    title: document.querySelector('#viewTitle').textContent
  }));
  log('LIB ' + JSON.stringify(lib, null, 1));

  /* ---------- DRAWER ---------- */
  await page.click('#view .pc');
  await page.waitForTimeout(450);
  const drawer = await page.evaluate(() => {
    const d = document.querySelector('#drawer');
    return {
      on: d.classList.contains('on'),
      name: (d.querySelector('.dw-hd h3') || {}).textContent,
      groups: d.querySelectorAll('.dw-grp').length,
      rows: d.querySelectorAll('.dw-r').length,
      kpi: d.querySelectorAll('.kpi').length,
      note: !!d.querySelector('.dw-note')
    };
  });
  log('DRAWER ' + JSON.stringify(drawer, null, 1));
  await page.click('#drawer [data-close]');
  await page.waitForTimeout(300);

  /* ---------- INSIGHT ---------- */
  await page.click('#nav .nav-item[data-view="insight"]');
  await page.waitForTimeout(450);
  const ins = await page.evaluate(() => ({
    cards: document.querySelectorAll('#view .ins').length,
    titles: Array.from(document.querySelectorAll('#view .ins-t')).map(e => e.textContent),
    evs: Array.from(document.querySelectorAll('#view .ins-ev')).map(e => e.textContent.trim().slice(0, 60)),
    rows: document.querySelectorAll('#view .ins-row').length,
    mix: document.querySelectorAll('#view .ins-list').length
  }));
  log('INSIGHT ' + JSON.stringify(ins, null, 1));

  /* ---------- IMPORT（按源导入：第 1 步选源 → 第 2 步粘贴） ---------- */
  await page.click('#btnImport');
  await page.waitForTimeout(400);
  const impStep1 = await page.evaluate(() => ({
    srcCards: document.querySelectorAll('#modal .src-card').length,
    nextDisabled: document.querySelector('#impNext').disabled
  }));
  await page.click('#modal .src-card[data-imp-src="蝉妈妈"]');
  await page.waitForTimeout(200);
  await page.click('#impNext');
  await page.waitForTimeout(400);
  await page.click('#impFill');
  await page.waitForTimeout(200);
  const draftSaved = await page.evaluate(() => (localStorage.getItem('wb_global_select_draft') || '').length > 20);
  await page.click('#impParse');
  await page.waitForTimeout(350);
  const imp = await page.evaluate(() => ({
    status: document.querySelector('#impStatus').textContent.trim(),
    cov: document.querySelector('#impCov').textContent.trim().slice(0, 80),
    goDisabled: document.querySelector('#impGo').disabled
  }));
  log('IMPORT-PARSE ' + JSON.stringify({ impStep1, draftSaved, ...imp }, null, 1));

  const before = await page.evaluate(() => state.list.length);
  await page.click('#impGo');
  await page.waitForTimeout(1800);
  const imp2 = await page.evaluate(() => ({
    total: state.list.length,
    real: state.list.filter(r => (r['数据标记'] || '') === '真实').length,
    srcSet: Array.from(new Set(state.list.filter(r => (r['数据标记'] || '') === '真实').map(r => r['数据来源']))),
    draftCleared: !localStorage.getItem('wb_global_select_draft'),
    modalClosed: !document.querySelector('#modal').classList.contains('on')
  }));
  log('IMPORT-DONE ' + JSON.stringify({ before, ...imp2 }, null, 1));

  /* ---------- FILTER ---------- */
  await page.click('#nav .nav-item[data-view="board"]');
  await page.waitForTimeout(300);
  const allN = await page.evaluate(() => state.list.length);
  await page.click('#chips .chip[data-f="market"][data-v="韩国"]');
  await page.waitForTimeout(350);
  const filt = await page.evaluate(() => ({
    on: (document.querySelector('#chips .chip.on') || {}).textContent,
    desc: document.querySelector('#viewDesc').textContent,
    cmpRows: document.querySelectorAll('#view .cmp-r').length
  }));
  log('FILTER ' + JSON.stringify({ allN, ...filt }, null, 1));
  await page.click('#chips .chip[data-f="market"][data-v="全部"]');
  await page.waitForTimeout(300);

  /* ---------- SEARCH ---------- */
  await page.fill('#kw', '头皮');
  await page.waitForTimeout(500);
  const srch = await page.evaluate(() => ({
    n: state.list.filter(r => {
      const hay = [r['商品名称'], r['品牌'], r['概念标签'], r['核心功效成分'], r['细分品类']].join(' ');
      if (hay.indexOf('头皮') < 0) return false;
      if (state.market !== '全部' && r['所属市场'] !== state.market) return false;
      if (state.cat !== '全部' && r['品类'] !== state.cat) return false;
      return true;
    }).length,
    desc: document.querySelector('#viewDesc').textContent
  }));
  log('SEARCH ' + JSON.stringify(srch, null, 1));
  await page.fill('#kw', '');
  await page.waitForTimeout(450);

  /* ---------- MOBILE ---------- */
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(450);
  const mob = await page.evaluate(() => {
    const tb = document.querySelector('#tabbar');
    const btns = Array.from(document.querySelectorAll('#tabbar button'));
    const side = document.querySelector('.side');
    return {
      tabbarShown: getComputedStyle(tb).display !== 'none',
      tabH: Math.round(tb.getBoundingClientRect().height),
      tabBtns: btns.length,
      minBtn: Math.min.apply(null, btns.map(b => Math.round(b.getBoundingClientRect().height))),
      sideHidden: getComputedStyle(side).display === 'none',
      scrollW: document.documentElement.scrollWidth,
      winW: window.innerWidth
    };
  });
  log('MOBILE ' + JSON.stringify(mob, null, 1));
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.waitForTimeout(350);

  /* ---------- PERSIST ---------- */
  await page.reload();
  await page.waitForTimeout(1100);
  const persist = await page.evaluate(() => ({ total: state.list.length, view: state.view }));
  log('PERSIST ' + JSON.stringify(persist, null, 1));

  /* ---------- CLEAR DEMO ---------- */
  await page.click('#btnMore');
  await page.waitForTimeout(350);
  await page.click('#btnClearDemo');
  await page.waitForTimeout(2200);
  const cleared = await page.evaluate(() => ({
    total: state.list.length,
    real: state.list.filter(r => (r['数据标记'] || '') === '真实').length,
    html: document.querySelector('#view').textContent.trim().slice(0, 70)
  }));
  log('CLEAR-DEMO ' + JSON.stringify(cleared, null, 1));

  /* ---------- BLANK ---------- */
  const blank = await page.evaluate(() => {
    const out = {};
    ['board', 'rank', 'lib', 'insight'].forEach(v => {
      state.view = v; refreshAll();
      out[v] = document.querySelector('#view').textContent.trim().slice(0, 34);
    });
    return out;
  });
  log('BLANK ' + JSON.stringify(blank, null, 1));

  log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
