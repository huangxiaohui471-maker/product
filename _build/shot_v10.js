// v10 视觉验收：桌面 / 移动端 / 洞察 / 档案抽屉 各截一张。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const D = path.join(__dirname, 'data');
const PAGE = process.env.PAGE_PATH || path.join(__dirname, '..', '全球选品平台.html');
const OUT = path.join(__dirname, 'shots_v10');
fs.mkdirSync(OUT, { recursive: true });

const NUM = new Set(['价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分', '评价数',
  '预估成本', 'SKU 数']);
const SEL = new Set(['品类', '数据来源', '所属市场', '国家/地区', '剂型', '技术壁垒', '评价来源',
  '备案路径', '宣称支撑难度', '与我方价格带匹配', '与我方客群匹配', '与我方 SKU 重合度', '决策状态', '数据标记']);

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
const NEWF = ['SKU 数', '备案/许可号', '法规合规声明'];
for (const rec of recs) {
  const c = cloudByPid[String(rec['商品ID'] || '')];
  if (c) for (const k of NEWF) if (c[k] !== undefined && c[k] !== null && c[k] !== '') rec[k] = c[k];
}
const prodRows = recs.map(wrap);

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
    await p.addInitScript(MOCK);
    await p.goto('file://' + PAGE, { waitUntil: 'load' });
    await p.waitForTimeout(2200);
    if (steps) await steps(p);
    await p.screenshot({ path: path.join(OUT, name + '.png'), fullPage: false });
    console.log(name, '| 错误:', errs.length ? errs : '无');
    await p.close();
  }

  await shot('01_board_desktop', 1440, 980);
  await shot('02_board_mobile', 390, 844);
  await shot('03_insight', 1440, 980, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="insight"]').click());
    await p.waitForTimeout(1100);
  });
  await shot('04_drawer', 1440, 980, async (p) => {
    await p.evaluate(() => document.querySelector('[data-view="lib"]').click());
    await p.waitForTimeout(900);
    await p.evaluate(() => {
      const c = document.querySelector('.pc[data-open], [data-open]');
      if (c) c.click();
    });
    await p.waitForTimeout(900);
  });
  await shot('05_board_mobile_hero', 390, 844, async (p) => {
    await p.evaluate(() => window.scrollTo(0, 0));
  });
  await b.close();
})();
