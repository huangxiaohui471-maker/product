/* 公开发布验证：打开稳定公开地址 + 实际发布产物，确认可正常加载、无 NoSuchKey、V12 关键特性在位 */
const { chromium } = require('playwright');

const STABLE = 'https://workbuddy.link/p/lMO9EIAM8o5cIwqudwUDr1';
const ARTIFACT = 'https://workbuddy-space-static.codebuddy.work/page/lMO9EIAM8o5cIwqudwUDr1/12/index.html';

const KEYS = ['boardRankDataOf', 'boardC2Stats', 'boardInsightsOf', 'rank-sec', 'fltLayer',
  'CURRENCY_BY_COUNTRY', 'rankPageOf'];

(async () => {
  const PROXY = process.env.HTTPS_PROXY || process.env.https_proxy || 'http://127.0.0.1:7897';
  const b = await chromium.launch({ proxy: { server: PROXY } });
  const out = { proxyUsed: PROXY };

  /* A) 稳定公开地址：壳页 + 内嵌产物能否渲染 */
  const p1 = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs1 = [];
  p1.on('pageerror', e => errs1.push(String(e).slice(0, 140)));
  p1.on('console', m => { if (m.type() === 'error') errs1.push('console: ' + m.text().slice(0, 140)); });
  const r1 = await p1.goto(STABLE, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await p1.waitForTimeout(6000);
  out.stable = {
    http: r1 && r1.status(),
    finalUrl: p1.url(),
    hasShell: await p1.evaluate(() => !!document.querySelector('#root') || document.body.innerHTML.length > 200),
    errs: errs1.slice(0, 4)
  };
  await p1.close();

  /* B) 实际发布产物：直接加载并检查渲染与关键符号 */
  const p2 = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs2 = [];
  p2.on('pageerror', e => errs2.push(String(e).slice(0, 140)));
  p2.on('console', m => { if (m.type() === 'error') errs2.push('console: ' + m.text().slice(0, 140)); });
  /* 平台注入的 /page/page_comm/inject.js 在静态域下会挂住 DOMContentLoaded；验证结构时中止该请求 */
  await p2.route('**/page_comm/inject.js', r => r.abort());
  /* 与本地验收同构的数据 mock：让页面走「有数据」分支而不是空态 */
  const fs = require('fs'), path = require('path');
  const D = path.join(__dirname, 'data');
  const NUM = new Set(['价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分', '评价数',
    '预估成本', 'SKU 数']);
  const SEL = new Set(['品类', '数据来源', '所属市场', '国家/地区', '剂型', '技术壁垒', '评价来源',
    '备案路径', '宣称支撑难度', '与我方价格带匹配', '与我方客群匹配', '与我方 SKU 重合度',
    '决策状态', '数据标记', '二级类目', '三级类目']);
  const ai = JSON.parse(fs.readFileSync(path.join(D, 'records_cat_400.json'), 'utf8'));
  const recs = (ai.records || ai);
  const cloudSnap = JSON.parse(fs.readFileSync(path.join(__dirname, 'cloud_platform.json'), 'utf8'));
  const byPid = {};
  for (const c of (cloudSnap.results || cloudSnap)) if (c['商品ID']) byPid[String(c['商品ID'])] = c;
  const NEWF = ['SKU 数', '备案/许可号', '法规合规声明', '数据标记', '二级类目', '三级类目', '榜单排名'];
  for (const rec of recs) {
    const c = byPid[String(rec['商品ID'] || '')];
    if (c) for (const k of NEWF) if (c[k] !== undefined && c[k] !== null && c[k] !== '') rec[k] = c[k];
  }
  const rows = recs.map((rec, i) => {
    const o = {};
    for (const [k, v] of Object.entries(rec)) {
      if (v === null || v === '' || v === undefined || k.startsWith('_')) continue;
      if (NUM.has(k)) o[k] = { number: Number(v) };
      else if (SEL.has(k)) o[k] = { select: String(v) };
      else if (k === '上市日期') o[k] = { date: String(v).slice(0, 19) };
      else o[k] = { text: String(v) };
    }
    o._id = 'p' + i;
    return o;
  });
  await p2.addInitScript(`window.__SMART_PAGE__ = { database: {
      query: function(){ return Promise.resolve({ results: window.__PR, nextCursor: null, hasMore: false }); },
      getSchema: function(){ return Promise.resolve({ properties: [] }); },
      addRecord: function(){ return Promise.resolve({ recordId: 'mock-new' }); },
      deleteRecord: function(){ return Promise.resolve({ ok: true }); },
      onUpdated: function(){ return function(){}; } } };
    window.__PR = ${JSON.stringify(rows)};`);
  const r2 = await p2.goto(ARTIFACT, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await p2.waitForTimeout(3500);
  await p2.evaluate(() => { if (window.refreshAll) { try { refreshAll(); } catch (e) {} } });
  await p2.waitForTimeout(2500);
  const probe = await p2.evaluate((keys) => {
    const html = document.documentElement.outerHTML;
    const o = { noSuchKey: /NoSuchKey|AccessDenied/i.test(html), keys: {} };
    for (const k of keys) o.keys[k] = html.indexOf(k) >= 0;
    o.hasGlobalBoard = html.indexOf('全球看板') >= 0;
    o.hasRankCenter = html.indexOf('榜单中心') >= 0;
    return o;
  }, KEYS);
  /* 切到看板 / 榜单，确认渲染无报错 */
  const render = await p2.evaluate(() => {
    const res = {};
    const bd = document.querySelector('[data-view="board"]');
    if (bd) { bd.click(); res.board = /全球看板/.test(document.querySelector('#view').textContent); }
    const rk = document.querySelector('[data-view="rank"]');
    if (rk) { rk.click(); const t = document.querySelector('#view').textContent; res.rank = /榜/.test(t); res.rankSec = !!document.querySelector('.rank-sec'); }
    return res;
  });
  await p2.waitForTimeout(800);
  out.artifact = {
    http: r2 && r2.status(),
    bytes: (await p2.content()).length,
    probe,
    render,
    errs: errs2.slice(0, 4)
  };
  await p2.close();
  await b.close();

  console.log(JSON.stringify(out, null, 2));
  const ok = out.stable.http === 200 && out.artifact.http === 200 && !out.artifact.probe.noSuchKey &&
    out.artifact.render.rankSec === true && out.artifact.probe.hasGlobalBoard && out.artifact.probe.hasRankCenter;
  console.log(ok ? '\nPUBLISH_VERIFY_OK' : '\nPUBLISH_VERIFY_FAIL');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('异常:', e); process.exit(2); });
