// 抓 FastMoss 完整筛选元数据（类目树 + 国家表），固化为本地 JSON
// 用法: node fm_cat_fetch.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const PORT = process.env.CDP_PORT || '65362';
const D = path.join(__dirname, 'data');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const b = await chromium.connectOverCDP('http://127.0.0.1:' + PORT);
  const ctx = b.contexts()[0];
  let page = ctx.pages().find((p) => /fastmoss\.com/.test(p.url()));
  if (!page) {
    page = await ctx.newPage();
    await page.goto('https://www.fastmoss.com/zh/e-commerce/saleslist?page=1&l1_cid=14', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
    await sleep(8000);
  }

  const raw = await page.evaluate(async () => {
    const ts = Math.floor(Date.now() / 1000);
    const rnd = () => String(Math.floor(Math.random() * 90000000) + 10000000);
    const r = await fetch('/api/live/filterInfo?_time=' + ts + '&cnonce=' + rnd(), { credentials: 'include' });
    const j = await r.json();
    return JSON.stringify(j);
  });
  const j = JSON.parse(raw);
  const d = j.data || j;

  fs.mkdirSync(D, { recursive: true });
  fs.writeFileSync(path.join(D, 'fm_cat_tree_raw.json'), JSON.stringify(d, null, 1), 'utf8');

  const flatten = (nodes, lv, out) => {
    (nodes || []).forEach((n) => {
      out.push({ level: lv, cid: String(n.cid || n.c_code || ''), name: String(n.name || n.c_name || '').replace(/\t/g, ' ').trim() });
      const kids = n.children || n.sub;
      if (kids) flatten(kids, lv + 1, out);
    });
  };
  const tree = [];
  d.product_category.forEach((c) => {
    const node = { cid: String(c.c_code), name: c.c_name, rank: c.rank, children: [] };
    (c.sub || []).forEach((s2) => {
      const n2 = { cid: String(s2.c_code), name: s2.c_name, children: [] };
      (s2.sub || []).forEach((s3) => n2.children.push({ cid: String(s3.c_code), name: String(s3.c_name || '').replace(/\t/g, ' ').trim() }));
      node.children.push(n2);
    });
    tree.push(node);
  });

  const regions = (d.region || []).map((r) => ({ code: r.region_code, name: r.region_name, zh: r.region_code_name }));
  const dateTypes = d.date_type || [];

  const out = {
    source: 'FastMoss /api/live/filterInfo',
    fetchedAt: new Date().toISOString(),
    regions,
    dateTypes,
    tree,
  };
  fs.writeFileSync(path.join(D, 'fm_cat_tree.json'), JSON.stringify(out, null, 1), 'utf8');

  const flat = [];
  flatten(tree, 1, flat);
  const byLv = {};
  flat.forEach((f) => { byLv[f.level] = (byLv[f.level] || 0) + 1; });
  console.log('类目总数 ' + flat.length + ' | 分布 ' + JSON.stringify(byLv));
  console.log('一级 ' + tree.length + ' 个，国家 ' + regions.length + ' 个');
  const bpc = tree.find((x) => x.cid === '14');
  console.log('美妆个护 Beauty & Personal Care：二级 ' + bpc.children.length + " 个，三级 " + bpc.children.reduce((a, c) => a + c.children.length, 0) + ' 个');
  console.log('SAVED data/fm_cat_tree.json');
  await b.close().catch(() => {});
  process.exit(0);
})();
