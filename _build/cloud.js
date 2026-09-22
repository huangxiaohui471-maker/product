const { chromium } = require('playwright-core');
const fs = require('fs');
const F = 'file:///Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/%E7%BE%8E%E5%A6%86%E6%83%85%E6%8A%A5%E5%8F%B0.html';
const sch = {
  SByOmCvTOwY3Ae700nplNF: JSON.parse(fs.readFileSync('_build/sch_intel.json','utf8')),
  qHCJ3Y0oFm8Q3GGMxEjVWv: JSON.parse(fs.readFileSync('_build/sch_content.json','utf8')),
  uuAoD57OB4hm0O9WGcCvDV: JSON.parse(fs.readFileSync('_build/sch_review.json','utf8')),
  fkttmXeeL5yZEHYsmCgCPb: JSON.parse(fs.readFileSync('_build/sch_source.json','utf8'))
};
(async () => {
  const browser = await chromium.launch({ channel:'chrome', args:['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport:{width:1440,height:940} });
  await ctx.addInitScript(({sch}) => {
    // 造 260 条情报（>1 页，验证翻页）+ 其他表若干；select 故意存“选项 ID”，验证 id→文本映射
    const opt = (t, id) => ({ text: t, id: id });
    const mk = (dbid, n) => {
      const out = [];
      for (let i = 0; i < n; i++) out.push({ _id: 'r' + dbid + i, '标题': '云数据情报 ' + (i+1),
        '情报类型': i%2 ? 'I7F6PCCRqGnX' : 'xqeRKJBhCrqd', '来源平台': 'Y2fCnKtx0lrM', '区域': 'BUHdblOZD1qz',
        '状态': 'VDHxRyK0oFXp', '热度': 100 + i, '拆解笔记': '云数据拆解 ' + (i+1), '采集日期': '2026-09-19' });
      return out;
    };
    const store = {
      SByOmCvTOwY3Ae700nplNF: mk('a', 260),
      qHCJ3Y0oFm8Q3GGMxEjVWv: [{ _id:'c1','选题标题':'云端选题A','状态':'oSRCioKi4RkJ','优先级':'Yha4SjKcfe1p','发布平台':'jgqHb1DvJ9bO','计划发布日期':'2026-09-16','正文提纲':'云端提纲' }],
      uuAoD57OB4hm0O9WGcCvDV: [{ _id:'v1','内容标题':'云端复盘A','平台':'VVgZX9ZDIipm','发布日期':'2026-09-16','阅读播放':20000,'点赞':800,'收藏':500,'评论':70,'复盘结论':'云端结论' }],
      fkttmXeeL5yZEHYsmCgCPb: [{ _id:'s1','信息源名称':'云端源A','类型':'npsKDUaHXkAL','覆盖地址':null,'覆盖区域':'17UPh7AZAbMV','更新频率':'BtkSAzqzfLdP','状态':'hrlRqMArVdIK','备注':'云端备注' }]
    };
    const calls = [];
    window.__CALLS__ = calls;
    window.__SMART_PAGE__ = { database: {
      getSchema: (p) => { calls.push(['getSchema', p.databaseId]); return Promise.resolve(sch[p.databaseId]); },
      query: (p) => {
        calls.push(['query', p.databaseId, p.startCursor || null]);
        const rows = store[p.databaseId] || [];
        const size = p.pageSize || 50;
        const start = p.startCursor ? Number(p.startCursor) : 0;
        const page = rows.slice(start, start + size);
        const next = start + size;
        return Promise.resolve({ results: page, nextCursor: next < rows.length ? String(next) : null, hasMore: next < rows.length });
      },
      addRecord: (p) => { calls.push(['add', p.databaseId, p.properties]); return Promise.resolve({ id:'new1' }); },
      updateRecord: (p) => { calls.push(['update', p.databaseId, p.recordId, p.properties]); return Promise.resolve({ id:p.recordId }); },
      deleteRecord: (p) => { calls.push(['delete', p.databaseId, p.recordId]); return Promise.resolve({}); },
      onUpdated: () => { calls.push(['onUpdated']); }
    }};
  }, { sch });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type()==='error') errs.push('C:' + m.text()); });
  await page.goto(F);
  await page.waitForTimeout(2500);

  const r = await page.evaluate(() => {
    const tags = Array.from(document.querySelectorAll('#contentBody .tag')).map(e => e.textContent);
    const iTags = Array.from(document.querySelectorAll('#intelBody .card .tag')).slice(0,4).map(e => e.textContent);
    return {
      sync: document.querySelector('#syncText').textContent,
      banner: document.querySelector('#offBanner').classList.contains('hide'),
      navCounts: Array.from(document.querySelectorAll('.nav-count')).map(e => e.textContent),
      cards: document.querySelectorAll('#intelBody .card').length,
      firstCard: document.querySelector('#intelBody .card-title').textContent,
      intelTags: iTags,
      todayRows: document.querySelectorAll('#todayList .today-row').length,
      todayMeta: Array.from(document.querySelectorAll('#todayList .today-meta')).map(e => e.textContent.trim()),
      kpiFirst: document.querySelector('#reviewBody .kpi-v').textContent,
      bars: Array.from(document.querySelectorAll('#reviewBody .bar-name')).map(e => e.textContent),
      srcRow: document.querySelector('#sourceBody .row-title') ? document.querySelector('#sourceBody .row-title').textContent : '',
      bind: document.querySelectorAll('[data-sp-bindable="database"]').length
    };
  });
  console.log('CLOUD ' + JSON.stringify(r, null, 1));
  await page.screenshot({ path:'_build/shot_cloud.png', fullPage:false });

  // 写操作是否带上正确的 databaseId
  const c1 = await page.evaluate(() => window.__CALLS__.filter(c => c[0]==='query').length);
  console.log('QUERY_CALLS ' + c1);
  await page.click('#btnNew');
  await page.waitForTimeout(300);
  await page.fill('[data-f="标题"]','云写入验证');
  await page.click('[data-of="情报类型"][data-opt="法规政策"]');
  await page.waitForTimeout(350);
  await page.click('#formSave');
  await page.waitForTimeout(900);
  const addCall = await page.evaluate(() => window.__CALLS__.filter(c => c[0]==='add').map(c => ({ db:c[1], props:c[2] })));
  console.log('ADD ' + JSON.stringify(addCall));
  console.log('ERRORS ' + JSON.stringify(errs.slice(0,5)));
  await browser.close();
})();
