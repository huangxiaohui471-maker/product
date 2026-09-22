// 逐条抓 FastMoss 商品详情页的「评分 / 评论数」
// 用法: node fm_rating_fetch.js [limit] [outFile] [cdpPort]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const LIMIT = parseInt(process.argv[2] || '5', 10);
const OUTFILE = process.argv[3] || 'fastmoss_rating.json';
const D = path.join(__dirname, 'data');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// SageSurf 的 CDP 端口每次启动都会变 → 现场用 lsof 找，再用 /json/version 确认
async function findCdpPort() {
  if (process.argv[4]) return process.argv[4];
  if (process.env.CDP_PORT) return process.env.CDP_PORT;
  let out = '';
  try {
    out = execSync("lsof -nP -iTCP -sTCP:LISTEN | grep -i sagesurf", { encoding: 'utf8' });
  } catch (e) { /* 没装/没起 */ }
  const ports = [...new Set((out.match(/:(\d{4,5})\s+\(LISTEN\)/g) || [])
    .map((s) => s.match(/:(\d+)/)[1]))];
  for (const p of ports) {
    try {
      const r = await fetch('http://127.0.0.1:' + p + '/json/version');
      if (r.ok) { const j = await r.json(); if (j.webSocketDebuggerUrl) return p; }
    } catch (e) { /* 下一个 */ }
  }
  return '65362';
}

// 汇总所有待补的商品 id（按销量降序）
const ids = [];
for (const f of ['fastmoss_sales_fiber.json', 'fastmoss_new_fiber.json']) {
  const d = JSON.parse(fs.readFileSync(path.join(D, f), 'utf8'));
  for (const r of d.rows) {
    if (r.sold_count) ids.push({ id: String(r.product_id), sold: r.sold_count });
    else ids.push({ id: String(r.product_id), sold: 0 });
  }
}
ids.sort((a, b) => b.sold - a.sold);
const uniq = [];
const seen = new Set();
for (const x of ids) { if (!seen.has(x.id)) { seen.add(x.id); uniq.push(x); } }
const targets = uniq.slice(0, LIMIT);
console.log(`待抓 ${targets.length} 条（总 ${uniq.length}）`);

const EXTRACT = `(function(){
  var t = document.body ? document.body.innerText : '';
  var m1 = t.match(/([0-5](?:\\.\\d)?)\\s*\\/\\s*5/);
  var m2 = t.match(/评论数[:：]?\\s*([\\d.]+\\s*[万亿]?)/);
  return JSON.stringify({
    rating: m1 ? parseFloat(m1[1]) : null,
    reviewText: m2 ? m2[1].replace(/\\s/g, '') : null,
    url: location.href
  });
})()`;

function parseCn(s) {
  if (!s) return null;
  const m = String(s).match(/^([\d.]+)(万|亿)?$/);
  if (!m) return null;
  let v = parseFloat(m[1]);
  if (m[2] === '万') v *= 10000;
  if (m[2] === '亿') v *= 100000000;
  return Math.round(v);
}

(async () => {
  const port = await findCdpPort();
  console.log('CDP 端口 ' + port);
  const b = await chromium.connectOverCDP('http://127.0.0.1:' + port);
  const ctx = b.contexts()[0];
  const p = await ctx.newPage();
  const out = {};
  const t0 = Date.now();
  for (let i = 0; i < targets.length; i++) {
    const id = targets[i].id;
    try {
      await p.goto('https://www.fastmoss.com/zh/e-commerce/detail/' + id, { waitUntil: 'domcontentloaded', timeout: 30000 });
      let got = null;
      for (let k = 0; k < 6; k++) {
        await sleep(1200);
        const raw = await p.evaluate(EXTRACT);
        const o = typeof raw === 'string' ? JSON.parse(raw) : raw;
        if (o && o.rating != null) { got = o; break; }
      }
      out[id] = got ? { rating: got.rating, reviews: parseCn(got.reviewText), reviewText: got.reviewText } : { rating: null, reviews: null };
      console.log(`${i + 1}/${targets.length} ${id} -> 评分 ${out[id].rating} / 评论 ${out[id].reviews} (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
    } catch (e) {
      out[id] = { rating: null, reviews: null, err: String(e).slice(0, 80) };
      console.log(`${i + 1}/${targets.length} ${id} ERR ${String(e).slice(0, 60)}`);
    }
  }
  fs.writeFileSync(path.join(D, OUTFILE), JSON.stringify(out, null, 1), 'utf8');
  const ok = Object.values(out).filter((x) => x.rating != null).length;
  console.log(`完成：${ok} 条有评分 / 共 ${Object.keys(out).length} 条，用时 ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  await p.close();
  // CDP 连的是用户正在用的 SageSurf 浏览器 → 只关自己开的标签页，
  // 用 process.exit 收尾，避免误关用户整个浏览器会话
  process.exit(0);
})();
