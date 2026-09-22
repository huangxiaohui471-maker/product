/* ============================================================
   V11 截图验收：spec 要求 4 张（全球看板 / 榜单中心 各桌面 + 390px）
   另附 2 张补充证据（热力图、移动端筛选抽屉）。
   任一张截图缺失或尺寸异常 → 退出码 1。
   ============================================================ */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const D = path.join(__dirname, 'data');
const PAGE = process.env.PAGE_PATH || path.join(__dirname, '..', '全球选品平台.html');
const OUT = path.join(__dirname, 'shots_v11');
fs.mkdirSync(OUT, { recursive: true });

const NUM = new Set(['价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分', '评价数',
  '预估成本', 'SKU 数']);
const SEL = new Set(['品类', '数据来源', '所属市场', '国家/地区', '剂型', '技术壁垒', '评价来源',
  '备案路径', '宣称支撑难度', '与我方价格带匹配', '与我方客群匹配', '与我方 SKU 重合度',
  '决策状态', '数据标记', '二级类目', '三级类目']);

function wrap(rec, i) {
  const out = {};
  for (const [k, v] of Object.entries(rec)) {
    if (v === null || v === '' || v === undefined || k.startsWith('_')) continue;
    if (NUM.has(k)) out[k] = { number: Number(v) };
    else if (SEL.has(k)) out[k] = { select: String(v) };
    else if (k === '上市日期') out[k] = { date: String(v).slice(0, 19) };
    else out[k] = { text: String(v) };
  }
  out._id = 'p' + i;
  return out;
}

const ai = JSON.parse(fs.readFileSync(path.join(D, 'records_cat_400.json'), 'utf8'));
const recs = (ai.records || ai);
const cloudSnap = JSON.parse(fs.readFileSync(path.join(__dirname, 'cloud_platform.json'), 'utf8'));
const cloudByPid = {};
for (const c of (cloudSnap.results || cloudSnap)) if (c['商品ID']) cloudByPid[String(c['商品ID'])] = c;
const NEWF = ['SKU 数', '备案/许可号', '法规合规声明', '数据标记', '二级类目', '三级类目', '榜单排名'];
for (const rec of recs) {
  const c = cloudByPid[String(rec['商品ID'] || '')];
  if (c) for (const k of NEWF) if (c[k] !== undefined && c[k] !== null && c[k] !== '') rec[k] = c[k];
}
const prodRows = recs.map(wrap);

