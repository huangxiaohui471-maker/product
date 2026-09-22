// 用 Playwright 打开本地页面，注入一个「假的资料库」把两张表的数据喂进去，
// 然后切到「口碑诊断」视图，检查真实渲染结果（不依赖线上环境）。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const D = path.join(__dirname, 'data');
const PAGE = path.join(__dirname, '..', '全球选品平台.html');

const us = JSON.parse(fs.readFileSync(path.join(D, 'douyin_usersound.json'), 'utf8'));

function wrap(rec) {
  const NUM = new Set(['评价数', '好评数', '好评率', '差评订单数', '差评率', '评价差评率',
    '品质退货数', '品质退货率', '投诉数', '投诉率']);
  const SEL = new Set(['数据来源', '评价来源']);
  const out = {};
  for (const [k, v] of Object.entries(rec)) {
    if (v === null || v === '') continue;
    out[k] = NUM.has(k) ? { number: v } : (SEL.has(k) ? { select: v } : { text: v });
  }
  return out;
}
const pct = (x) => (x == null ? null : Math.round(x * 10000) / 100);

const reviewRows = us.products.map((p, i) => wrap({
  商品名称: p.name, 商品ID: p.id, 店铺类目: p.cat || '',
  评价数: p.eval_cnt, 好评数: p.good_cnt, 好评率: pct(p.good_ratio),
  差评订单数: p.bad_cnt, 差评率: pct(p.bad_ratio), 评价差评率: pct(p.bad_eval_ratio),
  好评关键词: (p.good || []).map((x) => x.label).join(' / '),
  差评关键词: (p.bad || []).map((x) => x.label).join(' / '),
  差评原因: (p.reason || []).map((x) => `${x.label} ${x.n}`).join(' / '),
  差评原声: (p.reason || []).map((x) => x.sample).filter(Boolean).join(' | ').slice(0, 900),
  品质退货数: p.qreturn_cnt, 品质退货率: pct(p.qreturn_ratio),
  投诉数: p.complaint_cnt, 投诉率: pct(p.complaint_ratio),
  采集周期: us.range, 数据来源: '抖音罗盘', 评价来源: '抖音评价',
  备注: '抖音电商罗盘·体验·用户原声（本店）', _id: 'r' + i,
}));

// 主表给 3 条最小记录，够触发看板/洞察渲染即可
const prodRows = [1, 2, 3].map((n) => ({
  商品名称: '【示例】测试商品 ' + n, 商品ID: 'P' + n, 品类: { select: '护肤' },
  数据来源: { select: 'FastMoss' }, 所属市场: { select: '东南亚' },
  销量: { number: 1000 * n }, 环比增速: { number: 80 * n }, 关联达人数: { number: 40 * n },
  数据标记: { select: '示例' }, _id: 'p' + n,
}));

const PRODUCT_DB = 'Hu5q2PAyW17BmdP5JPQ9os';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.addInitScript(({ reviewRows, prodRows, PRODUCT_DB }) => {
    window.__SMART_PAGE__ = {
      database: {
        __fake: true,
        query(opts) {
          const rows = opts.databaseId === PRODUCT_DB ? prodRows : reviewRows;
          return Promise.resolve({ results: rows, nextCursor: '', hasMore: false });
        },
        getSchema(opts) {
          return Promise.resolve({
            properties: [
              { name: '商品名称', type: 'text', config: {} },
              { name: '品类', type: 'select', config: { options: [{ id: '护肤', text: '护肤' }] } },
              { name: '数据来源', type: 'select', config: { options: [{ id: 'FastMoss', text: 'FastMoss' }] } },
              { name: '所属市场', type: 'select', config: { options: [] } },
              { name: '数据标记', type: 'select', config: { options: [] } },
            ],
          });
        },
        addRecord() { return Promise.resolve({}); },
        deleteRecord() { return Promise.resolve({}); },
      },
    };
  }, { reviewRows, prodRows, PRODUCT_DB });

  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()); });

  await p.goto('file://' + PAGE, { waitUntil: 'load' });
  await p.waitForTimeout(2500);

  // 切到口碑诊断
  const ok = await p.evaluate(() => {
    const btn = document.querySelector('[data-view="review"]');
    if (!btn) return false;
    btn.click();
    return true;
  });
  await p.waitForTimeout(1200);

  const res = await p.evaluate(() => {
    const v = document.querySelector('#view');
    const txt = v ? v.innerText : '';
    return {
      navBtns: Array.from(document.querySelectorAll('#nav [data-view]')).map((x) => x.textContent.trim()),
      bindables: Array.from(document.querySelectorAll('[data-sp-bindable]'))
        .map((x) => x.getAttribute('data-sp-database-id')),
      title: (document.querySelector('#viewTitle') || {}).textContent,
      desc: (document.querySelector('#viewDesc') || {}).textContent,
      len: txt.length,
      head: txt.slice(0, 900),
    };
  });
  console.log(JSON.stringify({ ...res, errors: errs.slice(0, 6) }, null, 1));
  await p.screenshot({ path: path.join(D, 'review_view.png'), fullPage: false });
  await b.close();
})();
