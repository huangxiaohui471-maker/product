// v8 渲染验收：喂真实的 360 条选品数据 + 37 条口碑数据，逐个视图跑一遍，
// 检查 5 个视图、品类树展开、成分库 Tab、4 条新洞察规则是否都真的渲染出来，且无 JS 报错。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const D = path.join(__dirname, 'data');
const PAGE = process.env.PAGE_PATH || path.join(__dirname, '..', '全球选品平台.html');

const NUM = new Set(['价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分', '评价数',
  '预估成本', '评价数', '好评数', '好评率', '差评订单数', '差评率', '评价差评率',
  '品质退货数', '品质退货率', '投诉数', '投诉率', 'SKU 数']);
const SEL = new Set(['品类', '数据来源', '所属市场', '国家/地区', '剂型', '技术壁垒', '评价来源',
  '备案路径', '宣称支撑难度', '与我方价格带匹配', '与我方客群匹配', '与我方 SKU 重合度', '决策状态', '数据标记']);
const DATE = new Set(['上市日期']);

function wrap(rec, i) {
  const out = {};
  for (const [k, v] of Object.entries(rec)) {
    if (v === null || v === '' || v === undefined || k.startsWith('_')) continue;
    if (NUM.has(k)) out[k] = { number: Number(v) };
    else if (SEL.has(k)) out[k] = { select: String(v) };
    else if (DATE.has(k)) out[k] = { date: String(v).slice(0, 19) };
    else out[k] = { text: String(v) };
  }
  out._id = 'p' + i;
  return out;
}

const ai = JSON.parse(fs.readFileSync(path.join(D, 'records_cat_400.json'), 'utf8'));
const recs = (ai.records || ai);

// v10：把云表里新增的「法规 / SKU 结构」字段按 商品ID 合并进来，
// 让冒烟测试也能覆盖 Hero 的「已备案」计数与档案里的新字段。
const cloudSnap = JSON.parse(fs.readFileSync(path.join(__dirname, 'cloud_platform.json'), 'utf8'));
const cloudByPid = {};
for (const c of (cloudSnap.results || cloudSnap)) if (c['商品ID']) cloudByPid[String(c['商品ID'])] = c;
const NEWF = ['SKU 数', '备案/许可号', '法规合规声明'];
for (const rec of recs) {
  const c = cloudByPid[String(rec['商品ID'] || '')];
  if (!c) continue;
  for (const k of NEWF) {
    if (c[k] !== undefined && c[k] !== null && c[k] !== '') rec[k] = c[k];
  }
}
const prodRows = recs.map(wrap);

const us = JSON.parse(fs.readFileSync(path.join(D, 'douyin_usersound.json'), 'utf8'));
const pct = (x) => (x == null ? null : Math.round(x * 10000) / 100);
const reviewRows = us.products.map((p, i) => {
  const o = {
    商品名称: p.name, 商品ID: p.id, 店铺类目: p.cat || '', 评价数: p.eval_cnt, 好评数: p.good_cnt,
    好评率: pct(p.good_ratio), 差评订单数: p.bad_cnt, 差评率: pct(p.bad_ratio),
    好评关键词: (p.good || []).map((x) => x.label).join(' / '),
    差评关键词: (p.bad || []).map((x) => x.label).join(' / '),
    差评原因: (p.reason || []).map((x) => `${x.label} ${x.n}`).join(' / '),
    数据来源: '抖音罗盘', 评价来源: '抖音评价', _id: 'r' + i,
  };
  return wrap(o, 'r' + i);
});

// 注意：JS 里字符串后面的 `%` 是取模，不是格式化——早先用 `'... %d ...' % n` 全打成了 NaN
console.log(`商品 ${prodRows.length} 条 / 口碑 ${reviewRows.length} 条`);
console.log('含 国家/地区 的:', prodRows.filter((r) => r['国家/地区']).length);
console.log('含 二级类目 的:', prodRows.filter((r) => r['二级类目']).length);
console.log('含 核心功效成分 的:', prodRows.filter((r) => r['核心功效成分']).length);

