#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面 v10：设计令牌升级 + Hero 情报卡（高级 + 情绪价值）+ 三个新字段 + 增速展示抗极端值。

改动清单（每处都要求唯一命中，命中数 != 1 即中止）：
  A. :root 设计令牌升级（分层阴影 / 圆角节奏 / Hero 渐变）
  B. 追加 v10 CSS（Hero / 卡片精修 / 进入动效 / 移动端）
  C. FIELDS 新增 SKU 数（商品主数据）
  D. FIELDS 新增 备案/许可号、法规合规声明（可行性）
  E. 新增 heroHtml / heroStat / medGrowthOf / animateCounters
  F. RENDER.board 顶部插入 Hero
  G. renderView 增加视图切换时的入场动效开关
  H. refreshAll 触发数字滚动
  I. 市场机会列表改显示中位数（均值会被低基数新品拉爆）+ 标注
  J. 市场机会 eval 行同步改中位数
  K. 增速品类列表改显示中位数 + 标注

用法：
  python3 patch_page_v10.py                 # dry-run，只做命中检查
  python3 patch_page_v10.py --apply --target /path/to/index.html
"""
from __future__ import annotations

import argparse
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET = os.path.join(BASE, '..', '全球选品平台.html')

# ---------------------------------------------------------------- A. 设计令牌
ROOT_OLD = """:root{
  --bg:#F5F5F7;--surface:#FFFFFF;--surface-2:#FAFAFC;
  --line:#E6E6EA;--line-2:#F0F0F3;
  --text:#1D1D1F;--sub:#6E6E73;--hint:#8E8E93;
  --blue:#0071E3;--blue-soft:#EAF3FE;--blue-deep:#0058B0;
  --up:#D93A2B;--up-soft:#FDEDEB;--down:#1B8A4B;--down-soft:#EAF6EE;
  --amber:#B26A00;--amber-soft:#FFF4E5;--purple:#6E4BD1;--purple-soft:#F1EDFC;
  --teal:#0E7C6B;--teal-soft:#E6F5F2;
  --r:12px;--r-s:8px;--r-l:16px;
  --sh:0 1px 2px rgba(0,0,0,.04);
  --side-w:212px;
}"""

ROOT_NEW = """:root{
  --bg:#F4F4F7;--surface:#FFFFFF;--surface-2:#FAFAFC;
  --line:#E7E7EC;--line-2:#F1F1F5;
  --text:#17171B;--sub:#5E5F67;--hint:#8A8B93;
  --blue:#0071E3;--blue-soft:#EAF3FE;--blue-deep:#0058B0;
  --up:#D93A2B;--up-soft:#FDEDEB;--down:#12855A;--down-soft:#E9F7EF;
  --amber:#A86300;--amber-soft:#FEF3E2;--purple:#6A45D0;--purple-soft:#F1EDFC;
  --teal:#0C7A6A;--teal-soft:#E5F5F1;
  --r:12px;--r-s:9px;--r-l:16px;--r-xl:22px;
  --sh:0 1px 2px rgba(16,24,40,.05);
  --sh-1:0 1px 2px rgba(16,24,40,.04),0 1px 3px rgba(16,24,40,.05);
  --sh-2:0 10px 26px -12px rgba(16,24,40,.22),0 2px 6px rgba(16,24,40,.05);
  --sh-3:0 26px 60px -26px rgba(10,16,48,.62),0 2px 10px rgba(10,16,48,.12);
  --grad-hero:linear-gradient(142deg,#0B1124 0%,#141A3B 46%,#201540 100%);
  --side-w:212px;
}"""

# ---------------------------------------------------------------- B. 追加 CSS
CSS_ADD = """
/* ===== v10 · 视觉精修：把「工具」做成「有人替你盯着」的台面 ===== */

/* ---- 数字与标题的排版质感 ---- */
body{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}
.kpi .vl{font-size:24px;font-weight:600;letter-spacing:-.015em;margin-top:6px}
.sec-hd h2{letter-spacing:-.012em;font-weight:600}
.topbar-title h1{letter-spacing:-.015em;font-weight:600}
.card{box-shadow:var(--sh-1);transition:box-shadow .22s ease,transform .22s ease,border-color .22s ease}
.card:hover{box-shadow:var(--sh-2);border-color:#DFDFE6}
.card.kpi:hover{transform:translateY(-1px)}
.chip{transition:background .18s,border-color .18s,color .18s}
.chip:not(.on):hover{background:var(--surface-2);border-color:#D8D8E0}
.mini{transition:background .18s,border-color .18s,box-shadow .18s}
.mini:hover{box-shadow:var(--sh-1)}
.cmp-r{transition:background .16s}
.cmp-r:hover{background:var(--surface-2)}
.nav-item{transition:background .18s,color .18s}
.topbar{background:rgba(246,246,248,.76);backdrop-filter:saturate(190%) blur(22px);-webkit-backdrop-filter:saturate(190%) blur(22px)}
.topbar-title h1+p{max-width:52em}

/* ---- 增速标注：中位数为主，均值被极端值拉高时如实标出 ---- */
.ins-row .vv .skew{font-size:10.5px;font-weight:400;color:var(--hint);margin-left:5px;
  padding:1px 5px;border-radius:5px;background:var(--surface-2);border:1px solid var(--line-2)}

/* ---- Hero 情报卡：浅色页面里唯一的重色块，负责第一眼的情绪 ---- */
.hero{
  position:relative;overflow:hidden;isolation:isolate;
  margin-bottom:22px;padding:26px 28px 24px;border-radius:var(--r-xl);
  color:#fff;background:var(--grad-hero);box-shadow:var(--sh-3);
}
.hero::before{
  content:'';position:absolute;inset:0;z-index:-1;
  background:
    radial-gradient(56% 88% at 4% -12%,rgba(64,110,255,.66),rgba(64,110,255,0) 62%),
    radial-gradient(48% 78% at 98% 2%,rgba(146,78,255,.52),rgba(146,78,255,0) 60%),
    radial-gradient(40% 60% at 62% 118%,rgba(0,196,168,.28),rgba(0,196,168,0) 62%);
}
.hero::after{
  content:'';position:absolute;inset:0;z-index:-1;opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,.055) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.055) 1px,transparent 1px);
  background-size:40px 40px;
  -webkit-mask-image:radial-gradient(78% 82% at 74% 0%,#000,transparent 72%);
  mask-image:radial-gradient(78% 82% at 74% 0%,#000,transparent 72%);
}
.hero-in{display:flex;gap:28px;align-items:flex-end;flex-wrap:wrap}
.hero-l{flex:1 1 330px;min-width:0}
.hero-r{display:flex;gap:10px;flex:0 1 auto;flex-wrap:wrap}
.hero-eye{display:inline-flex;align-items:center;gap:8px;font-size:11px;font-weight:500;
  letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.6)}
.hero-eye i{width:6px;height:6px;border-radius:50%;background:#5CE1A6;box-shadow:0 0 0 4px rgba(92,225,166,.14);animation:heroPulse 2.6s ease-in-out infinite}
@keyframes heroPulse{0%,100%{box-shadow:0 0 0 3px rgba(92,225,166,.16)}50%{box-shadow:0 0 0 7px rgba(92,225,166,.04)}}
.hero-h{margin:12px 0 0;font-size:23px;line-height:1.44;font-weight:500;letter-spacing:-.012em;max-width:26em}
.hero-h em{font-style:normal;font-weight:600;
  background:linear-gradient(94deg,#9DBAFF,#C9A9FF 58%,#FFD9A6);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.hero-p{margin:11px 0 0;font-size:12.5px;line-height:1.78;color:rgba(255,255,255,.66);max-width:40em}
.hero-p b{color:rgba(255,255,255,.92);font-weight:600}
.hero-foot{margin-top:9px;font-size:11.5px;color:rgba(255,255,255,.5)}
.hero-btns{display:flex;gap:9px;margin-top:18px;flex-wrap:wrap}
.hero-btn{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 17px;
  border-radius:11px;font-size:13px;font-weight:500;color:#fff;
  background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  transition:background .18s,border-color .18s,transform .18s}
.hero-btn:hover{background:rgba(255,255,255,.18)}
.hero-btn:active{transform:scale(.98)}
.hero-btn.pri{background:#fff;border-color:#fff;color:#101534;font-weight:600}
.hero-btn.pri:hover{background:#EDF1FF}
.hero-stat{flex:0 0 auto;min-width:116px;padding:14px 16px 13px;border-radius:16px;
  background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.13);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
.hero-stat .l{font-size:11px;color:rgba(255,255,255,.58);letter-spacing:.02em}
.hero-stat .v{margin-top:6px;font-size:30px;font-weight:600;line-height:1.1;letter-spacing:-.025em;
  color:#fff;text-shadow:0 2px 20px rgba(150,180,255,.45)}
.hero-stat .v small{font-size:12px;font-weight:400;margin-left:3px;color:rgba(255,255,255,.6)}
.hero-stat .f{margin-top:5px;font-size:11px;color:rgba(255,255,255,.42)}

/* ---- 进入动效：只在切换视图时播一次，筛选时不闪 ---- */
@keyframes riseIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes heroIn{from{opacity:0;transform:translateY(16px) scale(.986)}to{opacity:1;transform:none}}
#view.anim > .hero{animation:heroIn .62s cubic-bezier(.16,1,.3,1) both}
#view.anim > .sec{animation:riseIn .46s cubic-bezier(.16,1,.3,1) both}
#view.anim > .sec:nth-child(1){animation-delay:.03s}
#view.anim > .sec:nth-child(2){animation-delay:.07s}
#view.anim > .sec:nth-child(3){animation-delay:.11s}
#view.anim > .sec:nth-child(4){animation-delay:.15s}
#view.anim > .sec:nth-child(5){animation-delay:.19s}
#view.anim > .sec:nth-child(6){animation-delay:.23s}
#view.anim > .sec:nth-child(7){animation-delay:.27s}
#view.anim > .sec:nth-child(8){animation-delay:.3s}
#view.anim > .sec:nth-child(n+9){animation-delay:.33s}
@media (prefers-reduced-motion:reduce){
  #view.anim > .hero,#view.anim > .sec,.hero-eye i{animation:none!important}
  .card,.hero-btn{transition:none!important}
}

/* ---- 移动端 ---- */
@media (max-width:860px){
  .hero{padding:20px 18px 18px;border-radius:18px}
  .hero-h{font-size:19px;line-height:1.5}
  .hero-in{gap:16px}
  .hero-r{width:100%;gap:8px}
  .hero-stat{flex:1 1 0;min-width:0;padding:11px 12px 10px;border-radius:13px}
  .hero-stat .v{font-size:22px}
  .hero-stat .f{display:none}
  .hero-btns{gap:8px}
  .hero-btn{flex:1 1 45%}
  .ins-row .vv .skew{display:none}
}
"""

# ---------------------------------------------------------------- C. SKU 数
SKU_OLD = "  { n: '上市日期', t: 'date', g: '商品主数据', src: 'auto' },"
SKU_NEW = ("  { n: '上市日期', t: 'date', g: '商品主数据', src: 'auto' },\n"
           "  { n: 'SKU 数', t: 'number', g: '商品主数据', src: 'auto',"
           " hint: 'TikTok 商品规格数（容量/色号/组合装等），来自 TikHub 商品详情' },")

# ---------------------------------------------------------------- D. 法规字段
LEGAL_OLD = ("  { n: '宣称支撑难度', t: 'select', g: '可行性', src: 'manual',"
             " opts: ['无需评价', '需文献资料', '需人体功效试验'] },")
LEGAL_NEW = ("  { n: '宣称支撑难度', t: 'select', g: '可行性', src: 'manual',"
             " opts: ['无需评价', '需文献资料', '需人体功效试验'] },\n"
             "  { n: '备案/许可号', t: 'text', g: '可行性', src: 'auto',"
             " hint: '目标市场官方备案或注册号原文（印尼 BPOM、菲律宾 FDA 等），来自 TikTok 商品详情——平台没写就留空' },\n"
             "  { n: '法规合规声明', t: 'text', g: '可行性', src: 'auto',"
             " hint: '法规类声明原文（如美国 CA Prop 65 致癌物/生殖毒性），照录平台值不推测' },")

# ---------------------------------------------------------------- E. Hero 代码
HERO_ANCHOR = "RENDER.board = function () {"

HERO_JS = r"""/* ---- v10 · Hero 情报卡：把「一堆图表」翻译成「今天该先看什么」 ----
   只用已算好的纯函数（kpiOf / insightsOf），不调用其它渲染函数。

   为什么用中位数不用均值：真实数据里存在「低基数新品」——
   例如一条印尼唇妆的环比是 57725%，一条品就能把整格均值拉到 8000% 以上。
   均值在这里既不可信也不好读，中位数才代表这一格的常态水位。 ---- */
function medOf(vals) {
  var v = [], i;
  for (i = 0; i < vals.length; i++) {
    if (vals[i] !== null && vals[i] !== undefined && !isNaN(vals[i])) v.push(vals[i]);
  }
  if (!v.length) return null;
  v.sort(function (a, b) { return a - b; });
  var m = Math.floor(v.length / 2);
  var r = v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  return Math.round(r * 10) / 10;
}
function medGrowthOf(rows) {
  var v = [], i;
  for (i = 0; i < (rows || []).length; i++) {
    var g = numField(rows[i], '环比增速');
    if (g !== null) v.push(g);
  }
  return medOf(v);
}
function medGrowthOfC2(list, c2) {
  var v = [], i;
  for (i = 0; i < list.length; i++) {
    if (txtOf(list[i], '二级类目') !== c2) continue;
    var g = numField(list[i], '环比增速');
    if (g !== null) v.push(g);
  }
  return medOf(v);
}
/* 截尾均值：去掉两端各 10% 再平均。中位数太保守（一半商品持平 → 恒为 0），
   算术平均又被少数爆款拉爆（+288%），截尾均值落在两者之间，最能代表「整体水温」。 */
function trimMean(vals, t) {
  var v = [], i;
  for (i = 0; i < vals.length; i++) {
    if (vals[i] !== null && vals[i] !== undefined && !isNaN(vals[i])) v.push(vals[i]);
  }
  if (!v.length) return null;
  v.sort(function (a, b) { return a - b; });
  var k = Math.floor(v.length * (t || 0.1));
  var s = v.slice(k, v.length - k);
  if (!s.length) s = v;
  var sum = 0;
  for (i = 0; i < s.length; i++) sum += s[i];
  return Math.round(sum / s.length * 10) / 10;
}
function heroStat(label, val, unit, foot) {
  return '<div class="hero-stat"><div class="l">' + esc(label) + '</div>'
    + '<div class="v" data-count="' + val + '" data-unit="' + esc(unit) + '">' + val
    + '<small>' + esc(unit) + '</small></div>'
    + '<div class="f">' + esc(foot) + '</div></div>';
}
function heroHtml(list) {
  var k = kpiOf(list);
  var ins = insightsOf(list);
  var filed = 0, i;
  for (i = 0; i < list.length; i++) {
    if (txtOf(list[i], '备案/许可号') !== '') filed++;
  }

  var line, sub;
  if (ins.mkt.length) {
    var m0 = ins.mkt[0];
    var mg = medGrowthOf(m0.rows);
    line = '<em>' + esc(m0.country) + ' · ' + esc(m0.c2) + '</em> 这一格在集体起量，'
      + m0.n + ' 个品的中位环比 <em>'
      + (mg === null || mg <= 0 ? '普遍为正' : fmtPct(mg)) + '</em>';
    sub = '同一个国家、同一个功能子类里同时冒出这么多上升品，一般不是巧合，'
      + '更像是当地需求在换挡。先把这一格里的品逐个看一遍，比在别处找单点爆款划算。';
  } else if (ins.gcat.length) {
    var g0 = ins.gcat[0];
    var gg = medGrowthOfC2(list, g0.c2);
    line = '<em>' + esc(g0.c2) + '</em> 整条赛道在涨，'
      + (gg !== null && gg > 0 ? '中位环比 <em>' + fmtPct(gg) + '</em>' : '绝大多数样本都在增长');
    sub = '品类级别的普涨比单点爆款更值得跟——前者说明需求在扩大，后者可能只是某个商家在砸钱。';
  } else if (ins.win.length) {
    line = '有 <em>' + ins.win.length + ' 个品</em>环比涨超 60%，值得逐个看';
    sub = '这些品的共性是能反推的：先看它们用了什么成分、打了什么概念，再看价格带落在哪里。';
  } else {
    line = '本期数据还没跑出明显的上升趋势';
    sub = '可以先从「品类与成分库」翻一翻已收录的商品档案，或放宽筛选条件重新看一遍。';
  }

  var foot = '当前范围内 <b>' + k.n + '</b> 个商品样本、覆盖 <b>' + k.markets + '</b> 个市场'
    + (filed ? '，其中 <b>' + filed + '</b> 个能在目标市场查到官方备案号' : '')
    + '。';

  var now = new Date();
  var dateTxt = (now.getMonth() + 1) + ' 月 ' + now.getDate() + ' 日';

  return '<div class="hero"><div class="hero-in">'
    + '<div class="hero-l">'
    + '<span class="hero-eye"><i></i>今日情报 · ' + dateTxt + '</span>'
    + '<h2 class="hero-h">' + line + '</h2>'
    + '<p class="hero-p">' + sub + '</p>'
    + '<p class="hero-p hero-foot">' + foot + '</p>'
    + '<div class="hero-btns">'
    + '<button type="button" class="hero-btn pri" data-view="insight">看全部机会</button>'
    + '<button type="button" class="hero-btn" data-view="lib">翻商品档案</button>'
    + '</div></div>'
    + '<div class="hero-r">'
    + heroStat('上升中', ins.win.length, '个', '环比 ≥ 60%')
    + heroStat('加速赛道', ins.gcat.length, '条', '品类均值 ≥ 80%')
    + heroStat('已备案', filed, '个', '可查官方备案号')
    + '</div></div></div>';
}

/* 数字滚动：只在首次渲染和切换视图时跑，尊重「减少动态效果」偏好 */
function animateCounters() {
  var reduce = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var els = $$('[data-count]');
  for (var i = 0; i < els.length; i++) {
    (function (el) {
      var target = parseFloat(el.getAttribute('data-count')) || 0;
      var unit = el.getAttribute('data-unit') || '';
      var paint = function (v) {
        el.innerHTML = v + (unit ? '<small>' + unit + '</small>' : '');
      };
      if (reduce || !window.requestAnimationFrame) { paint(target); return; }
      var t0 = 0, dur = 760;
      var step = function (ts) {
        if (!t0) t0 = ts;
        var p = Math.min(1, (ts - t0) / dur);
        var e = 1 - Math.pow(1 - p, 3);
        paint(Math.round(target * e));
        if (p < 1) window.requestAnimationFrame(step); else paint(target);
      };
      window.requestAnimationFrame(step);
    })(els[i]);
  }
}

"""

# ---------------------------------------------------------------- F. board 挂钩
HOOK_OLD = """  var k = kpiOf(list);
  var h = '';

  h += '<div class="sec">' + secHd('全局概览'"""
HOOK_NEW = """  var k = kpiOf(list);
  var h = '';
  h += heroHtml(list);

  h += '<div class="sec">' + secHd('全局概览'"""

# ---------------------------------------------------------------- G. renderView
RV_OLD = """function renderView() {
  var v = state.view;"""
RV_NEW = """function renderView() {
  var v = state.view;
  /* 进入动效只在「换视图」时播一次；筛选/搜索重绘不重播，免得闪 */
  var vw = $('#view');
  if (state._lastView !== v) { vw.classList.add('anim'); state._lastView = v; }
  else { vw.classList.remove('anim'); }"""

# ---------------------------------------------------------------- H. refreshAll
RA_OLD = """  renderView();
  bindDb(document);
}"""
RA_NEW = """  renderView();
  animateCounters();
  bindDb(document);
}"""

# ---------------------------------------------------------------- I. 市场机会列表
MKT_OLD = """    for (var mi = 0; mi < Math.min(5, ins.mkt.length); mi++) {
      var mx = ins.mkt[mi];
      mktRows += '<button type="button" class="ins-row" data-f="country" data-v="' + esc(mx.country) + '">'
        + '<span class="nm">[' + esc(mx.country) + '] ' + esc(mx.c2) + '　<small>' + mx.n + ' 个样本</small></span>'
        + '<span class="vv"><span class="' + pctCls(mx.avgGrowth) + '">' + fmtPct(Math.round(mx.avgGrowth)) + '</span></span></button>';
    }"""
MKT_NEW = """    for (var mi = 0; mi < Math.min(5, ins.mkt.length); mi++) {
      var mx = ins.mkt[mi];
      /* 显示中位数：单条低基数新品（如环比 +57725%）能把均值拉爆，
         那样既不可信也不好读。均值偏离中位数 3 倍以上就如实标注。 */
      var mgv = medGrowthOf(mx.rows);
      if (mgv === null) mgv = mx.avgGrowth;
      var mskew = mx.avgGrowth > 0 && mgv > 0 && mx.avgGrowth > mgv * 3;
      mktRows += '<button type="button" class="ins-row" data-f="country" data-v="' + esc(mx.country) + '">'
        + '<span class="nm">[' + esc(mx.country) + '] ' + esc(mx.c2) + '　<small>' + mx.n + ' 个样本</small></span>'
        + '<span class="vv"><span class="' + pctCls(mgv) + '">' + fmtPct(mgv) + '</span>'
        + (mskew ? '<small class="skew">已剔除极端值</small>' : '') + '</span></button>';
    }"""

# ---------------------------------------------------------------- J. 市场机会 eval 行
MKTEV_OLD = """      + (ins.mkt.length ? '　·　最高 <b>' + esc(ins.mkt[0].country) + ' · ' + esc(ins.mkt[0].c2) + '</b> ' + fmtPct(Math.round(ins.mkt[0].avgGrowth)) : ''),"""
MKTEV_NEW = """      + (ins.mkt.length ? '　·　最高 <b>' + esc(ins.mkt[0].country) + ' · ' + esc(ins.mkt[0].c2) + '</b> ' + fmtPct(medGrowthOf(ins.mkt[0].rows)) : ''),"""
MKTRULE_OLD = """    rule: '规则：同一个「国家/地区 × 二级类目」里至少 ' + MKT_MIN_SAMPLE + ' 个样本，且这些样本的平均环比增速 ≥ ' + MKT_MIN_GROWTH + '%。点一行就能把该国家筛出来。'"""
MKTRULE_NEW = """    rule: '规则：同一个「国家/地区 × 二级类目」里至少 ' + MKT_MIN_SAMPLE + ' 个样本，且这些样本的平均环比增速 ≥ ' + MKT_MIN_GROWTH + '%。点一行就能把该国家筛出来。列表里显示的是中位数——个别低基数新品会把均值抬到几千个百分点，中位数更能代表这一格的常态水位。'"""

# ---------------------------------------------------------------- K. 增速品类列表
GCAT_OLD = """    var gx = ins.gcat[gi];
    gcatRows += '<button type="button" class="ins-row" data-f="c2" data-v="' + esc(gx.c2) + '">'
      + '<span class="nm">' + esc(gx.l1) + ' · ' + esc(gx.c2) + '　<small>' + gx.n + ' 个 / ' + gx.c3n + ' 个三级类目</small></span>'
      + '<span class="vv"><span class="' + pctCls(gx.avgGrowth) + '">' + fmtPct(Math.round(gx.avgGrowth)) + '</span> · ' + fmtBig(gx.sales) + '</span></button>';"""
GCAT_NEW = """    var gx = ins.gcat[gi];
    var ggv = medGrowthOfC2(list, gx.c2);
    if (ggv === null) ggv = gx.avgGrowth;
    var gskew = gx.avgGrowth > 0 && ggv > 0 && gx.avgGrowth > ggv * 3;
    gcatRows += '<button type="button" class="ins-row" data-f="c2" data-v="' + esc(gx.c2) + '">'
      + '<span class="nm">' + esc(gx.l1) + ' · ' + esc(gx.c2) + '　<small>' + gx.n + ' 个 / ' + gx.c3n + ' 个三级类目</small></span>'
      + '<span class="vv"><span class="' + pctCls(ggv) + '">' + fmtPct(ggv) + '</span> · ' + fmtBig(gx.sales)
      + (gskew ? '<small class="skew">已剔除极端值</small>' : '') + '</span></button>';"""


# ---------------------------------------------------------------- L. kpiOf 收集中位数/截尾均值
KPI_OLD = """  var n = list.length, gsum = 0, gn = 0, ksum = 0, kn = 0, rsum = 0, rn = 0, sales = 0, mk = [], high = 0;
  for (var i = 0; i < list.length; i++) {
    var r = list[i];
    var g = numField(r, '环比增速'); if (g !== null) { gsum += g; gn++; }"""
KPI_NEW = """  var n = list.length, gsum = 0, gn = 0, ksum = 0, kn = 0, rsum = 0, rn = 0, sales = 0, mk = [], high = 0, gs = [];
  for (var i = 0; i < list.length; i++) {
    var r = list[i];
    var g = numField(r, '环比增速'); if (g !== null) { gsum += g; gn++; gs.push(g); }"""
KPIRET_OLD = """    avgGrowth: gn ? Math.round(gsum / gn * 10) / 10 : null,"""
KPIRET_NEW = """    avgGrowth: gn ? Math.round(gsum / gn * 10) / 10 : null,
    trimGrowth: trimMean(gs),"""

# ---------------------------------------------------------------- M. KPI 卡改截尾均值
KPICARD_OLD = """  h += '<div class="card kpi"><div class="lb">平均环比增速</div><div class="vl ' + pctCls(k.avgGrowth) + '">' + fmtPct(k.avgGrowth) + '</div><div class="ft">增速 ≥50% 的有 ' + k.high + ' 个</div></div>';"""
KPICARD_NEW = """  h += '<div class="card kpi"><div class="lb">环比增速中枢</div><div class="vl ' + pctCls(k.trimGrowth) + '">' + fmtPct(k.trimGrowth) + '</div><div class="ft">去掉最极端 10% 后的均值——算术平均会被个别爆款拉到几百个百分点；增速 ≥50% 的有 ' + k.high + ' 个</div></div>';"""


# ---------------------------------------------------------------- N/O. 窗口期 / 空白赛道 卡改中位数
WIN_OLD = """  var wg = avgOf(ins.win, '环比增速'), wk = avgOf(ins.win, '关联达人数');"""
WIN_NEW = """  var wg = medGrowthOf(ins.win), wk = avgOf(ins.win, '关联达人数');"""
WINEV_OLD = """    ev: '命中 <b>' + ins.win.length + '</b> 个　·　平均增速 <b>' + (wg === null ? '—' : Math.round(wg) + '%') + '</b>　·　达人渗透度：未铺开 <b>' + kLow + '</b> / 起量 <b>' + kMid + '</b> / 已铺开 <b>' + kHigh + '</b>'"""
WINEV_NEW = """    ev: '命中 <b>' + ins.win.length + '</b> 个　·　增速中位 <b>' + (wg === null ? '—' : Math.round(wg) + '%') + '</b>　·　达人渗透度：未铺开 <b>' + kLow + '</b> / 起量 <b>' + kMid + '</b> / 已铺开 <b>' + kHigh + '</b>'"""
BLANK_OLD = """    ev: '命中 <b>' + ins.blank.length + '</b> 个　·　平均增速 <b>' + (avgOf(ins.blank, '环比增速') === null ? '—' : Math.round(avgOf(ins.blank, '环比增速')) + '%') + '</b>',"""
BLANK_NEW = """    ev: '命中 <b>' + ins.blank.length + '</b> 个　·　增速中位 <b>' + (medGrowthOf(ins.blank) === null ? '—' : Math.round(medGrowthOf(ins.blank)) + '%') + '</b>',"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--target', default=DEFAULT_TARGET)
    a = ap.parse_args()
    target = os.path.abspath(a.target)

    src = io.open(target, encoding='utf-8').read()

    patches = [
        ('A 设计令牌', ROOT_OLD, ROOT_NEW),
        ('B 追加 CSS', '</style>', CSS_ADD + '</style>'),
        ('C SKU 数', SKU_OLD, SKU_NEW),
        ('D 法规字段', LEGAL_OLD, LEGAL_NEW),
        ('E Hero 代码', HERO_ANCHOR, HERO_JS + HERO_ANCHOR),
        ('F board 挂钩', HOOK_OLD, HOOK_NEW),
        ('G renderView', RV_OLD, RV_NEW),
        ('H refreshAll', RA_OLD, RA_NEW),
        ('I 市场机会列表', MKT_OLD, MKT_NEW),
        ('J 市场机会规则', MKTEV_OLD, MKTEV_NEW),
        ('J2 市场机会口径说明', MKTRULE_OLD, MKTRULE_NEW),
        ('K 增速品类列表', GCAT_OLD, GCAT_NEW),
        ('L kpiOf 收集增速', KPI_OLD, KPI_NEW),
        ('L2 kpiOf 返回截尾均值', KPIRET_OLD, KPIRET_NEW),
        ('M KPI 卡改截尾均值', KPICARD_OLD, KPICARD_NEW),
        ('N 窗口期卡中位数', WIN_OLD, WIN_NEW),
        ('N2 窗口期卡文案', WINEV_OLD, WINEV_NEW),
        ('O 空白赛道卡中位数', BLANK_OLD, BLANK_NEW),
    ]

    bad = []
    for name, old, _new in patches:
        n = src.count(old)
        if n != 1:
            bad.append((name, n, old.splitlines()[0][:76] if old.splitlines() else ''))
    if bad:
        print('!! 以下补丁未唯一命中，中止：')
        for name, n, head in bad:
            print('   %-16s 命中 %d 次 | %s' % (name, n, head))
        return 1
    print('%d 处补丁全部唯一命中（%s）' % (len(patches), os.path.basename(target)))

    if not a.apply:
        print('（dry-run，未写入；加 --apply 执行）')
        return 0

    out = src
    for _name, old, new in patches:
        out = out.replace(old, new, 1)
    io.open(target, 'w', encoding='utf-8').write(out)
    print('已写入 %s（%d -> %d 字节，+%d）' % (target, len(src), len(out), len(out) - len(src)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
