// 验证：新字段（SKU 数 / 备案许可号 / 法规合规声明）在商品档案抽屉里真的显示出来
const { chromium } = require('playwright');
const fs = require('fs');
const PAGE = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/全球选品平台.html';
const NUM = new Set(['价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分', '评价数', '预估成本', 'SKU 数']);

function wrap(rec, i) {
  const o = {};
  for (const [k, v] of Object.entries(rec)) {
    if (v === null || v === '' || v === undefined || k.startsWith('_')) continue;
    o[k] = NUM.has(k) ? { number: Number(v) } : { text: String(v) };
  }
  o._id = 'p' + i;
  return o;
}
const snap = JSON.parse(fs.readFileSync('/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/cloud_platform.json', 'utf8'));
const rows = (snap.results || snap).filter(function (r) { return r['备案/许可号']; }).map(wrap);
console.log('带备案号的样本:', rows.length);

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
  const errs = [];
  p.on('pageerror', function (e) { errs.push(String(e).slice(0, 150)); });
  const mock = 'window.__SMART_PAGE__={database:{query:function(){return Promise.resolve({results:'
    + JSON.stringify(rows) + ',nextCursor:null,hasMore:false});},'
    + 'getSchema:function(){return Promise.resolve({properties:[]});},'
    + 'addRecord:function(){return Promise.resolve({recordId:"x"});},'
    + 'deleteRecord:function(){return Promise.resolve({ok:true});},'
    + 'onUpdated:function(){return function(){};}}};';
  await p.addInitScript(mock);
  await p.goto('file://' + PAGE, { waitUntil: 'load' });
  await p.waitForTimeout(2000);
  await p.evaluate(function () { document.querySelector('[data-view="lib"]').click(); });
  await p.waitForTimeout(900);
  await p.evaluate(function () { const c = document.querySelector('[data-open]'); if (c) c.click(); });
  await p.waitForTimeout(700);
  const t = await p.evaluate(function () { return document.querySelector('#drawer').innerText; });
  const lines = t.split('\n');
  for (const k of ['SKU 数', '备案/许可号', '法规合规声明']) {
    const i = lines.indexOf(k);
    console.log(k, '->', i >= 0 ? ('显示: ' + lines[i + 1]) : '未显示');
  }
  console.log('抽屉含 BPOM/FDA:', /BPOM|FDA/.test(t));
  console.log('JS 错误:', errs.length ? errs : '无');
  await b.close();
})();