const PRODUCT_DB = 'Hu5q2PAyW17BmdP5JPQ9os';
const REVIEW_DB = 'ZOiFonS5w7psZlgM5kJjiD';

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
  const errs = [];
  p.on('pageerror', (e) => errs.push('pageerror: ' + String(e).slice(0, 200)));
  p.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });

  const MOCK = `window.__SMART_PAGE__ = { database: {
      query: function(o){ var db = (o && o.databaseId) === '${REVIEW_DB}' ? window.__RV : window.__PR;
        return Promise.resolve({ results: db, nextCursor: null, hasMore: false }); },
      getSchema: function(o){ return Promise.resolve({ properties: (o && o.databaseId) === '${REVIEW_DB}' ? window.__RVSCHEMA : window.__PRSCHEMA }); },
      addRecord: function(){ return Promise.resolve({ recordId: 'mock-new' }); },
      deleteRecord: function(){ return Promise.resolve({ ok: true }); },
      onUpdated: function(){ return function(){}; }
    } };
    window.__PR = ${JSON.stringify(prodRows)};
    window.__RV = ${JSON.stringify(reviewRows)};
    window.__PRSCHEMA = [];
    window.__RVSCHEMA = [];`;
  await p.addInitScript(MOCK);

  await p.goto('file://' + PAGE, { waitUntil: 'load' });
  await p.waitForTimeout(3000);

  const out = await p.evaluate(() => {
    const r = {};
    const chips = document.querySelector('#chips');
    r.filterSel = chips ? Array.from(chips.querySelectorAll('select[data-f-sel]')).map((s) => s.getAttribute('data-f-sel') + ':' + s.options.length) : [];
    r.viewBtn = Array.from(document.querySelectorAll('[data-view]')).map((x) => x.getAttribute('data-view'));
    return r;
  });
  console.log('\n筛选下拉:', JSON.stringify(out.filterSel));
  console.log('视图按钮:', JSON.stringify(out.viewBtn));

  const views = ['board', 'rank', 'lib', 'insight', 'review'];
  for (const v of views) {
    const before = errs.length;
    await p.evaluate((vv) => {
      const el = document.querySelector('[data-view="' + vv + '"]');
      if (el) el.click();
    }, v);
    await p.waitForTimeout(900);
    let info;
    if (v === 'board') {
      info = await p.evaluate(() => ({
        secs: Array.from(document.querySelectorAll('.sec-hd h2')).map((x) => x.textContent),
        cmp6: document.querySelectorAll('.cmp-hd6').length,
        cmp6rows: document.querySelectorAll('.cmp-hd6 ~ .cmp-r, .cmp-hd6').length,
        hero: !!document.querySelector('.hero'),
        heroLine: (document.querySelector('.hero-h') || {}).innerText || '',
        heroStats: Array.from(document.querySelectorAll('.hero-stat')).map((x) => x.querySelector('.l').innerText + '=' + x.querySelector('.v').innerText),
        heroBtns: Array.from(document.querySelectorAll('.hero-btn')).map((x) => x.innerText),
        anim: document.querySelector('#view').classList.contains('anim'),
        text: document.body.innerText.slice(0, 0),
      }));
    } else if (v === 'insight') {
      info = await p.evaluate(() => ({
        cards: Array.from(document.querySelectorAll('.ins .ins-t')).map((x) => x.textContent),
        rows: document.querySelectorAll('.ins-row').length,
        health: (document.querySelector('.card.pad .hint') || {}).innerText || '',
      }));
    } else if (v === 'lib') {
      // 品类树
      const t = await p.evaluate(() => ({
        tabs: Array.from(document.querySelectorAll('.tab')).map((x) => x.textContent),
        l1: document.querySelectorAll('.ct-hd[data-exp="l1"]').length,
        rows: document.querySelectorAll('.cmp-r').length,
      }));
      // 展开第一个一级
      await p.evaluate(() => { const e = document.querySelector('.ct-hd[data-exp="l1"]'); if (e) e.click(); });
      await p.waitForTimeout(600);
      const t2 = await p.evaluate(() => ({
        l2: document.querySelectorAll('.ct-hd[data-exp="l2"]').length,
        l2label: Array.from(document.querySelectorAll('.ct-hd[data-exp="l2"] .ct-nm')).slice(0, 6).map((x) => x.textContent),
      }));
      await p.evaluate(() => { const e = document.querySelector('.ct-hd[data-exp="l2"]'); if (e) e.click(); });
      await p.waitForTimeout(600);
      const t3 = await p.evaluate(() => ({
        l3: document.querySelectorAll('.ct-row.lv3').length,
        l3label: Array.from(document.querySelectorAll('.ct-row.lv3 .ct-nm')).slice(0, 6).map((x) => x.textContent),
      }));
      // 切成分库
      await p.evaluate(() => { const e = document.querySelector('[data-tab="ing"]'); if (e) e.click(); });
      await p.waitForTimeout(700);
      const ing = await p.evaluate(() => ({
        n: document.querySelectorAll('.ing').length,
        first: Array.from(document.querySelectorAll('.ing')).slice(0, 5).map((x) => {
          const nm = x.querySelector('.ing-nm'); const ct = x.querySelector('.ing-ct');
          return (nm ? nm.textContent : '') + '(' + (ct ? ct.textContent : '') + ')';
        }),
        kv: (document.querySelector('.ing .ing-kv') || {}).innerText || '',
        ct3: (document.querySelector('.ing .ing-ct3') || {}).textContent || '',
      }));
      info = Object.assign({}, t, { l2: t2.l2, l2label: t2.l2label, l3: t3.l3, l3label: t3.l3label, ingN: ing.n, ingFirst: ing.first, ingCt3: ing.ct3 });
      // 切回品类树
      await p.evaluate(() => { const e = document.querySelector('[data-tab="cat"]'); if (e) e.click(); });
      await p.waitForTimeout(500);
    } else if (v === 'review') {
      info = await p.evaluate(() => ({ rows: document.querySelectorAll('.rv-row, .card').length }));
    } else {
      info = await p.evaluate(() => ({ items: document.querySelectorAll('.rk-row, .card').length }));
    }
    console.log(`\n=== ${v} ===`);
    console.log(JSON.stringify(info, null, 1).slice(0, 1400));
    console.log('新增错误:', errs.length - before);
  }

  // 下拉筛选联动（先切回看板，筛选行只在非口碑视图出现）
  await p.evaluate(() => { const e = document.querySelector('[data-view="board"]'); if (e) e.click(); });
  await p.waitForTimeout(700);
  const f1 = await p.evaluate(async () => {
    const s = document.querySelector('select[data-f-sel="country"]');
    if (!s) return 'no-select';
    const opt = Array.from(s.options).find((o) => o.value !== '全部');
    s.value = opt.value;
    s.dispatchEvent(new Event('change', { bubbles: true }));
    return opt.value;
  });
  await p.waitForTimeout(900);
  const f2 = await p.evaluate(() => ({
    selected: (document.querySelector('select[data-f-sel="country"]') || {}).value,
    kpi: (document.querySelector('.kpi .vl') || {}).innerText || '',
  }));
  console.log('\n=== 国家筛选联动 ===');
  console.log('选了:', f1, '→', JSON.stringify(f2));
  // 二级类目下拉
  const g1 = await p.evaluate(() => {
    const s2 = document.querySelector('select[data-f-sel="c2"]');
    if (!s2) return 'no-select';
    const opt = Array.from(s2.options).find((o) => o.value !== '全部');
    s2.value = opt.value; s2.dispatchEvent(new Event('change', { bubbles: true }));
    return opt.value;
  });
  await p.waitForTimeout(800);
  const g2 = await p.evaluate(() => ({
    selected: (document.querySelector('select[data-f-sel="c2"]') || {}).value,
    kpi: (document.querySelector('.kpi .vl') || {}).innerText || '',
  }));
  console.log('二级类目选了:', g1, '→', JSON.stringify(g2));
  // 市场机会卡片点一行 → 应把国家筛出来
  await p.evaluate(() => { const e = document.querySelector('[data-view="insight"]'); if (e) e.click(); });
  await p.waitForTimeout(700);
  const clk = await p.evaluate(() => {
    const rows = Array.from(document.querySelectorAll('.ins-row'));
    const t = rows.find((r) => r.getAttribute('data-f') === 'country');
    if (!t) return 'no-country-row';
    t.click(); return t.getAttribute('data-v');
  });
  await p.waitForTimeout(700);
  const after = await p.evaluate(() => ({
    view: window.location.hash,
    chipSel: (document.querySelector('select[data-f-sel="country"]') || {}).value,
    selCount: document.querySelectorAll('select[data-f-sel="country"]').length,
    state: (function(){ try { return document.querySelector('[data-f="country"]') ? 'chip' : 'nochip'; } catch(e){ return 'err'; } })(),
  }));
  console.log('点市场机会行:', clk, '→', JSON.stringify(after));

  await p.screenshot({ path: path.join(D, 'page_v8.png'), fullPage: false });

  // 手机视口
  const p2 = await b.newPage({ viewport: { width: 390, height: 844 } });
  await p2.addInitScript(MOCK);
  await p2.goto('file://' + PAGE, { waitUntil: 'load' });
  await p2.waitForTimeout(2500);
  await p2.evaluate(() => { const e = document.querySelector('[data-view="lib"]'); if (e) e.click(); });
  await p2.waitForTimeout(800);
  const m = await p2.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth > window.innerWidth + 2,
    scrollW: document.documentElement.scrollWidth, winW: window.innerWidth,
    selH: (document.querySelector('.flt') || {}).offsetHeight || 0,
    tabH: (document.querySelector('.tab') || {}).offsetHeight || 0,
    inputFont: getComputedStyle(document.querySelector('input#kw')).fontSize,
  }));
  console.log('\n=== 移动端 390px ===');
  console.log(JSON.stringify(m));
  await p2.screenshot({ path: path.join(D, 'page_v8_mobile.png'), fullPage: false });

  console.log('\n=== JS 错误汇总 ===');
  if (!errs.length) console.log('无');
  else errs.slice(0, 15).forEach((e) => console.log('  ' + e));
  await b.close();
})();
