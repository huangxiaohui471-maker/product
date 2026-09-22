// 截图：看板 / 国家市场 / 品类树 / 成分库
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const D = path.join(__dirname, 'data');
const PAGE = path.join(__dirname, '..', '全球选品平台.html');

const NUM = new Set(['价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分', '评价数', '预估成本']);
const SEL = new Set(['品类', '数据来源', '所属市场', '国家/地区', '剂型', '技术壁垒', '评价来源', '备案路径',
  '宣称支撑难度', '与我方价格带匹配', '与我方客群匹配', '与我方 SKU 重合度', '决策状态', '数据标记']);
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
const recs = JSON.parse(fs.readFileSync(path.join(D, 'records_cat_400.json'), 'utf8'));
const prodRows = (recs.records || recs).map(wrap);
const rowsJson = JSON.stringify(prodRows);
const MOCK = 'window.__SMART_PAGE__={database:{query:function(o){return Promise.resolve({results:window.__PR,nextCursor:null,hasMore:false});},'
  + 'getSchema:function(){return Promise.resolve({properties:[]});},addRecord:function(){return Promise.resolve({});},'
  + 'deleteRecord:function(){return Promise.resolve({});},onUpdated:function(){return function(){};}}};window.__PR=' + rowsJson + ';';

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 1050 } });
  await p.addInitScript(MOCK);
  await p.goto('file://' + PAGE, { waitUntil: 'load' });
  await p.waitForTimeout(3200);
  await p.screenshot({ path: path.join(D, 'shot_board.png') });
  await p.evaluate(() => { const els = document.querySelectorAll('.sec'); els[els.length - 2].scrollIntoView(); });
  await p.waitForTimeout(400);
  await p.screenshot({ path: path.join(D, 'shot_country.png') });
  await p.evaluate(() => { const e = document.querySelector('[data-view="lib"]'); if (e) e.click(); });
  await p.waitForTimeout(900);
  await p.evaluate(() => { const e = document.querySelector('.ct-hd[data-exp="l1"]'); if (e) e.click(); });
  await p.waitForTimeout(600);
  await p.screenshot({ path: path.join(D, 'shot_tree.png') });
  await p.evaluate(() => { const e = document.querySelector('[data-tab="ing"]'); if (e) e.click(); });
  await p.waitForTimeout(800);
  await p.screenshot({ path: path.join(D, 'shot_ing.png') });
  await b.close();
  console.log('截图完成');
})();