const SHOTS = [];
(async () => {
  const b = await chromium.launch();
  const MOCK = `window.__SMART_PAGE__ = { database: {
      query: function(){ return Promise.resolve({ results: window.__PR, nextCursor: null, hasMore: false }); },
      getSchema: function(){ return Promise.resolve({ properties: [] }); },
      addRecord: function(){ return Promise.resolve({ recordId: 'mock-new' }); },
      deleteRecord: function(){ return Promise.resolve({ ok: true }); },
      onUpdated: function(){ return function(){}; } } };
    window.__PR = ${JSON.stringify(prodRows)};`;

  async function shot(name, w, h, steps) {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
    const errs = [];
    p.on('pageerror', (e) => errs.push(String(e).slice(0, 160)));
    p.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 160)); });
    await p.addInitScript(MOCK);
    await p.goto('file://' + PAGE, { waitUntil: 'load' });
    await p.waitForTimeout(2600);
    if (steps) await steps(p);
    const file = path.join(OUT, name + '.png');
    await p.screenshot({ path: file, fullPage: false });
    const sz = fs.existsSync(file) ? fs.statSync(file).size : 0;
    const w2 = await p.evaluate(() => document.documentElement.scrollWidth);
    SHOTS.push({ name: name, size: sz, errs: errs.length, scrollW: w2, winW: w });
    await p.close();
  }

  /* ---- 必需 4 张 ---- */
  await shot('11-01_board_desktop_1440', 1440, 980, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="board"]').click());
    await p.waitForTimeout(1100);
  });
  await shot('11-02_board_390', 390, 844, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="board"]').click());
    await p.waitForTimeout(1100);
    await p.evaluate(() => window.scrollTo(0, 0));
  });
  await shot('11-03_rank_desktop_1440', 1440, 980, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="rank"]').click());
    await p.waitForTimeout(1200);
  });
  await shot('11-04_rank_390', 390, 844, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="rank"]').click());
    await p.waitForTimeout(1200);
    /* 复审⑥·移动端榜单标题区：标题整词单行、说明与「共 N 条」自然换行不挤压 */
    const v = await p.evaluate(() => {
      const hd = document.querySelector('.rank-sec .sec-hd');
      if (!hd) return { ok: false, why: 'no .rank-sec .sec-hd' };
      const h2 = hd.querySelector('h2'), r = hd.querySelector('.r');
      if (!h2 || !r) return { ok: false, why: 'missing h2/.r' };
      const cs = getComputedStyle(h2);
      const lh = parseFloat(cs.lineHeight) || (parseFloat(cs.fontSize) * 1.5);
      const hr = h2.getBoundingClientRect(), rr = r.getBoundingClientRect(), dr = hd.getBoundingClientRect();
      return {
        ok: true,
        h2: h2.textContent,
        h2Lines: Math.round((hr.height / lh) * 100) / 100,
        h2FullRow: hr.width >= dr.width * 0.9,
        r: r.textContent,
        rNotSqueezed: r.scrollWidth <= r.clientWidth + 1,
        rAfterH2: rr.top >= hr.bottom - 2,
        scrollW: document.documentElement.scrollWidth
      };
    });
    if (!v.ok || v.h2Lines > 1.8 || !v.h2FullRow || !v.rNotSqueezed || !v.rAfterH2 || v.scrollW > 392) {
      console.log('390 榜单标题区验收失败: ' + JSON.stringify(v));
      process.exit(1);
    }
    console.log('390 榜单标题区验收: ' + JSON.stringify(v));
  });

  /* ---- 补充 2 张：本次两个新亮点 ---- */
  await shot('11-05_board_heatmap_1440', 1440, 980, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="board"]').click());
    await p.waitForTimeout(1100);
    await p.evaluate(() => {
      const h = document.querySelector('.heat-wrap');
      if (h) h.scrollIntoView({ block: 'center' });
      else window.scrollTo(0, 900);
    });
    await p.waitForTimeout(700);
  });
  await shot('11-06_mobile_filter_drawer_390', 390, 844, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="board"]').click());
    await p.waitForTimeout(900);
    await p.evaluate(() => { const b1 = document.querySelector('.flt-open'); if (b1) b1.click(); });
    await p.waitForTimeout(800);
    /* 复审⑦：结构化视觉验收，不只 display!=none */
    const v = await p.evaluate(() => {
      const layer = document.getElementById('fltLayer');
      const scrim = document.querySelector('.flt-scrim');
      const sheet = document.querySelector('.flt-sheet');
      if (!layer || !scrim || !sheet) return { ok: false, why: 'missing' };
      const lr = layer.getBoundingClientRect(), sr = scrim.getBoundingClientRect(), tr = sheet.getBoundingClientRect();
      const hit = document.elementFromPoint(innerWidth / 2, 60);
      return {
        ok: true,
        parentBody: layer.parentElement === document.body,
        covers: Math.abs(sr.width - innerWidth) < 3 && Math.abs(sr.height - innerHeight) < 3,
        hitBlocked: hit ? !!(hit.closest('.flt-scrim') || hit.closest('.flt-sheet')) : false,
        opaque: getComputedStyle(sheet).backgroundColor === 'rgb(255, 255, 255)',
        atBottom: Math.abs(tr.bottom - innerHeight) < 3,
        sbd: !!document.querySelector('.flt-sbd'),
        scrollW: document.documentElement.scrollWidth
      };
    });
    if (!v.ok || !v.parentBody || !v.covers || !v.hitBlocked || !v.opaque || !v.atBottom || !v.sbd ||
        v.scrollW > 392) {
      console.log('抽屉结构验收失败: ' + JSON.stringify(v));
      process.exit(1);
    }
    console.log('抽屉结构验收: ' + JSON.stringify(v));
  });

  await b.close();

  let bad = 0;
  console.log('\n================ V11 截图结果 ================');
  SHOTS.forEach((s) => {
    const ok = s.size > 20000 && s.errs === 0 && s.scrollW <= s.winW + 2;
    if (!ok) bad++;
    console.log((ok ? '  PASS  ' : '  FAIL  ') + s.name + '  ' + Math.round(s.size / 1024) + 'KB  JS错误=' + s.errs +
      '  scrollW=' + s.scrollW + '/' + s.winW);
  });
  console.log('目录: ' + OUT);
  if (bad) { console.log('\n*** ' + bad + ' 张截图不合格，退出码 1 ***'); process.exit(1); }
  console.log('\nV11_SHOTS_OK（必需 4 张 + 补充 2 张，均无 JS 错误、无横向溢出）');
  process.exit(0);
})().catch((e) => { console.error('截图脚本异常:', e); process.exit(2); });
