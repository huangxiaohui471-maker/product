/* 验证「只看真实」开关：开启后 KPI / 洞察规则体检应只由真实数据驱动 */
const { chromium } = require('playwright');
const fs = require('fs');
const DIR = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47';
const F = 'file://' + encodeURIComponent(DIR + '/全球选品平台.html').replace(/%2F/g, '/');
const schema = JSON.parse(fs.readFileSync(DIR + '/_build/schema_platform.json', 'utf8'));
const cloud = JSON.parse(fs.readFileSync(DIR + '/_build/data/cloud_after_v3.json', 'utf8'));
const rows = Array.isArray(cloud) ? cloud : (cloud.results || []);

(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  for (const mode of ['all', 'realOnly']) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    await ctx.addInitScript(({ schema, rows }) => {
      window.__SMART_PAGE__ = {
        database: {
          getSchema: () => Promise.resolve(schema),
          query: () => Promise.resolve({ results: rows, nextCursor: null, hasMore: false }),
          addRecord: () => Promise.resolve({ id: 'n1' }),
          updateRecord: () => Promise.resolve({}),
          deleteRecord: () => Promise.resolve({}),
          onUpdated: () => { }
        }
      };
    }, { schema, rows });
    const page = await ctx.newPage();
    page.on('pageerror', e => errs.push(mode + ' PAGEERROR ' + e.message));
    page.on('console', m => { if (m.type() === 'error') errs.push(mode + ' C:' + m.text()); });
    await page.goto(F);
    await page.waitForTimeout(2400);

    if (mode === 'realOnly') {
      const ok = await page.evaluate(() => {
        const b = [...document.querySelectorAll('#chips button')].find(e => (e.innerText || '').trim() === '只看真实');
        if (b) { b.click(); return true; }
        return false;
      });
      await page.waitForTimeout(1200);
      console.log('  点击「只看真实」=' + ok);
    }

    // 机会洞察
    await page.evaluate(() => {
      const b = [...document.querySelectorAll('#nav *')].find(e => (e.innerText || '').trim() === '机会洞察');
      if (b) b.click();
    });
    await page.waitForTimeout(1500);
    const r = await page.evaluate(() => {
      const t = (document.body.innerText || '').replace(/\s+/g, ' ');
      const m = t.match(/(\d+) 个商品/);
      const mh = t.match(/引擎体检：([^。]+。)/);
      const hits = [...t.matchAll(/命中 (\d+) 个/g)].map(x => x[1]);
      const skip = [...t.matchAll(/已跳过/g)].length;
      return { n: m ? m[1] : '?', health: mh ? mh[1] : '', hits: hits, skipLines: skip, sample: t.slice(0, 200) };
    });
    console.log('[' + mode + '] 商品数=' + r.n + ' | 引擎体检=' + r.health);
    console.log('        各规则命中=' + JSON.stringify(r.hits));
    await ctx.close();
  }
  console.log('ERRORS ' + JSON.stringify(errs.slice(0, 8)));
  await browser.close();
})();
