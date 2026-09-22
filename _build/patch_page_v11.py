#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面 v11：全球看板 + 榜单中心 专项（对应 workbuddy_v11_spec.md）。

范围：只改「全球看板」与「榜单中心」，以及为满足 390px 筛选可用性所必需的筛选条结构。
不重构「品类与成分库」「机会洞察」「口碑诊断」，不改导入流程 / 云表结构 / API。

改动清单：
  A  追加 v11 CSS（移动端筛选抽屉 / 热力图 / 榜单表格）
  B  state 增 c3 / period / fltOpen，rankBy 默认改为 rank
  C  插入 v11 引擎：稳健增长口径 + 周期与截至 + 来源列可得性 + 热力格 + 标签统计 + 可比 GMV
  D  dataOf 支持三级类目与统计周期筛选
  E  countryStats 改稳健口径
  F  marketStats 改稳健口径
  G  c2Stats 的 avgGrowth 由均值改中位数（保留 meanGrowth 备查）
  H  市场机会「分组资格」由均值改稳健中位数 + 正增长占比门槛
  I  heroHtml / heroStat 用稳健口径
  J  RENDER.filter 重写（桌面不变，小屏改按钮 + 抽屉 + 已选 chips）
  K  RENDER.board 重写
  L  RANK_TYPES / rankRows / 列定义重写
  M  RENDER.rank 重写（分来源分榜 + 覆盖 N/50 + 列随来源可得性增减）
  N  下钻：热力格 / 国家行点击带筛选跳到榜单中心
  O  切页时收起筛选抽屉

用法：
  python3 patch_page_v11.py                          # dry-run，只做锚点检查
  python3 patch_page_v11.py --apply --target /path/to/index.html
"""
from __future__ import annotations

import argparse
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET = os.path.join(BASE, '..', '全球选品平台.html')

# ================================================================ A. CSS
CSS_ADD = r"""
/* ===== v11 · 全球看板 / 榜单中心 专项 ===== */

/* ---- 小屏筛选：不再依赖横向长条，改「筛选」按钮 + 底部抽屉 + 已选 chips。
   抽屉必须挂在 body 直下的 #fltLayer：topbar 带 backdrop-filter，会把它内部
   position:fixed 子元素的包含块劫持到 topbar 自身，抽屉会被页面内容盖住。
   注意：本页变量是 --surface / --text / --sub，没有 --card / --t1 / --t2。 ---- */
.flt-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 0 2px}
.flt-open,.flt-sel-chips{display:none}
.flt-open{align-items:center;gap:7px;min-height:44px;padding:0 15px;border-radius:12px;
  border:1px solid var(--line);background:var(--surface);font-family:inherit;font-size:14px;
  font-weight:500;color:var(--text);cursor:pointer}
.flt-open .ic{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}
.flt-open .n{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:19px;
  padding:0 5px;border-radius:10px;background:var(--blue);color:#fff;font-size:11px;font-weight:600}
.flt-sc{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 8px 0 11px;
  border-radius:9px;background:var(--blue-soft);color:var(--blue-deep);border:1px solid #CFE4FB;font-size:12px}
.flt-sc b{font-weight:500}
.flt-sc button{border:0;background:transparent;padding:0 2px;font-size:15px;line-height:1;
  color:inherit;cursor:pointer;font-family:inherit}
#fltLayer{display:none}
body.flt-lock{overflow:hidden}
@media (max-width:860px){
  .chips{overflow:visible;padding:0}
  .chips-wide{display:none}
  .flt-bar{padding:9px 0 11px}
  .flt-open{display:inline-flex}
  .flt-sel-chips{display:flex;flex-wrap:wrap;gap:6px;width:100%}
  /* 抽屉层：body 直下、fixed 全屏、z 高于 topbar(20)/side(30)/tabbar(35)/mask(40)，低于 toast(70) */
  #fltLayer.on{display:block;position:fixed;inset:0;z-index:60}
  .flt-scrim{position:absolute;inset:0;background:rgba(15,17,28,.46)}
  .flt-sheet{position:absolute;left:0;right:0;bottom:0;display:flex;flex-direction:column;
    max-height:min(78vh,600px);background:var(--surface);border-radius:20px 20px 0 0;
    box-shadow:0 -18px 50px -20px rgba(10,16,48,.45);overflow:hidden;
    transform:translateY(102%);transition:transform .26s cubic-bezier(.32,.72,0,1)}
  .flt-sheet.on{transform:none}
  .flt-shd{flex:none;display:flex;align-items:center;justify-content:space-between;gap:10px;
    padding:14px 16px 12px;border-bottom:1px solid var(--line-2);font-size:14.5px;color:var(--text)}
  .flt-shd b{font-weight:600}
  .flt-shd .flt-shd-n{display:block;font-size:11.5px;color:var(--hint);margin-top:2px;font-weight:400}
  .flt-sbd{flex:1;min-height:0;overflow-y:auto;-webkit-overflow-scrolling:touch;
    padding:14px 16px calc(20px + env(safe-area-inset-bottom))}
  .flt-row{margin-bottom:16px}
  .flt-lb{display:block;font-size:11.5px;color:var(--hint);margin-bottom:7px}
  .flt-set{display:flex;flex-wrap:wrap;gap:7px}
  .flt-row .flt{width:100%}
  .flt-row .flt+.flt{margin-top:10px}
  /* v11 触控目标 ≥ 44px（抽屉里的 chip / 排序 tab / 商品名 / 筛选按钮） */
  .rank-tab,.flt-sheet .chip{min-height:44px;height:44px;display:inline-flex;align-items:center;
    justify-content:center;border-radius:12px;font-size:13.5px;padding:0 14px}
  .flt-sheet .mini{min-height:44px;height:44px;display:inline-flex;align-items:center;padding:0 18px}
  .flt-sheet .flt-sel{min-height:44px;height:44px;font-size:16px;padding:0 10px}
  .flt-open{height:44px}
  .flt-sc{min-height:44px}
  .flt-sc button{min-width:34px;min-height:44px}
  .rkt .pname{min-height:44px;display:flex;align-items:center}
  /* 来源榜标题区：390px 下「『抖音罗盘』榜」不能被右栏挤成三行。
     标题独占首行且整词不折，说明与「共 N 条」在次行自然换行、数量右对齐。
     仅作用于榜单（.rank-sec），不影响其它视图的 .sec-hd。 */
  .rank-sec .sec-hd{display:flex;flex-wrap:wrap;align-items:baseline;gap:3px 8px}
  .rank-sec .sec-hd h2{flex:0 0 100%;min-width:0;white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis}
  .rank-sec .sec-hd span:not(.r){flex:1 1 auto;min-width:0;line-height:1.55}
  .rank-sec .sec-hd .r{flex:0 0 auto;margin-left:auto;white-space:nowrap}
}
@media (min-width:861px){ #fltLayer{display:none !important} }

/* ---- 热力图：国家/地区 × 二级类目，容器内滚动，不产生页面级横向溢出 ---- */
.heat-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;padding:2px 0 6px}
.heat{display:grid;gap:4px;min-width:max-content}
.heat .hc,.heat .hr{font-size:11.5px;color:var(--hint)}
.heat .hr{position:sticky;left:0;z-index:2;background:var(--surface);display:flex;align-items:center;
  gap:5px;padding-right:10px;min-height:58px}
.heat .hc{writing-mode:vertical-rl;transform:rotate(180deg);height:112px;display:flex;
  align-items:center;justify-content:center;letter-spacing:.03em}
.heat .hcell{width:74px;min-height:58px;border-radius:9px;padding:7px 6px;display:flex;
  flex-direction:column;justify-content:center;gap:3px;border:1px solid transparent;
  font-family:inherit;cursor:pointer;text-align:left;transition:transform .18s,box-shadow .18s}
.heat .hcell b{font-size:14px;font-weight:600;line-height:1.05;letter-spacing:-.02em}
.heat .hcell i{font-size:10.5px;font-style:normal;color:var(--hint)}
.heat .hcell.z{background:repeating-linear-gradient(45deg,#F5F5F7 0 5px,#EFEFF2 5px 10px);
  cursor:default;align-items:center;color:#B0B0B6;font-size:11px}
.heat .hcell.l0{background:#F5F5F7;border-color:#E7E7EC}
.heat .hcell.l1{background:#F2F8FE;border-color:#E1EEFB}
.heat .hcell.l2{background:#DCEBFB;border-color:#C8DFF8}
.heat .hcell.l3{background:#0071E3;border-color:#0071E3}
.heat .hcell.l3 b{color:#fff}
.heat .hcell.l3 i{color:rgba(255,255,255,.78)}
.heat .hcell:not(.z):hover{transform:translateY(-1px);box-shadow:var(--sh-2)}

/* ---- 榜单表格：桌面是表，小屏自动变卡片 ---- */
.rkt-wrap{overflow-x:auto}
.rkt{width:100%;border-collapse:collapse}
.rkt th{font-size:11.5px;font-weight:500;color:var(--hint);text-align:left;padding:0 10px 9px;
  border-bottom:1px solid var(--line);white-space:nowrap}
.rkt td{padding:11px 10px;border-bottom:1px solid var(--line-2);font-size:12.5px;
  vertical-align:top;color:var(--text)}
.rkt tr:last-child td{border-bottom:0}
.rkt .num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.rkt .rkno{width:46px;color:var(--hint);font-weight:500}
.rkt .rkno.top{color:var(--blue);font-size:14px}
.rkt .pname{font-size:13px;font-weight:500;line-height:1.42;white-space:normal;text-align:left}
.rkt .pmeta{font-size:11px;color:var(--hint);margin-top:4px;line-height:1.5}
.rkt .bdg{display:inline-block;margin-left:6px;font-size:10px;font-weight:400;
  color:var(--amber);background:var(--amber-soft);border-radius:6px;padding:1px 6px}
/* 低基数行：打标 + 置底，视觉上再压一档，避免 57725% 这种数字抢眼光 */
.rkt tr.ex td{color:var(--sub)}
.rkt tr.ex .pname{font-weight:400}
.rkt tr.ex .rkno.top{color:var(--hint);font-size:12.5px}
.lbl-sm{font-size:11.5px;color:var(--hint);margin-bottom:8px;font-weight:500}
.rank-src{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.rank-tab .cn{font-size:10.5px;opacity:.6;margin-left:3px;font-variant-numeric:tabular-nums}
.cov-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:11px 13px;
  border-radius:12px;background:var(--surface-2);border:1px solid var(--line);
  margin-bottom:12px;font-size:12.5px}
.cov-bar b{font-variant-numeric:tabular-nums}
.cov-bar .pill{display:inline-flex;align-items:center;gap:5px;min-height:26px;padding:0 9px;
  border-radius:8px;background:var(--surface);border:1px solid var(--line);font-size:11.5px;color:var(--sub)}
.miss-note{font-size:11.5px;color:var(--hint);line-height:1.75;margin-top:9px}
.src-sum{display:flex;flex-wrap:wrap;gap:7px}
.src-chip{display:flex;flex-direction:column;gap:2px;padding:8px 11px;border-radius:10px;
  background:var(--surface-2);border:1px solid var(--line);min-width:112px}
.src-chip b{font-size:12.5px;font-weight:500}
.src-chip span{font-size:11px;color:var(--hint)}
.row-btns{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}
.q-list{margin:0;padding:0;list-style:none}
.q-list li{font-size:12px;line-height:1.75;color:var(--sub);padding-left:14px;position:relative}
.q-list li::before{content:"";position:absolute;left:2px;top:9px;width:5px;height:5px;
  border-radius:50%;background:var(--hint);opacity:.5}
.q-list li b{color:var(--text)}
.cmp-btn{width:100%;border:0;background:transparent;color:inherit;font-family:inherit;
  font-size:inherit;cursor:pointer}
.cmp-btn:hover{background:var(--surface-2)}
@media (max-width:860px){
  .rkt thead{display:none}
  .rkt,.rkt tbody,.rkt tr,.rkt td{display:block;width:auto}
  .rkt tr{border:1px solid var(--line);border-radius:14px;padding:11px 12px;margin-bottom:9px;
    background:var(--surface)}
  .rkt td{border:0;padding:3px 0;display:flex;gap:10px;justify-content:space-between;text-align:right}
  .rkt td::before{content:attr(data-l);color:var(--hint);font-size:11.5px;text-align:left;
    flex:0 0 auto}
  .rkt td.rkno{width:auto}
  .rkt td.pc{display:block;text-align:left;padding-bottom:4px}
  .rkt td.pc::before{display:none}
  .rkt-wrap{overflow-x:visible}
}
"""

# ================================================================ C. 引擎
ENGINE = r"""/* =============================================================
   v11 · 全球看板 / 榜单中心 专项引擎
   ① 统一稳健增长口径（中位数，剔除低基数）
   ② 逐来源统计周期与数据截至（不合并、不编造）
   ③ 来源列可得性 + 国家×二级类目热力格 + 可比样本 GMV
   ============================================================= */

/* ---- ① 稳健增长口径：分组资格、排序、Hero、卡片、表格统一用这一套 ----
   为什么必须统一：算术均值会被「低基数新品」单点拉爆——真实数据里印尼 × 唇妆
   有一条环比 +57725%（当期销量 2313、反推基期只剩 4 件），一条就把整格均值从
   14% 抬到 8272.78%，而中位数只有 18.16%。所以：
     · 资格判定 / 排序 / 展示 一律用中位数（剔除低基数样本）
     · 同时给出样本量、正增长占比，并把「含极端值的中位数」对照展示，不藏
     · 剔除只影响「资格判定与排序」，样本本身照常展示，只是打标，不隐藏数据
   低基数判据：反推基期销量 = 当期销量 /（1 + 环比/100） < 10 件。
   新品（上市 ≤ 90 天）只标注不剔除，因为它是真实在卖的商品。 ---------- */
var GROW_BASE_MIN = 10;
var GROW_NEW_DAYS = 90;
function baseSoldOf(r) {
  var s = numField(r, '销量'), g = numField(r, '环比增速');
  if (s === null || g === null || g <= -100) return null;
  return s / (1 + g / 100);
}
function growExcluded(r) {
  var g = numField(r, '环比增速');
  if (g === null) return '无增速';
  var b = baseSoldOf(r);
  if (b !== null && b < GROW_BASE_MIN) return '低基数';
  return '';
}
function isNewProd(r) { var d = daysSince(r['上市日期']); return d !== null && d <= GROW_NEW_DAYS; }
function growthStats(rows) {
  var all = [], keep = [], exWhy = {}, exRows = [], i, j;
  rows = rows || [];
  for (i = 0; i < rows.length; i++) {
    var g = numField(rows[i], '环比增速');
    if (g === null) continue;
    all.push(g);
    var why = growExcluded(rows[i]);
    if (why) { exWhy[why] = (exWhy[why] || 0) + 1; exRows.push(rows[i]); }
    else keep.push(g);
  }
  var pos = 0;
  for (j = 0; j < keep.length; j++) if (keep[j] > 0) pos++;
  var whyList = [];
  for (var k in exWhy) if (Object.prototype.hasOwnProperty.call(exWhy, k)) whyList.push(k + ' ' + exWhy[k] + ' 条');
  return {
    n: keep.length, nAll: all.length,
    med: medOf(keep), medAll: medOf(all),
    pos: keep.length ? Math.round(pos / keep.length * 100) : null, posN: pos,
    ex: all.length - keep.length, exWhy: whyList, exRows: exRows,
    trim: trimMean(keep, 0.1)
  };
}

/* ---- ② 统计周期与数据截至：周期是来源属性，绝不假设成「近 30 天」 ---- */
var PERIOD_BY_SRC = {
  '抖音罗盘': '榜单快照周期（写在榜单排名里）',
  '蝉妈妈': '近 7 天 vs 前 7 天',
  'FastMoss': '平台榜单未标注周期',
  'Hwahae': '仅排名（无周期）',
  'Olive Young': '仅排名（无周期）',
  'KEV美妆圈': '接口未打通（无周期）'
};
var PERIOD_RE = /(\d{4})[/-](\d{2})[/-](\d{2})\s*[~～\-—至]+\s*(\d{4})[/-](\d{2})[/-](\d{2})/;
function periodOf(r) {
  var m = PERIOD_RE.exec(txtOf(r, '榜单排名'));
  if (m) return m[1] + '-' + m[2] + '-' + m[3] + ' ~ ' + m[4] + '-' + m[5] + '-' + m[6];
  return PERIOD_BY_SRC[txtOf(r, '数据来源')] || '来源未标注周期';
}
function periodShort(src) {
  if (src === '抖音罗盘') return '7 天榜单快照';
  if (src === '蝉妈妈') return '近 7 天 vs 前 7 天';
  if (src === 'FastMoss') return '来源未标注周期';
  var d = srcDef(src);
  if (d && d.kind === 'kr') return '仅排名';
  return '来源未标注周期';
}
/* 数据截至：只有榜单文本里带周期的来源能给；给不出就返回空串，由调用方显示「—」 */
function asOfOf(r) {
  var m = PERIOD_RE.exec(txtOf(r, '榜单排名'));
  if (m) return m[4] + '-' + m[5] + '-' + m[6];
  return '';
}
function freshnessOf(list) {
  var best = '';
  for (var i = 0; i < list.length; i++) { var a = asOfOf(list[i]); if (a && a > best) best = a; }
  return best || '—（来源未标注）';
}
/* 榜单原始名次：库里两种形态都要认，且不能混——
   「第 N 名」= 来源全局名次 N；「第 P 页 第 Q 位」= 抓取分页序（不是「第 Q 名」，
   也不能把「第1页第1位」猜成全局第 1 名）。推不出原始名次就返回空，不编造。 */
var RANK_NO_RE = /第\s*(\d+)\s*名/;
var RANK_PAGE_RE = /第\s*(\d+)\s*页\s*第\s*(\d+)\s*位/;
function rankNoOf(r) {
  var m = RANK_NO_RE.exec(txtOf(r, '榜单排名'));
  return m ? Number(m[1]) : null;
}
function rankPageOf(r) {
  var m = RANK_PAGE_RE.exec(txtOf(r, '榜单排名'));
  return m ? { page: Number(m[1]), pos: Number(m[2]) } : null;
}
function rankTextOf(r) {
  var n = rankNoOf(r);
  if (n !== null) return '第' + n + '名';
  var p = rankPageOf(r);
  if (p) return '第' + p.page + '页第' + p.pos + '位';
  return '';
}
/* 原始名次排序键：全局名次在前，分页位次按「页 → 位」，都推不出的最后 */
function rankKeyOf(r) {
  var n = rankNoOf(r);
  if (n !== null) return [0, n, 0];
  var p = rankPageOf(r);
  if (p) return [1, p.page, p.pos];
  return [2, 0, 0];
}
/* 库里出现的统计周期取值（榜单中心筛选用；可传 rows 限定作用域） */
function periodIn(rows) {
  var L = rows || state.list, m = {}, out = [], k;
  for (var i = 0; i < L.length; i++) m[periodOf(L[i])] = 1;
  for (k in m) if (Object.prototype.hasOwnProperty.call(m, k)) out.push(k);
  out.sort();
  return out;
}

/* ---- ③ 来源列可得性：没有的列不编造，排名型来源整列不出 ---- */
var SRC_HAS = {
  '抖音罗盘': { no: 1, sold: 1, gmv: 1, asof: 1, note: '商品榜单不提供环比增速与关联达人数，所以本榜没有「增速」列；周期写在榜单排名文本里' },
  '蝉妈妈': { no: 1, sold: 1, gmv: 1, grow: 1, note: '商品榜不提供评分 / 评价数 / 价格；增速口径为近 7 天 vs 前 7 天' },
  'FastMoss': { no: 1, sold: 1, grow: 1, note: '榜单未标注统计周期与截至日；当前未结构化提供销售额（250 条全缺），所以本榜没有「销售额」列；名次为抓取序「页-位」' },
  'Hwahae': { no: 1, note: '排名型来源：只公开名次与评分，无销量 / 金额 / 增速' },
  'Olive Young': { no: 1, note: '排名型来源：只公开名次，销量与金额不公开' },
  'KEV美妆圈': { note: '接口未打通，暂无字段可得' },
  '人工调研': { note: '人工字段，不含平台销量类数据' }
};
function srcHas(src, col) {
  var d = SRC_HAS[src];
  if (!d) return false;
  return !!d[col];
}
function srcNote(src) {
  var d = SRC_HAS[src];
  return d ? (d.note || '') : '该来源不在数据源台账里，列可得性未知，因此不展示销量与金额';
}

/* ---- 来源分布：分榜 Tabs 与筛选 chip 共用；只看「当前筛选下真的会出现」的来源 ---- */
function srcCounts(rows) {
  var m = {}, out = [], i, k;
  var order = SOURCES.map(function (s) { return s.k; });
  for (i = 0; i < rows.length; i++) {
    var v = txtOf(rows[i], '数据来源') || '未标来源';
    m[v] = (m[v] || 0) + 1;
  }
  for (k in m) if (Object.prototype.hasOwnProperty.call(m, k)) out.push({ k: k, n: m[k], order: order.indexOf(k) });
  out.sort(function (a, b) {
    var oa = a.order < 0 ? 99 : a.order, ob = b.order < 0 ? 99 : b.order;
    return oa === ob ? b.n - a.n : oa - ob;
  });
  return out;
}

/* ---- 热力格：国家/地区 × 二级类目，每格给样本数与稳健增长中枢 ---- */
function heatOf(list) {
  var grid = {}, cty = [], c2n = {}, mkt = {}, i, j;
  for (i = 0; i < list.length; i++) {
    var r = list[i], c = txtOf(r, '国家/地区') || '未标国家', s = txtOf(r, '二级类目') || '未标细分';
    if (cty.indexOf(c) < 0) { cty.push(c); mkt[c] = txtOf(r, '所属市场') || '其他'; }
    c2n[s] = (c2n[s] || 0) + 1;
    var key = c + '\u0001' + s;
    if (!grid[key]) grid[key] = { n: 0, rows: [] };
    grid[key].n++; grid[key].rows.push(r);
  }
  var cols = [], k;
  for (k in c2n) if (Object.prototype.hasOwnProperty.call(c2n, k)) cols.push({ k: k, n: c2n[k] });
  cols.sort(function (a, b) { return b.n - a.n || (a.k < b.k ? -1 : 1); });
  var rows = [];
  for (i = 0; i < cty.length; i++) {
    var tot = 0;
    for (j = 0; j < cols.length; j++) {
      var cell = grid[cty[i] + '\u0001' + cols[j].k];
      tot += cell ? cell.n : 0;
    }
    rows.push({ country: cty[i], tot: tot, mkt: mkt[cty[i]] });
  }
  rows.sort(function (a, b) { return b.tot - a.tot; });
  return { rows: rows, cols: cols, grid: grid, mkt: mkt, total: list.length };
}

/* ---- 标签（概念 / 成分）统计：条长用样本数，避免跨币种金额相加 ---- */
function tagStats(list, name) {
  var map = {}, i, j;
  for (i = 0; i < list.length; i++) {
    var arr = splitTags(txtOf(list[i], name));
    for (j = 0; j < arr.length; j++) {
      var k = arr[j];
      if (!map[k]) map[k] = { k: k, n: 0, rows: [] };
      map[k].n++; map[k].rows.push(list[i]);
    }
  }
  var out = [], q;
  for (q in map) if (Object.prototype.hasOwnProperty.call(map, q)) {
    var x = map[q], g = growthStats(x.rows);
    out.push({ k: x.k, n: x.n, med: g.med, pos: g.pos });
  }
  out.sort(function (a, b) {
    return b.n - a.n || ((b.med === null ? -1e9 : b.med) - (a.med === null ? -1e9 : a.med));
  });
  return out;
}

/* ---- 可比样本 GMV（v11·复审收紧）：单一来源 + 单一国家 + 单一币种 + 单一周期才相加。
   库里没有「币种」字段，币种只能由「国家/地区」唯一推出；单来源 ≠ 单币种
   （FastMoss 一个来源就横跨 11 个国家、多种货币）。币种推不出、国家不唯一、
   周期不唯一——任何一条不满足都不出合计，显示「—」并给原因，绝不出「0 元」。 ---- */
var CURRENCY_BY_COUNTRY = {
  '中国': 'CNY', '中国香港': 'HKD', '中国台湾': 'TWD', '日本': 'JPY', '韩国': 'KRW',
  '美国': 'USD', '英国': 'GBP', '新加坡': 'SGD', '马来西亚': 'MYR', '泰国': 'THB',
  '越南': 'VND', '菲律宾': 'PHP', '印度尼西亚': 'IDR', '巴西': 'BRL', '墨西哥': 'MXN'
};
var CURRENCY_UNIT = { CNY: '元', HKD: '港元', TWD: '新台币', JPY: '日元', KRW: '韩元', USD: '美元',
  GBP: '英镑', SGD: '新加坡元', MYR: '令吉', THB: '泰铢', VND: '越南盾', PHP: '比索',
  IDR: '印尼盾', BRL: '雷亚尔', MXN: '比索' };
function currencyOf(country) { return CURRENCY_BY_COUNTRY[country] || null; }
function comparableGmv(list) {
  var srcs = {}, cts = {}, pers = {}, i, k, rows = [];
  for (i = 0; i < list.length; i++) {
    if (numField(list[i], '销售额') === null) continue;
    rows.push(list[i]);
    srcs[txtOf(list[i], '数据来源') || '未标来源'] = 1;
    cts[txtOf(list[i], '国家/地区') || '未标国家'] = 1;
    pers[periodOf(list[i])] = 1;
  }
  var sk = [], ck = [], pk = [];
  for (k in srcs) if (Object.prototype.hasOwnProperty.call(srcs, k)) sk.push(k);
  for (k in cts) if (Object.prototype.hasOwnProperty.call(cts, k)) ck.push(k);
  for (k in pers) if (Object.prototype.hasOwnProperty.call(pers, k)) pk.push(k);
  var cur = (ck.length === 1) ? currencyOf(ck[0]) : null;
  var reasons = [];
  if (!rows.length) reasons.push('当前范围没有带金额的样本');
  if (sk.length > 1) reasons.push('横跨 ' + sk.length + ' 个来源（' + sk.join('、') + '），统计口径不同，不能相加');
  if (ck.length > 1) reasons.push('横跨 ' + ck.length + ' 个国家/地区（' + ck.slice(0, 6).join('、') + (ck.length > 6 ? ' 等' : '') + '），币种不同，不能相加');
  if (rows.length && ck.length === 1 && !cur) reasons.push('「' + ck[0] + '」的币种未登记，不能默认按人民币合计');
  if (pk.length > 1) reasons.push('金额来自 ' + pk.length + ' 个统计周期，不能相加');
  if (!rows.length || sk.length > 1 || ck.length > 1 || !cur || pk.length > 1) {
    if (!reasons.length) reasons.push('不满足「单一来源 + 单一国家 + 单一币种 + 单一周期」，不出合计');
    reasons.push('库里没有「币种」字段，不做默认汇率折算');
    return { ok: false, reasons: reasons };
  }
  var sum = 0;
  for (i = 0; i < rows.length; i++) sum += numField(rows[i], '销售额');
  return { ok: true, src: sk[0], country: ck[0], currency: cur, unit: CURRENCY_UNIT[cur] || cur,
    period: pk[0], sum: sum, n: rows.length,
    reasons: ['仅 ' + sk[0] + ' · ' + ck[0] + '（' + cur + '）单一来源、单一国家、单一周期（' + pk[0] + '）的合计，原币未折算'] };
}

/* ---- v11·复审：board / rank 专用数据作用域。
   dataOf() 保持 V10 原样（含示例、不套三级类目 / 统计周期），lib / insight / review 继续用它；
   只有看板与榜单中心走 boardRankDataOf()：默认只取真实数据，并应用三级类目与统计周期。
   opt.ignore = { 维度: 1 }：计算某个筛选项的选项计数时，只忽略自己的维度。 ---- */
function isBrView() { return state.view === 'board' || state.view === 'rank'; }
function boardRankDataOf(opt) {
  opt = opt || {};
  var ig = opt.ignore || {}, out = [], i, r;
  for (i = 0; i < state.list.length; i++) {
    r = state.list[i];
    if (!ig.market && state.market !== '全部' && txtOf(r, '所属市场') !== state.market) continue;
    if (!ig.cat && state.cat !== '全部' && txtOf(r, '品类') !== state.cat) continue;
    if (!ig.c2 && state.c2 !== '全部' && txtOf(r, '二级类目') !== state.c2) continue;
    if (!ig.country && state.country !== '全部' && txtOf(r, '国家/地区') !== state.country) continue;
    if (!ig.src && state.src !== '全部' && txtOf(r, '数据来源') !== state.src) continue;
    if (!ig.c3 && state.c3 !== '全部' && txtOf(r, '三级类目') !== state.c3) continue;
    if (!ig.period && state.period !== '全部' && periodOf(r) !== state.period) continue;
    if (state.kw) {
      var hay = [txtOf(r, '商品名称'), txtOf(r, '品牌'), txtOf(r, '概念标签'), txtOf(r, '核心功效成分'),
        txtOf(r, '细分品类'), txtOf(r, '二级类目'), txtOf(r, '三级类目'), txtOf(r, '国家/地区'),
        txtOf(r, '功效宣称'), txtOf(r, '差评关键词')].join(' ').toLowerCase();
      if (hay.indexOf(state.kw.toLowerCase()) < 0) continue;
    }
    /* 默认只取真实数据；用户显式切「只看示例」后示例才进入统计与计数 */
    if (state.demoOnly) { if (!isDemo(r)) continue; }
    else if (isDemo(r)) continue;
    out.push(r);
  }
  return out;
}
/* 筛选项计数作用域：board/rank 基于默认真实数据（只忽略正在计数的维度）；
   lib/insight 保持 V10 语义——选项来自全量 state.list。 */
function fltScopeRows(ignoreKey) {
  if (!isBrView()) return state.list;
  var ig = {};
  if (ignoreKey) ig[ignoreKey] = 1;
  return boardRankDataOf({ ignore: ig });
}

/* ---- v11·复审：board 专用二级类目统计（稳健口径）。c2Stats 保持 V10 均值口径不动。 ---- */
function boardC2Stats(list) {
  var m = {}, i;
  for (i = 0; i < list.length; i++) {
    var r = list[i], c = txtOf(r, '二级类目');
    if (!c) continue;
    var a = m[c];
    if (!a) a = m[c] = { c2: c, l1: txtOf(r, '品类') || '—', n: 0, sales: 0, gs: [], c3: {}, ct: {} };
    a.n++;
    a.sales += numField(r, '销售额') || 0;
    var g = numField(r, '环比增速'); if (g !== null) a.gs.push(g);
    var c3 = txtOf(r, '三级类目'); if (c3) a.c3[c3] = (a.c3[c3] || 0) + 1;
    var ct = txtOf(r, '国家/地区'); if (ct) a.ct[ct] = 1;
  }
  var out = [], c;
  for (c in m) {
    if (!Object.prototype.hasOwnProperty.call(m, c)) continue;
    var x = m[c];
    out.push({
      c2: x.c2, l1: x.l1, n: x.n, sales: x.sales,
      avgGrowth: medOf(x.gs), meanGrowth: avgArr(x.gs),
      c3n: Object.keys(x.c3).length, ctn: Object.keys(x.ct).length,
      topC3: topKey(x.c3, 3).join(' / ') || '—'
    });
  }
  out.sort(function (a, b) {
    return (b.avgGrowth === null ? -1e9 : b.avgGrowth) - (a.avgGrowth === null ? -1e9 : a.avgGrowth);
  });
  return out;
}

/* ---- v11·复审：board 专用机会判定（稳健口径）。insightsOf 保持 V10 均值口径不动，
   机会洞察视图继续用 insightsOf；看板 Hero 用这里的中位数 + 正增长占比口径。 ---- */
function boardInsightsOf(list) {
  var win = [], fix = [], blank = [], ready = [], risk = [], mkt = [], gcat = [], newp = [], ingr = [];
  var i, j;
  for (i = 0; i < list.length; i++) {
    var r = list[i];
    var g = numField(r, '环比增速'), sd = numField(r, '销量');
    var bad = txtOf(r, '差评关键词');
    var overlap = txtOf(r, '与我方 SKU 重合度');
    var filing = txtOf(r, '备案路径'), hard = txtOf(r, '宣称支撑难度');
    var ratio = ratioCost(r);
    if (g !== null && g >= WIN_MIN_GROWTH) win.push(r);
    if (bad !== '') fix.push(r);
    if (overlap === '全新' && g !== null && g >= 25) blank.push(r);
    if (filing === '普通化妆品备案' && hard === '无需评价' && ratio !== null && ratio <= 0.25) ready.push(r);
    if ((g !== null && g < 0) || HIGH_RISK_WORD.test(bad)) risk.push(r);
    var d = daysSince(r['上市日期']);
    if (d !== null && d <= NEW_MAX_DAYS && g !== null && g >= NEW_MIN_GROWTH && (sd === null || sd >= NEW_MIN_SOLD)) newp.push(r);
  }
  var cells = {};
  for (j = 0; j < list.length; j++) {
    var rj = list[j], ct = txtOf(rj, '国家/地区'), c2 = txtOf(rj, '二级类目');
    var gv = numField(rj, '环比增速');
    if (!ct || !c2 || gv === null) continue;
    var key = ct + '\u0001' + c2;
    if (!cells[key]) cells[key] = { country: ct, c2: c2, n: 0, gs: [], rows: [] };
    cells[key].n++; cells[key].gs.push(gv); cells[key].rows.push(rj);
  }
  var ck;
  for (ck in cells) {
    if (!Object.prototype.hasOwnProperty.call(cells, ck)) continue;
    var cl = cells[ck], cst = growthStats(cl.rows), cmean = avgArr(cl.gs);
    if (cst.n >= MKT_MIN_SAMPLE && cst.med !== null && cst.med >= MKT_MIN_GROWTH
        && cst.pos !== null && cst.pos >= MKT_MIN_POS) {
      mkt.push({ country: cl.country, c2: cl.c2, n: cl.n, nKeep: cst.n, avgGrowth: cst.med, med: cst.med,
        medAll: cst.medAll, pos: cst.pos, excluded: cst.ex, exWhy: cst.exWhy, mean: cmean,
        rows: cl.rows, key: ck });
    }
  }
  mkt.sort(function (a, b) { return (b.med === null ? -1e9 : b.med) - (a.med === null ? -1e9 : a.med); });
  var c2s = boardC2Stats(list);
  for (j = 0; j < c2s.length; j++) {
    var x = c2s[j];
    if (x.n >= GCAT_MIN_SAMPLE && x.avgGrowth !== null && x.avgGrowth >= GCAT_MIN_GROWTH) gcat.push(x);
  }
  gcat.sort(function (a, b) { return b.avgGrowth - a.avgGrowth; });
  var ings = ingStats(list);
  for (j = 0; j < ings.length; j++) {
    var y = ings[j];
    if (y.n >= ING_MIN_SAMPLE && y.medianGrowth !== null && y.medianGrowth >= ING_MIN_GROWTH) ingr.push(y);
  }
  ingr.sort(function (a, b) { return b.medianGrowth - a.medianGrowth || b.n - a.n; });
  function byGrowth(a, b) { return (numField(b, '环比增速') || 0) - (numField(a, '环比增速') || 0); }
  win.sort(byGrowth); blank.sort(byGrowth); ready.sort(byGrowth); newp.sort(byGrowth);
  fix.sort(function (a, b) { return (numField(b, '销量') || 0) - (numField(a, '销量') || 0); });
  risk.sort(function (a, b) { return (numField(b, '销量') || 0) - (numField(a, '销量') || 0); });
  return { win: win, fix: fix, blank: blank, ready: ready, risk: risk,
    mkt: mkt, gcat: gcat, newp: newp, ingr: ingr };
}

"""

# （D. dataOf 切片已删除：dataOf 保持 V10 原样，board/rank 用独立的 boardRankDataOf）

# ================================================================ E/F. 聚合
COUNTRY_OLD = """function countryStats(list) {
  var m = {}, i;
  for (i = 0; i < list.length; i++) {
    var r = list[i], c = txtOf(r, '国家/地区') || '未标国家';
    var a = m[c];
    if (!a) a = m[c] = { country: c, market: txtOf(r, '所属市场') || '其他', n: 0, sales: 0, sn: 0, gs: [], ks: [], c2: {} };
    a.n++;
    var sv = numField(r, '销售额');
    if (sv !== null) { a.sales += sv; a.sn++; }
    var g = numField(r, '环比增速'); if (g !== null) a.gs.push(g);
    var k = numField(r, '关联达人数'); if (k !== null) a.ks.push(k);
    var c2 = txtOf(r, '二级类目'); if (c2) a.c2[c2] = (a.c2[c2] || 0) + 1;
  }
  var out = [], c;
  for (c in m) {
    if (!Object.prototype.hasOwnProperty.call(m, c)) continue;
    var x = m[c], ag = avgArr(x.gs), ak = avgArr(x.ks), tk = topKey(x.c2, 2);
    out.push({
      country: x.country, market: x.market, n: x.n,
      sales: x.sn ? x.sales : null,   /* 一条有销售额的都没有就显示 —，别拿 0 冒充 */
      avgGrowth: ag, avgKol: ak === null ? null : Math.round(ak), topC2: tk.join(' / ') || '—'
    });
  }
  out.sort(function (a, b) { return b.sales - a.sales; });
  return out;
}"""

COUNTRY_NEW = r"""/* 国家/地区维度（v11）：样本数、样本结构占比、稳健增长中枢、正增长占比、来源与主力细分。
   不再按销售额排序——金额只有部分来源有、且币种不同，排序一律回到样本与稳健增速。 */
function countryStats(list) {
  var m = {}, i;
  for (i = 0; i < list.length; i++) {
    var r = list[i], c = txtOf(r, '国家/地区') || '未标国家';
    var a = m[c];
    if (!a) a = m[c] = { country: c, market: txtOf(r, '所属市场') || '其他', n: 0, ks: [], c2: {}, src: {}, gmv: 0, rows: [] };
    a.n++;
    if (numField(r, '销售额') !== null) a.gmv++;
    var k = numField(r, '关联达人数'); if (k !== null) a.ks.push(k);
    var c2 = txtOf(r, '二级类目'); if (c2) a.c2[c2] = (a.c2[c2] || 0) + 1;
    var s = txtOf(r, '数据来源'); if (s) a.src[s] = 1;
    a.rows.push(r);
  }
  var out = [], c, tot = list.length || 1;
  for (c in m) {
    if (!Object.prototype.hasOwnProperty.call(m, c)) continue;
    var x = m[c], g = growthStats(x.rows), ak = avgArr(x.ks), tk = topKey(x.c2, 2);
    var sn = 0, sk;
    for (sk in x.src) if (Object.prototype.hasOwnProperty.call(x.src, sk)) sn++;
    out.push({
      country: x.country, market: x.market, n: x.n, share: Math.round(x.n / tot * 1000) / 10,
      med: g.med, medAll: g.medAll, pos: g.pos, nKeep: g.n, ex: g.ex,
      avgKol: ak === null ? null : Math.round(ak), topC2: tk.join(' / ') || '—',
      srcN: sn, gmvN: x.gmv
    });
  }
  out.sort(function (a, b) { return b.n - a.n; });
  return out;
}"""

MARKET_OLD = """function marketStats(list) {
  var map = groupBy(list, '所属市场'), out = [];
  for (var k in map) {
    if (!Object.prototype.hasOwnProperty.call(map, k)) continue;
    var g = map[k];
    var sales = 0, kol = 0, kn = 0;
    for (var i = 0; i < g.length; i++) {
      var s = numField(g[i], '销售额'); if (s !== null) sales += s;
      var kk = numField(g[i], '关联达人数'); if (kk !== null) { kol += kk; kn++; }
    }
    out.push({ market: k, n: g.length, sales: sales, avgGrowth: avgField(g, '环比增速'), avgKol: kn ? Math.round(kol / kn) : null, avgRefund: avgField(g, '退货率') });
  }
  out.sort(function (a, b) { return b.sales - a.sales; });
  return out;
}"""

MARKET_NEW = r"""/* 大区维度（v11）：只出样本结构占比与稳健增长中枢，不出跨币种金额合计 */
function marketStats(list) {
  var m = {}, i;
  for (i = 0; i < list.length; i++) {
    var r = list[i], k = txtOf(r, '所属市场') || '未标市场';
    var a = m[k];
    if (!a) a = m[k] = { market: k, n: 0, ks: [], rf: [], cty: {}, rows: [] };
    a.n++; a.rows.push(r);
    var cty = txtOf(r, '国家/地区'); if (cty) a.cty[cty] = 1;
    var kk = numField(r, '关联达人数'); if (kk !== null) a.ks.push(kk);
    var rf = numField(r, '退货率'); if (rf !== null) a.rf.push(rf);
  }
  var out = [], c, tot = list.length || 1;
  for (c in m) {
    if (!Object.prototype.hasOwnProperty.call(m, c)) continue;
    var x = m[c], g = growthStats(x.rows), ak = avgArr(x.ks);
    out.push({
      market: x.market, n: x.n, share: Math.round(x.n / tot * 1000) / 10,
      med: g.med, medAll: g.medAll, pos: g.pos, nKeep: g.n, ex: g.ex,
      avgKol: ak === null ? null : Math.round(ak), avgRefund: avgArr(x.rf),
      ctyN: Object.keys(x.cty).length
    });
  }
  out.sort(function (a, b) { return b.n - a.n; });
  return out;
}"""

# ================================================================ I. Hero
HERO_OLD = """function heroHtml(list) {
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
}"""

HERO_NEW = r"""function heroHtml(list) {
  /* v11·复审：Hero 只属于看板，用 board 专用稳健口径，不动共享的 insightsOf */
  var ins = boardInsightsOf(list);
  var gAll = growthStats(list);
  var filed = 0, srcs = {}, i;
  for (i = 0; i < list.length; i++) {
    if (txtOf(list[i], '备案/许可号') !== '') filed++;
    srcs[txtOf(list[i], '数据来源') || '未标来源'] = 1;
  }
  var sn = 0, sk;
  for (sk in srcs) if (Object.prototype.hasOwnProperty.call(srcs, sk)) sn++;

  var line, sub;
  if (ins.mkt.length) {
    var m0 = ins.mkt[0];
    line = '<em>' + esc(m0.country) + ' · ' + esc(m0.c2) + '</em> 这一格值得先看：'
      + m0.nKeep + ' 个有效样本的稳健增长中枢 <em>' + (m0.med === null ? '—' : fmtPct(m0.med)) + '</em>，'
      + '正增长 <em>' + (m0.pos === null ? '—' : m0.pos + '%') + '</em>';
    sub = '口径是中位数（已剔除' + (m0.excluded ? ' ' + m0.excluded + ' 条低基数样本' : ' 0 条低基数样本')
      + '，含极端值的中位数是 ' + (m0.medAll === null ? '—' : fmtPct(m0.medAll)) + '）。'
      + '同一个国家、同一个功能子类里同时冒出上升品，一般不是巧合，更像当地需求在换挡——先把这一格里的品逐个看一遍，比在别处找单点爆款划算。';
  } else if (ins.gcat.length) {
    var g0 = ins.gcat[0];
    line = '<em>' + esc(g0.c2) + '</em> 这条赛道在涨，稳健增长中枢 <em>'
      + (g0.avgGrowth === null ? '—' : fmtPct(g0.avgGrowth)) + '</em>';
    sub = '口径是中位数，且要求样本 ≥ ' + GCAT_MIN_SAMPLE + ' 个。品类级别的普涨比单点爆款更值得跟——前者说明需求在扩大，后者可能只是某个商家在砸钱。';
  } else if (ins.win.length) {
    line = '有 <em>' + ins.win.length + ' 个品</em>环比涨超 ' + WIN_MIN_GROWTH + '%，值得逐个看';
    sub = '这是单品维度的筛选（看单条商品的环比），与格子/榜单的中位数中枢是两种粒度——单品榜在「榜单中心」按来源分别看。';
  } else {
    line = '本期稳健口径下还没有格子达到资格门槛';
    sub = '门槛是：样本 ≥ ' + MKT_MIN_SAMPLE + ' 条、稳健增长中枢 ≥ ' + MKT_MIN_GROWTH + '%、正增长占比 ≥ ' + MKT_MIN_POS + '%。可以放宽筛选，或到「榜单中心」按来源逐个看。';
  }

  var foot = '当前范围 <b>' + list.length + '</b> 个真实样本、<b>' + sn + '</b> 个来源；'
    + '有效增速样本 <b>' + gAll.n + '</b> 条，正增长 <b>' + gAll.posN + '</b> 条（占 '
    + (gAll.pos === null ? '—' : gAll.pos + '%') + '）'
    + (gAll.ex ? '；已剔除低基数样本 <b>' + gAll.ex + '</b> 条' : '')
    + (filed ? '；<b>' + filed + '</b> 个能在目标市场查到官方备案号' : '') + '。';

  return '<div class="hero"><div class="hero-in">'
    + '<div class="hero-l">'
    + '<span class="hero-eye"><i></i>稳健口径 · ' + cnDate(new Date()) + ' 快照</span>'
    + '<h2 class="hero-h">' + line + '</h2>'
    + '<p class="hero-p">' + sub + '</p>'
    + '<p class="hero-p hero-foot">' + foot + '</p>'
    + '<div class="hero-btns">'
    + '<button type="button" class="hero-btn pri" data-view="rank">去榜单中心</button>'
    + '<button type="button" class="hero-btn" data-view="insight">看全部机会</button>'
    + '</div></div>'
    + '<div class="hero-r">'
    + heroStat('稳健增长中枢', (gAll.med === null ? '—' : fmtPct(gAll.med)), '', '中位数 · 剔除低基数')
    + heroStat('正增长占比', (gAll.pos === null ? '—' : gAll.pos), '%', gAll.posN + ' / ' + gAll.n + ' 条有效样本')
    + heroStat('样本数', list.length, '条', '覆盖 ' + sn + ' 个来源')
    + heroStat('已备案', filed, '个', '可查官方备案号')
    + '</div></div></div>';
}"""

HERO_STAT_OLD = """function heroStat(label, val, unit, foot) {
  return '<div class="hero-stat"><div class="l">' + esc(label) + '</div>'
    + '<div class="v" data-count="' + val + '" data-unit="' + esc(unit) + '">' + val
    + '<small>' + esc(unit) + '</small></div>'
    + '<div class="f">' + esc(foot) + '</div></div>';
}"""

HERO_STAT_NEW = r"""function heroStat(label, val, unit, foot) {
  /* 只有纯数字才挂 data-count（数字滚动）；「+14.1%」这类格式化字符串原样渲染 */
  var isNum = (typeof val === 'number' && isFinite(val));
  return '<div class="hero-stat"><div class="l">' + esc(label) + '</div>'
    + '<div class="v"' + (isNum ? ' data-count="' + val + '" data-unit="' + esc(unit) + '"' : '') + '>' + val
    + (unit ? '<small>' + esc(unit) + '</small>' : '') + '</div>'
    + '<div class="f">' + esc(foot) + '</div></div>';
}"""

# ================================================================ J. 筛选
FILTER_OLD = """RENDER.filter = function () {
  if (state.view === 'review') {
    $('#chips').innerHTML = '<span class="hint" style="margin:2px 0">口碑诊断读的是第二张表「自有店铺口碑库」，与上面的商品筛选无关；切回其它视图即恢复筛选。</span>';
    return;
  }
  var h = '';
  var ms = marketsIn();
  h += '<button type="button" class="chip' + (state.market === '全部' ? ' on' : '') + '" data-f="market" data-v="全部">全部市场</button>';
  for (var i = 0; i < ms.length; i++) {
    h += '<button type="button" class="chip' + (state.market === ms[i] ? ' on' : '') + '" data-f="market" data-v="' + esc(ms[i]) + '">' + esc(ms[i]) + '</button>';
  }
  h += '<span class="chip-sep"></span>';
  var cs = catsIn();
  h += '<button type="button" class="chip' + (state.cat === '全部' ? ' on' : '') + '" data-f="cat" data-v="全部">全部品类</button>';
  for (var j = 0; j < cs.length; j++) {
    h += '<button type="button" class="chip' + (state.cat === cs[j] ? ' on' : '') + '" data-f="cat" data-v="' + esc(cs[j]) + '">' + esc(cs[j]) + '</button>';
  }
  h += '<span class="chip-sep"></span>';
  var ss = srcsIn();
  h += '<button type="button" class="chip' + (state.src === '全部' ? ' on' : '') + '" data-f="src" data-v="全部">全部来源</button>';
  for (var q = 0; q < ss.length; q++) {
    h += '<button type="button" class="chip' + (state.src === ss[q].k ? ' on' : '') + '" data-f="src" data-v="' + esc(ss[q].k) + '">' + esc(ss[q].k) + ' <span class="cn">' + ss[q].n + '</span></button>';
  }
  h += '<span class="chip-sep"></span>';
  h += '<button type="button" class="chip' + (state.realOnly ? ' on' : '') + '" data-f="realOnly" data-v="' + (state.realOnly ? '0' : '1') + '">只看真实</button>';
  h += '<button type="button" class="chip' + (state.demoOnly ? ' on' : '') + '" data-f="demoOnly" data-v="' + (state.demoOnly ? '0' : '1') + '">只看示例</button>';
  /* 第二行：国家/地区 + 二级类目细分。二级类目取值多，用下拉不铺 chip，手机上一行放得下 */
  h += '<div class="chip-row2">';
  h += '<label class="flt"><span>国家/地区</span><select class="flt-sel" data-f-sel="country">'
    + '<option value="全部"' + (state.country === '全部' ? ' selected' : '') + '>全部（' + state.list.length + ' 个商品）</option>';
  var cos = countriesIn();
  for (var ci = 0; ci < cos.length; ci++) {
    h += '<option value="' + esc(cos[ci].k) + '"' + (state.country === cos[ci].k ? ' selected' : '')
      + '>' + esc(cos[ci].k) + '（' + cos[ci].n + '）</option>';
  }
  h += '</select></label>';
  h += '<label class="flt"><span>二级类目</span><select class="flt-sel" data-f-sel="c2">'
    + '<option value="全部"' + (state.c2 === '全部' ? ' selected' : '') + '>全部细分</option>';
  var c2s = c2In();
  for (var cj = 0; cj < c2s.length; cj++) {
    h += '<option value="' + esc(c2s[cj].k) + '"' + (state.c2 === c2s[cj].k ? ' selected' : '')
      + '>' + esc(c2s[cj].k) + '（' + c2s[cj].n + '）</option>';
  }
  h += '</select></label>';
  if (state.country !== '全部') h += '<button type="button" class="chip" data-f="country" data-v="全部">清空国家</button>';
  if (state.c2 !== '全部') h += '<button type="button" class="chip" data-f="c2" data-v="全部">清空细分</button>';
  h += '</div>';
  $('#chips').innerHTML = h;
};"""

FILTER_NEW = r"""RENDER.filter = function () {
  if (state.view === 'review') {
    $('#chips').innerHTML = '<span class="hint" style="margin:2px 0">口碑诊断读的是第二张表「自有店铺口碑库」，与上面的商品筛选无关；切回其它视图即恢复筛选。</span>';
    fltLayerRender();
    return;
  }
  var showMore = (state.view === 'board' || state.view === 'rank');
  var n = fltSelCount();
  var h = '<div class="flt-bar">'
    + '<button type="button" class="flt-open" data-f="fltOpen" data-v="' + (state.fltOpen === '1' ? '0' : '1') + '">'
    + '<svg class="ic" viewBox="0 0 24 24"><path d="M4 6h16M7 12h10M10 18h4"/></svg>筛选'
    + (n ? '<span class="n">' + n + '</span>' : '') + '</button>'
    + '<div class="flt-sel-chips">' + fltSelChipsHtml() + '</div>'
    + '</div>';
  /* 桌面端保持 v10 的横向 chip 条（视觉不变），小屏由 CSS 换成按钮 + 抽屉 */
  h += '<div class="chips-wide">' + fltStripHtml(showMore) + '</div>';
  $('#chips').innerHTML = h;
  /* 抽屉渲染在 body 直下的 #fltLayer：topbar 的 backdrop-filter 会劫持 fixed 包含块，
     留在 #chips 里会被页面内容盖住（v11 第一版的实际缺陷） */
  fltLayerRender();
};
/* ---- 筛选抽屉层：body 直下，不透明白面板 + 遮罩，遮罩挡住底层所有点击 ---- */
function fltLayerEl() {
  var el = document.getElementById('fltLayer');
  if (!el) { el = document.createElement('div'); el.id = 'fltLayer'; document.body.appendChild(el); }
  return el;
}
function fltLayerRender() {
  var el = fltLayerEl();
  var open = (state.fltOpen === '1' && state.view !== 'review');
  if (!open) {
    if (el.className || el.innerHTML) { el.className = ''; el.innerHTML = ''; }
    document.body.classList.remove('flt-lock');
    return;
  }
  el.className = 'on';
  document.body.classList.add('flt-lock');
  var n = fltSelCount();
  el.innerHTML = '<div class="flt-scrim" data-f="fltOpen" data-v="0"></div>'
    + '<div class="flt-sheet on"><div class="flt-shd"><div><b>筛选条件</b>'
    + '<span class="flt-shd-n">' + (n ? '已选 ' + n + ' 个条件' : '未选条件 · 默认只统计真实数据') + '</span></div>'
    + '<button type="button" class="mini" data-f="fltOpen" data-v="0">完成</button></div>'
    + '<div class="flt-sbd">' + fltSheetHtml(state.view === 'board' || state.view === 'rank') + '</div></div>';
}
/* ---- 筛选项计数：board/rank 基于默认真实数据作用域（只忽略正在计数的维度，
   默认页面不出现 400）；lib/insight 保持 V10 语义（选项来自全量 state.list）。 ---- */
function countByField(rows, field) {
  var name = (field === 'c2') ? '二级类目' : (field === 'c3') ? '三级类目'
    : (field === 'country') ? '国家/地区' : (field === 'market') ? '所属市场'
    : (field === 'cat') ? '品类' : field;
  var m = {}, i;
  for (i = 0; i < rows.length; i++) {
    var v = txtOf(rows[i], name);
    if (v) m[v] = (m[v] || 0) + 1;
  }
  var out = [], k;
  for (k in m) if (Object.prototype.hasOwnProperty.call(m, k)) out.push({ k: k, n: m[k] });
  out.sort(function (a, b) { return b.n - a.n; });
  return out;
}
function fltCountOf(dim) {
  if (!isBrView()) {
    if (dim === 'country') return countriesIn();
    if (dim === 'c2') return c2In();
    return srcsIn();
  }
  var ig = {};
  ig[dim] = 1;
  return countByField(boardRankDataOf({ ignore: ig }), dim === 'src' ? '数据来源' : dim);
}
function fltTotalOf() { return isBrView() ? boardRankDataOf().length : state.list.length; }
function fltStripHtml(showMore) {
  var h = '', i, j, q;
  var ms = marketsIn();
  h += '<button type="button" class="chip' + (state.market === '全部' ? ' on' : '') + '" data-f="market" data-v="全部">全部市场</button>';
  for (i = 0; i < ms.length; i++) {
    h += '<button type="button" class="chip' + (state.market === ms[i] ? ' on' : '') + '" data-f="market" data-v="' + esc(ms[i]) + '">' + esc(ms[i]) + '</button>';
  }
  h += '<span class="chip-sep"></span>';
  var cs = catsIn();
  h += '<button type="button" class="chip' + (state.cat === '全部' ? ' on' : '') + '" data-f="cat" data-v="全部">全部品类</button>';
  for (j = 0; j < cs.length; j++) {
    h += '<button type="button" class="chip' + (state.cat === cs[j] ? ' on' : '') + '" data-f="cat" data-v="' + esc(cs[j]) + '">' + esc(cs[j]) + '</button>';
  }
  h += '<span class="chip-sep"></span>';
  var ss = fltCountOf('src');
  h += '<button type="button" class="chip' + (state.src === '全部' ? ' on' : '') + '" data-f="src" data-v="全部">全部分来源</button>';
  for (q = 0; q < ss.length; q++) {
    h += '<button type="button" class="chip' + (state.src === ss[q].k ? ' on' : '') + '" data-f="src" data-v="' + esc(ss[q].k) + '">' + esc(ss[q].k) + ' <span class="cn">' + ss[q].n + '</span></button>';
  }
  h += '<span class="chip-sep"></span>';
  h += '<button type="button" class="chip' + (state.realOnly ? ' on' : '') + '" data-f="realOnly" data-v="' + (state.realOnly ? '0' : '1') + '">只看真实</button>';
  h += '<button type="button" class="chip' + (state.demoOnly ? ' on' : '') + '" data-f="demoOnly" data-v="' + (state.demoOnly ? '0' : '1') + '">只看示例</button>';
  h += '<div class="chip-row2">' + fltSelectHtml(showMore) + '</div>';
  return h;
}
function fltSelectHtml(showMore) {
  var h = '', i, j, p, t;
  h += '<label class="flt"><span>国家/地区</span><select class="flt-sel" data-f-sel="country">'
    + '<option value="全部"' + (state.country === '全部' ? ' selected' : '') + '>全部（' + fltTotalOf() + ' 个商品）</option>';
  var cos = fltCountOf('country');
  for (i = 0; i < cos.length; i++) {
    h += '<option value="' + esc(cos[i].k) + '"' + (state.country === cos[i].k ? ' selected' : '')
      + '>' + esc(cos[i].k) + '（' + cos[i].n + '）</option>';
  }
  h += '</select></label>';
  h += '<label class="flt"><span>二级类目</span><select class="flt-sel" data-f-sel="c2">'
    + '<option value="全部"' + (state.c2 === '全部' ? ' selected' : '') + '>全部细分</option>';
  var c2s = fltCountOf('c2');
  for (j = 0; j < c2s.length; j++) {
    h += '<option value="' + esc(c2s[j].k) + '"' + (state.c2 === c2s[j].k ? ' selected' : '')
      + '>' + esc(c2s[j].k) + '（' + c2s[j].n + '）</option>';
  }
  h += '</select></label>';
  if (showMore) {
    h += '<label class="flt"><span>三级类目</span><select class="flt-sel" data-f-sel="c3">'
      + '<option value="全部"' + (state.c3 === '全部' ? ' selected' : '') + '>全部三级</option>';
    var c3s = fltCountOf('c3');
    for (p = 0; p < c3s.length; p++) {
      h += '<option value="' + esc(c3s[p].k) + '"' + (state.c3 === c3s[p].k ? ' selected' : '')
        + '>' + esc(c3s[p].k) + '（' + c3s[p].n + '）</option>';
    }
    h += '</select></label>';
    h += '<label class="flt"><span>统计周期</span><select class="flt-sel" data-f-sel="period">'
      + '<option value="全部"' + (state.period === '全部' ? ' selected' : '') + '>全部周期</option>';
    var ps = periodIn(fltScopeRows('period'));
    for (t = 0; t < ps.length; t++) {
      h += '<option value="' + esc(ps[t]) + '"' + (state.period === ps[t] ? ' selected' : '') + '>' + esc(ps[t]) + '</option>';
    }
    h += '</select></label>';
  }
  if (state.country !== '全部') h += '<button type="button" class="chip" data-f="country" data-v="全部">清空国家</button>';
  if (state.c2 !== '全部') h += '<button type="button" class="chip" data-f="c2" data-v="全部">清空细分</button>';
  if (state.c3 !== '全部') h += '<button type="button" class="chip" data-f="c3" data-v="全部">清空三级</button>';
  if (state.period !== '全部') h += '<button type="button" class="chip" data-f="period" data-v="全部">清空周期</button>';
  return h;
}
/* 小屏抽屉：同样的条件竖排，触控目标 ≥44px */
function fltSheetHtml(showMore) {
  var h = '', i, j, q;
  var ms = marketsIn();
  h += '<div class="flt-row"><span class="flt-lb">大区</span><div class="flt-set">'
    + '<button type="button" class="chip' + (state.market === '全部' ? ' on' : '') + '" data-f="market" data-v="全部">全部</button>';
  for (i = 0; i < ms.length; i++) {
    h += '<button type="button" class="chip' + (state.market === ms[i] ? ' on' : '') + '" data-f="market" data-v="' + esc(ms[i]) + '">' + esc(ms[i]) + '</button>';
  }
  h += '</div></div>';
  var cs = catsIn();
  h += '<div class="flt-row"><span class="flt-lb">一级类目</span><div class="flt-set">'
    + '<button type="button" class="chip' + (state.cat === '全部' ? ' on' : '') + '" data-f="cat" data-v="全部">全部</button>';
  for (j = 0; j < cs.length; j++) {
    h += '<button type="button" class="chip' + (state.cat === cs[j] ? ' on' : '') + '" data-f="cat" data-v="' + esc(cs[j]) + '">' + esc(cs[j]) + '</button>';
  }
  h += '</div></div>';
  var ss = fltCountOf('src');
  h += '<div class="flt-row"><span class="flt-lb">平台 / 来源</span><div class="flt-set">'
    + '<button type="button" class="chip' + (state.src === '全部' ? ' on' : '') + '" data-f="src" data-v="全部">全部分来源</button>';
  for (q = 0; q < ss.length; q++) {
    h += '<button type="button" class="chip' + (state.src === ss[q].k ? ' on' : '') + '" data-f="src" data-v="' + esc(ss[q].k) + '">' + esc(ss[q].k) + ' ' + ss[q].n + '</button>';
  }
  h += '</div></div>';
  h += '<div class="flt-row"><span class="flt-lb">市场细分与统计周期</span>' + fltSelectHtml(showMore) + '</div>';
  h += '<div class="flt-row"><span class="flt-lb">数据口径</span><div class="flt-set">'
    + '<button type="button" class="chip' + (state.realOnly ? ' on' : '') + '" data-f="realOnly" data-v="' + (state.realOnly ? '0' : '1') + '">只看真实</button>'
    + '<button type="button" class="chip' + (state.demoOnly ? ' on' : '') + '" data-f="demoOnly" data-v="' + (state.demoOnly ? '0' : '1') + '">只看示例</button>'
    + '</div></div>';
  return h;
}
function fltSelList() {
  var out = [];
  if (state.market !== '全部') out.push(['market', '大区', state.market]);
  if (state.cat !== '全部') out.push(['cat', '品类', state.cat]);
  if (state.c2 !== '全部') out.push(['c2', '二级类目', state.c2]);
  if (state.c3 !== '全部') out.push(['c3', '三级类目', state.c3]);
  if (state.country !== '全部') out.push(['country', '国家/地区', state.country]);
  if (state.src !== '全部') out.push(['src', '来源', state.src]);
  if (state.period !== '全部') out.push(['period', '周期', state.period]);
  if (state.kw) out.push(['kw', '关键词', state.kw]);
  if (state.realOnly) out.push(['realOnly', '范围', '只看真实']);
  if (state.demoOnly) out.push(['demoOnly', '范围', '只看示例']);
  return out;
}
function fltSelCount() { return fltSelList().length; }
function fltSelChipsHtml() {
  var l = fltSelList(), h = '';
  for (var i = 0; i < l.length; i++) {
    var reset = (l[i][0] === 'realOnly' || l[i][0] === 'demoOnly') ? '0' : '';
    h += '<span class="flt-sc">' + esc(l[i][1]) + '：<b>' + esc(l[i][2]) + '</b>'
      + '<button type="button" data-f="' + esc(l[i][0]) + '" data-v="' + reset + '" aria-label="清除条件">×</button></span>';
  }
  return h;
}
/* 三级类目（看板 / 榜单中心） */
function c3In() {
  var m = {}, out = [], k, i;
  for (i = 0; i < state.list.length; i++) {
    var v = txtOf(state.list[i], '三级类目');
    if (v) m[v] = (m[v] || 0) + 1;
  }
  for (k in m) if (Object.prototype.hasOwnProperty.call(m, k)) out.push({ k: k, n: m[k] });
  out.sort(function (a, b) { return b.n - a.n; });
  return out;
}"""

# ================================================================ K. 看板
BOARD_OLD_START = 'RENDER.board = function () {'
BOARD_NEW = r"""/* ---------- v11 · 全球看板：回答「去哪里看」 ----------
   顺序：Hero → 真实数据覆盖（含新鲜度与缺失）→ 国家/地区 × 二级类目热力图（主区，可下钻）
        → 辅区（各国家样本结构 + 来源周期台账 + 数据质量）→ 覆盖度盲区 → 通路体检
        → 数据源地图 → 增长动能 × 竞争密度 → 大区样本结构 → 国家/地区市场
        → 二级类目稳健增长榜 → 概念 / 成分覆盖
   一切金额只按「单一来源 + 单一周期 + 原币」呈现，跨来源绝不合并。 ---------- */
RENDER.board = function () {
  var list = boardRankDataOf();
  var v = $('#view');
  if (!list.length) { v.innerHTML = diagHtml(list); return; }
  var h = '';
  h += heroHtml(list);
  h += boardTopHtml(list);
  h += heatSecHtml(list);
  h += auxSecHtml(list);
  h += '<div class="sec">' + secHd('市场 × 品类 覆盖度', '0 格就是盲区，本身就是结论', '') + covHtml(list) + '</div>';
  h += '<div class="sec">' + secHd('数据通路体检', '每个市场有没有源能供数，决定上面的结论算不算数', '')
    + flowHtml() + '</div>';
  h += srcMapSecHtml(list);
  h += scatterSecHtml(list);
  h += marketSecHtml(list);
  h += countrySecHtml(list);
  h += c2SecHtml(list);
  h += tagSecHtml(list);
  v.innerHTML = h;
};

function boardTopHtml(list) {
  var cty = {}, src = {}, c2 = {}, i;
  var asof = 0, sold = 0, gmv = 0, price = 0, rt = 0;
  for (i = 0; i < list.length; i++) {
    var r = list[i];
    cty[txtOf(r, '国家/地区') || '未标国家'] = 1;
    src[txtOf(r, '数据来源') || '未标来源'] = 1;
    c2[txtOf(r, '二级类目') || '未标细分'] = 1;
    if (asOfOf(r)) asof++;
    if (numField(r, '销量') !== null) sold++;
    if (numField(r, '销售额') !== null) gmv++;
    if (numField(r, '价格') !== null) price++;
    if (numField(r, '评分') !== null) rt++;
  }
  function cnt(o) { var n = 0, k; for (k in o) if (Object.prototype.hasOwnProperty.call(o, k)) n++; return n; }
  var g = growthStats(list), n = list.length;
  var cg = comparableGmv(list);
  var asofMax = '', asofN = 0, i2;
  for (i2 = 0; i2 < list.length; i2++) {
    var a0 = asOfOf(list[i2]);
    if (a0) { asofN++; if (a0 > asofMax) asofMax = a0; }
  }
  function item(lb, vl, ft) {
    return '<div class="card kpi"><div class="lb">' + esc(lb) + '</div><div class="vl">' + vl + '</div>'
      + '<div class="ft">' + ft + '</div></div>';
  }
  var h = '<div class="sec">' + secHd('真实数据覆盖', '这批数据覆盖到哪、什么时候的、缺什么',
    asofMax ? '数据截至 ' + esc(asofMax) : '数据截至：来源未标注');
  h += '<div class="grid g-kpi">';
  h += item('覆盖国家 / 地区', cnt(cty) + '<small>个</small>', '来源 ' + cnt(src) + ' 个 · 二级类目 ' + cnt(c2) + ' 个');
  h += item('榜单样本', n + '<small>条</small>', '全部为真实数据；40 条示例默认不计入，可切「只看示例」查看');
  h += item('稳健增长中枢', (g.med === null ? '—' : '<span class="' + pctCls(g.med) + '">' + fmtPct(g.med) + '</span>'),
    '中位数口径，剔除低基数样本' + (g.ex ? ' ' + g.ex + ' 条' : '') + '；有效增速样本 ' + g.n + '/' + n + ' 条');
  h += item('正增长占比', (g.pos === null ? '—' : g.pos + '%'), '在 ' + g.n + ' 条有效增速样本里，环比为正 ' + g.posN + ' 条');
  h += item('数据截至', (asofMax ? esc(asofMax) : '—'),
    asofMax ? esc('最新明确截至日；' + asofN + '/' + n + ' 条带明确截至日，其余来源未标注周期')
            : '所有来源都未标注统计周期与截至日');
  /* 金额单位来自国家→币种映射，不是硬编码「元」；推不出币种时 comparableGmv 直接不给合计 */
  h += item('可比样本 GMV', (cg.ok ? fmtNum(Math.round(cg.sum)) + '<small>' + esc(cg.unit) + '</small>' : '—'),
    cg.ok ? esc(cg.src + ' · ' + cg.country + '（' + cg.currency + '）· ' + cg.period + ' · ' + cg.n + ' 条 · 原币未折算')
          : esc(cg.reasons[0]));
  h += '</div>';
  h += '<div class="miss-note"><b>缺失情况：</b>' + esc(missingLine(n, { '销量': sold, '销售额': gmv, '价格': price, '评分': rt })) + '</div>';
  h += '<div class="miss-note"><b>为什么「可比样本 GMV」经常是「—」：</b>' + esc(cg.reasons.join('；')) + '。</div>';
  h += '</div>';
  return h;
}
function missingLine(n, pairs) {
  var out = [], k;
  for (k in pairs) if (Object.prototype.hasOwnProperty.call(pairs, k)) {
    var c = pairs[k];
    out.push(k + '缺 ' + (n - c) + '/' + n + (c ? '（有值 ' + c + ' 条按原币照录）' : ''));
  }
  return out.join('；') + '。缺失一律显示「—」，不当 0。';
}

function heatSecHtml(list) {
  var H = heatOf(list);
  var h = '<div class="sec">' + secHd('国家 / 地区 × 二级类目', '每格：样本数 + 稳健增长中枢（中位数）；点格子带筛选下钻榜单中心',
    H.rows.length + ' 个国家/地区 · ' + H.cols.length + ' 个二级类目');
  if (!H.rows.length) return h + emptyHtml('当前范围没有可画的国家 × 二级类目组合', '放宽筛选，或切到榜单中心按来源看') + '</div>';
  h += '<div class="card pad"><div class="heat-wrap"><div class="heat" style="grid-template-columns:136px repeat(' + H.cols.length + ',74px)">';
  h += '<div class="hc"></div>';
  for (var j = 0; j < H.cols.length; j++) h += '<div class="hc">' + esc(H.cols[j].k) + '</div>';
  for (var i = 0; i < H.rows.length; i++) {
    var cty = H.rows[i].country;
    h += '<div class="hr"><span class="dot" style="background:' + mktColor(H.rows[i].mkt) + '"></span>' + esc(cty) + '</div>';
    for (var k = 0; k < H.cols.length; k++) {
      var c2k = H.cols[k].k;
      var cell = H.grid[cty + '\u0001' + c2k];
      if (!cell) {
        h += '<div class="hcell z" title="' + esc(cty + ' · ' + c2k + '：库里一条数据都没有（覆盖盲区）') + '">无</div>';
        continue;
      }
      var g = growthStats(cell.rows);
      /* v11：深蓝「起量色」的资格判定与市场机会规则同门槛——
         中枢 ≥ MKT_MIN_GROWTH 且样本 ≥ MKT_MIN_SAMPLE 且正增长占比 ≥ MKT_MIN_POS。
         1~2 个样本把中位数顶到 +658% 的格子只给浅色：数字照实显示，但不当成集体起量信号。 */
      var hot = g.med !== null && g.med >= MKT_MIN_GROWTH
        && g.n >= MKT_MIN_SAMPLE && g.pos !== null && g.pos >= MKT_MIN_POS;
      var lv = (g.med === null || g.med <= 0) ? 'l0'
        : (hot ? 'l3' : (g.med >= MKT_MIN_GROWTH ? 'l1' : 'l2'));
      var tip = cty + ' · ' + c2k + '｜样本 ' + cell.n + ' 条｜有效增速样本 ' + g.n + ' 条｜稳健增长中枢 '
        + (g.med === null ? '—' : fmtPct(g.med)) + '（中位数）｜正增长 ' + (g.pos === null ? '—' : g.pos + '%')
        + (g.ex ? '｜已剔除低基数样本 ' + g.ex + ' 条' : '') + '｜含极端值中位数 ' + (g.medAll === null ? '—' : fmtPct(g.medAll))
        + (g.med !== null && g.med >= MKT_MIN_GROWTH && !hot
          ? '｜中枢虽高但样本 ' + g.n + ' 条 / 正增长 ' + (g.pos === null ? '—' : g.pos + '%') + ' 未过门槛，只当线索不当结论' : '');
      h += '<button type="button" class="hcell ' + lv + '" title="' + esc(tip) + '"'
        + ' data-drill="rank" data-d-country="' + esc(cty) + '" data-d-c2="' + esc(c2k) + '">'
        + '<b>' + (g.med === null ? '—' : fmtPct(g.med)) + '</b><i>' + cell.n + ' 个样本</i></button>';
    }
  }
  h += '</div></div></div>';
  h += '<div class="hint" style="margin-top:10px">大字是<b>稳健增长中枢</b>（中位数，已剔除低基数样本），小字是样本量；'
    + '斜纹「无」= 该组合一条数据都没有，是覆盖盲区不是没机会。'
    + '这里的分母是<b>榜单样本</b>，不是市场份额；点任意格子即带国家 + 细分筛到榜单中心。</div></div>';
  return h;
}

function auxSecHtml(list) {
  var H = heatOf(list), n = list.length || 1, i;
  var bars = H.rows.map(function (x) {
    return { k: x.country, v: x.tot, t: x.tot + ' 条 · ' + Math.round(x.tot / n * 100) + '%', color: mktColor(x.mkt) };
  });
  var h = '<div class="sec">' + secHd('各国家 / 地区样本结构', '条长 = 样本数；占比是榜单样本结构占比，不是市场份额', '')
    + '<div class="grid g-2">';
  h += '<div class="card pad">' + (bars.length ? hbarSvg(bars, { labelW: 92, valW: 96 })
    : '<div class="empty">当前范围没有样本</div>') + '</div>';
  h += '<div class="card pad"><div class="lbl-sm">数据质量提示</div><ul class="q-list">' + qualityList(list) + '</ul></div>';
  h += '</div>';
  h += '<div class="card" style="margin-top:14px"><div class="cmp-hd cmp-hd6"><span>来源</span><span>样本</span><span>统计周期</span><span>数据截至</span><span>金额可用</span><span>备注</span></div>';
  var by = {}, k;
  for (i = 0; i < list.length; i++) {
    var s = txtOf(list[i], '数据来源') || '未标来源';
    if (!by[s]) by[s] = { n: 0, per: {}, asof: '', gmv: 0 };
    by[s].n++;
    by[s].per[periodOf(list[i])] = 1;
    var a = asOfOf(list[i]); if (a && a > by[s].asof) by[s].asof = a;
    if (numField(list[i], '销售额') !== null) by[s].gmv++;
  }
  var keys = [];
  for (k in by) if (Object.prototype.hasOwnProperty.call(by, k)) keys.push(k);
  keys.sort(function (a, b) { return by[b].n - by[a].n; });
  if (!keys.length) h += '<div class="empty">当前范围没有来源</div>';
  for (i = 0; i < keys.length; i++) {
    var x = by[keys[i]], per = [];
    for (var q in x.per) if (Object.prototype.hasOwnProperty.call(x.per, q)) per.push(q);
    h += '<div class="cmp-r"><span><b>' + esc(keys[i]) + '</b></span><span>' + x.n + '</span>'
      + '<span class="cmp-sub">' + esc(per.join(' / ')) + '</span>'
      + '<span>' + (x.asof || '—') + '</span>'
      + '<span>' + x.gmv + '/' + x.n + '</span>'
      + '<span class="cmp-sub">' + esc(srcNote(keys[i])) + '</span></div>';
  }
  h += '</div>';
  h += '<div class="miss-note">「统计周期」来自各来源的实际口径，不是假设的「近 30 天」；金额可用 = 有销售额的样本数 / 该来源样本数。</div></div>';
  return h;
}
function qualityList(list) {
  var n = list.length || 1, i;
  var noAsOf = 0, noGmv = 0, noPrice = 0, noGrow = 0, noScore = 0, rankOnly = 0, lowBase = 0;
  for (i = 0; i < list.length; i++) {
    var r = list[i];
    if (!asOfOf(r)) noAsOf++;
    if (numField(r, '销售额') === null) noGmv++;
    if (numField(r, '价格') === null) noPrice++;
    if (numField(r, '环比增速') === null) noGrow++;
    if (numField(r, '评分') === null) noScore++;
    if (growExcluded(r) === '低基数') lowBase++;
    var d = srcDef(txtOf(r, '数据来源'));
    if (d && d.kind === 'kr') rankOnly++;
  }
  var g = growthStats(list);
  return '<li><b>数据截至日</b>：只有 ' + (n - noAsOf) + '/' + n + ' 条能给出（抖音罗盘的榜单文本里带周期），其余 ' + noAsOf
    + ' 条来源未标注周期 —— 所以不做跨来源的金额合并。</li>'
    + '<li><b>销售金额</b>：' + (n - noGmv) + '/' + n + ' 条有值（FastMoss 当前未结构化提供销售额），金额按原币照录；没有币种字段就不出跨国结论。</li>'
    + '<li><b>环比增速</b>：' + (n - noGrow) + '/' + n + ' 条有值；抖音罗盘商品榜单不提供环比增速，这些样本不参与增速类资格判定。</li>'
    + '<li><b>价格</b>：' + (n - noPrice) + '/' + n + ' 条有值；<b>评分 / 评价数</b>：' + (n - noScore) + '/' + n + ' 条有值（只有能按单品取数的来源才有）。</li>'
    + '<li><b>退货率</b>：三平台商品榜都不提供，全表为「—」，不参与任何规则。</li>'
    + '<li><b>低基数样本</b>：' + lowBase + ' 条属于「反推基期 < ' + GROW_BASE_MIN + ' 件」，已在资格判定与排序中剔除并打标，样本本身照常展示。</li>'
    + '<li><b>仅排名来源</b>：' + rankOnly + ' 条（Hwahae / Olive Young）只有名次与口碑，没有销量与金额，只当情报看。</li>'
    + '<li>本次范围 <b>' + g.n + '</b> 条有效增速样本，稳健增长中枢 <b>' + (g.med === null ? '—' : fmtPct(g.med))
    + '</b>，正增长 <b>' + g.posN + '</b> 条（' + (g.pos === null ? '—' : g.pos + '%') + '）。</li>';
}

function srcMapSecHtml(list) {
  var auto = 0, half = 0, man = 0, q;
  for (q = 0; q < FIELDS.length; q++) {
    if (FIELDS[q].src === 'manual') man++;
    else if (FIELDS[q].src === 'half') half++;
    else auto++;
  }
  var by = {}, i, k;
  for (i = 0; i < list.length; i++) {
    var s = txtOf(list[i], '数据来源') || '未标来源';
    by[s] = (by[s] || 0) + 1;
  }
  var keys = [];
  for (k in by) if (Object.prototype.hasOwnProperty.call(by, k)) keys.push(k);
  keys.sort(function (a, b) { return by[b] - by[a]; });
  var h = '<div class="sec">' + secHd('数据源地图', '全库 ' + FIELDS.length + ' 个字段：平台可导 ' + auto + ' 个 · 部分可导 ' + half + ' 个 · 只能人工标 ' + man + ' 个', '')
    + '<div class="card pad"><div class="src-sum">';
  for (i = 0; i < keys.length; i++) {
    var d = srcDef(keys[i]);
    h += '<div class="src-chip"><b>' + esc(keys[i]) + '</b><span>' + by[keys[i]] + ' 条 · '
      + esc(d ? d.markets.join(' / ') : '未登记') + '</span></div>';
  }
  h += '</div><div class="row-btns"><button type="button" class="mini" data-go="srcmap">看完整数据源地图（能拿什么 / 拿不到什么 / 取数路径）</button></div></div></div>';
  return h;
}

function scatterSecHtml(list) {
  var keep = [], ex = 0, i;
  for (i = 0; i < list.length; i++) {
    if (growExcluded(list[i]) === '低基数') { ex++; continue; }
    keep.push(list[i]);
  }
  var h = '<div class="sec">' + secHd('增长动能 × 竞争密度', '点越靠左上，越可能是窗口期', ex ? '已剔除 ' + ex + ' 个低基数样本' : '')
    + '<div class="card pad"><div class="legend">' + legendHtml() + '</div>' + scatterSvg(keep) + '</div>'
    + '<div class="hint" style="margin-top:9px">纵轴是<b>单品</b>环比增速（不是分组口径），横轴是关联达人数，气泡大小 = 销售额。'
    + (ex ? '反推基期 < ' + GROW_BASE_MIN + ' 件的 ' + ex + ' 个样本不进图，免得单点把坐标轴撑坏。' : '') + '</div></div>';
  return h;
}

function marketSecHtml(list) {
  var ms = marketStats(list);
  var bars = ms.map(function (m) {
    return { k: m.market, v: m.n, t: m.n + ' 条 · ' + m.share + '%', color: mktColor(m.market) };
  });
  var h = '<div class="sec">' + secHd('大区样本结构', '只比结构与稳健增速，不比金额（跨币种不可加）', '')
    + '<div class="card pad" style="margin-bottom:12px">'
    + (bars.length ? hbarSvg(bars, { labelW: 74, valW: 96 }) : '<div class="empty">当前范围没有样本</div>') + '</div>';
  h += '<div class="card"><div class="cmp-hd cmp-hd6"><span>大区</span><span>样本数</span><span>结构占比</span><span>稳健增长中枢</span><span>正增长占比</span><span>覆盖国家 / 地区</span></div>';
  for (var i = 0; i < ms.length; i++) {
    var m = ms[i];
    h += '<div class="cmp-r"><span><i class="dot" style="background:' + mktColor(m.market) + '"></i>' + esc(m.market) + '</span>'
      + '<span>' + m.n + '</span><span>' + m.share + '%</span>'
      + '<span class="' + pctCls(m.med) + '">' + (m.med === null ? '—' : fmtPct(m.med)) + '</span>'
      + '<span>' + (m.pos === null ? '—' : m.pos + '%') + '</span>'
      + '<span>' + m.ctyN + ' 个</span></div>';
  }
  h += '</div>';
  h += '<div class="miss-note">占比 = 该大区样本数 ÷ 当前范围样本数（榜单样本结构占比，不是市场份额）。'
    + '增速一律中位数口径，有效样本量与剔除情况见上文「数据质量提示」。</div></div>';
  return h;
}

function countrySecHtml(list) {
  var cn = countryStats(list);
  var h = '<div class="sec">' + secHd('国家 / 地区市场', '点一行即带国家筛到榜单中心', cn.length + ' 个国家 / 地区');
  h += '<div class="card"><div class="cmp-hd cmp-hd6"><span>国家 / 地区</span><span>样本数</span><span>结构占比</span><span>稳健增长中枢</span><span>正增长占比</span><span>主力细分</span></div>';
  for (var i = 0; i < cn.length; i++) {
    var c = cn[i];
    h += '<button type="button" class="cmp-r cmp-btn" data-drill="rank" data-d-country="' + esc(c.country) + '">'
      + '<span><i class="dot" style="background:' + mktColor(c.market) + '"></i>' + esc(c.country) + '</span>'
      + '<span>' + c.n + '</span><span>' + c.share + '%</span>'
      + '<span class="' + pctCls(c.med) + '">' + (c.med === null ? '—' : fmtPct(c.med)) + '</span>'
      + '<span>' + (c.pos === null ? '—' : c.pos + '%') + '</span>'
      + '<span class="cmp-sub">' + esc(c.topC2) + '</span></button>';
  }
  h += '</div>';
  h += '<div class="miss-note">占比是<b>榜单样本结构占比</b>（该国家样本数 ÷ 当前范围样本数），不是市场份额；'
    + '金额列已移除——各来源币种与周期不同，不做跨国金额对比。</div></div>';
  return h;
}

function c2SecHtml(list) {
  var c2s = boardC2Stats(list).filter(function (x) { return x.n >= 3 && x.avgGrowth !== null; });
  var bars = c2s.slice(0, 12).map(function (x) {
    return {
      k: x.c2, v: Math.max(0, x.avgGrowth),
      t: fmtPct(Math.round(x.avgGrowth * 10) / 10) + ' · ' + x.n + ' 个',
      color: x.avgGrowth >= MKT_MIN_GROWTH ? '#0E7C6B' : '#8E8E93'
    };
  });
  var h = '<div class="sec">' + secHd('二级类目稳健增长榜', '样本 ≥ 3 个的细分，条长 = 稳健增长中枢（中位数）', 'TOP 12')
    + '<div class="card pad">' + (bars.length ? hbarSvg(bars, { labelW: 100, valW: 104 })
      : '<div class="empty">这批数据里二级类目样本太散，放宽筛选再看</div>') + '</div>';
  h += '<div class="miss-note">排序用中位数而非均值：均值会被单条低基数新品拉爆（真实数据里有一条 +57725%）。'
    + '绿色 = 中枢 ≥ ' + MKT_MIN_GROWTH + '%，灰色 = 未到线。仅作赛道水位参考，不构成资格判定。</div></div>';
  return h;
}

function tagSecHtml(list) {
  var ct = tagStats(list, '概念标签').slice(0, 10);
  var ing = tagStats(list, '核心功效成分').slice(0, 10);
  function barsOf(arr, color) {
    return arr.map(function (x) {
      return { k: x.k, v: x.n, t: x.n + ' 个品' + (x.med === null ? ' · 中枢 —' : ' · 中枢 ' + fmtPct(x.med)), color: color };
    });
  }
  var h = '<div class="sec"><div class="grid g-2">';
  h += '<div><div class="sec-hd"><h2>概念覆盖 TOP10</h2><span>条长 = 样本数</span></div><div class="card pad">'
    + (ct.length ? hbarSvg(barsOf(ct, '#6E4BD1'), { labelW: 104, valW: 132 })
      : '<div class="empty">还没有填「概念标签」的数据</div>') + '</div></div>';
  h += '<div><div class="sec-hd"><h2>成分覆盖 TOP10</h2><span>条长 = 样本数</span></div><div class="card pad">'
    + (ing.length ? hbarSvg(barsOf(ing, '#0E7C6B'), { labelW: 104, valW: 132 })
      : '<div class="empty">还没有填「核心功效成分」的数据</div>') + '</div></div>';
  h += '</div>';
  h += '<div class="miss-note">这里只数样本、不算「带货力金额」——同一个概念横跨不同来源与币种，把钱加起来是错的。'
    + '要判断谁真的在赚钱，请到「榜单中心」按单一来源看。</div></div>';
  return h;
}"""

# ================================================================ L/M. 榜单
RANKTYPES_OLD = 'var RANK_TYPES = ['
RANKTYPES_NEW = r"""var RANK_TYPES = [
  { k: 'rank', n: '原始名次', hint: '按来源榜单的原始名次排' },
  { k: 'growth', n: '稳健增速', hint: '按环比增速排；低基数样本置底并标注' },
  { k: 'sold', n: '销量', hint: '按销量排，缺销量显示「—」并置底' },
  { k: 'sales', n: '销售额', hint: '按销售额排（原币），来源不提供金额时整列为「—」' },
  { k: 'kol', n: '达人密度', hint: '按关联达人数升序，越靠前越没人推' },
  { k: 'rating', n: '口碑', hint: '按评分排序，样本量不足的会标出来' },
  { k: 'fresh', n: '新品', hint: '按上市日期排序，越靠前越新' }
];
function rankDef(k) { for (var i = 0; i < RANK_TYPES.length; i++) { if (RANK_TYPES[i].k === k) return RANK_TYPES[i]; } return RANK_TYPES[0]; }
/* 榜单表格列定义；来源没有的列不渲染（见 rankColsOf） */
var RANK_COLS = [
  { k: 'no', n: '名次' },
  { k: 'prod', n: '商品' },
  { k: 'brand', n: '品牌' },
  { k: 'country', n: '国家/地区' },
  { k: 'cat', n: '品类' },
  { k: 'sold', n: '销量' },
  { k: 'gmv', n: '销售额' },
  { k: 'grow', n: '增速' },
  { k: 'asof', n: '数据截至' }
];
/* 某个来源这一榜实际渲染哪些列：
   - 排名型来源（Hwahae / Olive Young / KEV）只出真实具备的列；
   - 其它来源保留全部必需列，缺的字段单元格显示「—」，不推断、不填 0。 */
function rankColsOf(src) {
  var d = srcDef(src), cols = [], i, c;
  var rankOnly = !!(d && (d.kind === 'kr' || (d.kind === 'cn' && src === 'KEV美妆圈')));
  for (i = 0; i < RANK_COLS.length; i++) {
    c = RANK_COLS[i];
    if (rankOnly && (c.k === 'sold' || c.k === 'gmv' || c.k === 'grow' || c.k === 'asof')) continue;
    if (c.k === 'no' && !srcHas(src, 'no')) continue;
    /* v11：销量 / 金额 / 增速 / 数据截至 四列都按「来源可得性」决定出不出现。
       来源整列给不出的（如抖音罗盘无增速、FastMoss 与蝉妈妈无截至日），
       该列不渲染——与其排一整列「—」，不如不出这一列，缺什么在覆盖度条里说清。 */
    if ((c.k === 'sold' || c.k === 'gmv' || c.k === 'grow' || c.k === 'asof') && !srcHas(src, c.k)) continue;
    cols.push(c);
  }
  return cols;
}
function rankRows(list, by) {
  var out = list.slice();
  out.sort(function (a, b) {
    /* 只有「按增速排序」才把低基数样本置底（它的增速不能拿来比大小）；
       其余排序尊重该维度本身的大小关系——缺失值按缺失沉底，不做统一置底，
       「无增速」不能在原始名次 / 销量 / 销售额 / 评分排序里被强行压到末尾 */
    if (by === 'growth') {
      var ea = growExcluded(a) === '低基数' ? 1 : 0, eb = growExcluded(b) === '低基数' ? 1 : 0;
      if (ea !== eb) return ea - eb;
    }
    if (by === 'rank') {
      var ka = rankKeyOf(a), kb = rankKeyOf(b);
      return ka[0] - kb[0] || ka[1] - kb[1] || ka[2] - kb[2];
    }
    if (by === 'kol') {
      var ka = numField(a, '关联达人数'), kb = numField(b, '关联达人数');
      if (ka === null) ka = 999999;
      if (kb === null) kb = 999999;
      return ka - kb;
    }
    if (by === 'fresh') {
      var da = dayStr(a['上市日期']) || '0000', db2 = dayStr(b['上市日期']) || '0000';
      return db2 < da ? -1 : (db2 > da ? 1 : 0);
    }
    var map = { growth: '环比增速', sold: '销量', sales: '销售额', rating: '评分' };
    var f = map[by] || '环比增速';
    var va = numField(a, f), vb = numField(b, f);
    if (va === null) va = -999999999;
    if (vb === null) vb = -999999999;
    return vb - va;
  });
  return out;
}
function rankNoText(r) {
  var t = rankTextOf(r);
  return t ? '原榜 ' + t : '';
}
"""

RANK_NEW = r"""/* ---------- v11 · 榜单中心：回答「具体谁在卖」 ----------
   不同来源一律分榜（Tabs / 分来源），不生成跨来源混合总榜；
   每榜标注覆盖度 N/50、真实周期、缺失字段与原因；点商品即打开商品档案。 ---------- */
RENDER.rank = function () {
  var list = boardRankDataOf();
  var v = $('#view');
  var h = '';
  h += rankSrcTabs();
  h += rankSortTabs();
  if (!list.length) { v.innerHTML = h + diagHtml(list); return; }
  var groups = rankGroups(list);
  if (!groups.length) { v.innerHTML = h + emptyHtml('当前筛选下没有可排的榜单', '放宽国家 / 来源 / 类目再看'); return; }
  h += '<div class="hint" style="margin-bottom:12px">'
    + '<b>为什么必须分来源：</b>不同平台的统计周期与币种都不同（抖音罗盘是 7 天榜单快照、蝉妈妈是近 7 天日销口径、'
    + 'FastMoss 未标注周期、Hwahae / Olive Young 只公开名次），把它们揉成一个总榜等于把不可比的数字相加。'
    + '本期<b>没有任何来源提供「近 30 天」口径</b>，所以销量与金额按各来源的真实周期分列，不做跨来源合并。</div>';
  for (var i = 0; i < groups.length; i++) h += rankBoardHtml(groups[i], groups.length > 1);
  v.innerHTML = h;
};
function rankGroups(list) {
  var map = {}, order = [], i;
  for (i = 0; i < list.length; i++) {
    var s = txtOf(list[i], '数据来源') || '未标来源';
    if (!map[s]) { map[s] = []; order.push(s); }
    map[s].push(list[i]);
  }
  var out = [];
  for (i = 0; i < order.length; i++) out.push({ src: order[i], rows: map[order[i]] });
  return out;
}
/* 来源 Tabs：'全部' = 逐来源分榜（不是混合总榜） */
function rankSrcTabs() {
  var ss = srcCounts(boardRankDataOf({ ignore: { src: 1 } })), h = '<div class="rank-src">';
  h += '<button type="button" class="rank-tab' + (state.src === '全部' ? ' on' : '') + '" data-f="src" data-v="全部">分来源分榜</button>';
  for (var i = 0; i < ss.length; i++) {
    h += '<button type="button" class="rank-tab' + (state.src === ss[i].k ? ' on' : '') + '" data-f="src" data-v="' + esc(ss[i].k) + '">'
      + esc(ss[i].k) + ' <span class="cn">' + ss[i].n + '</span></button>';
  }
  h += '</div>';
  return h;
}
function rankSortTabs() {
  var h = '<div class="rank-tabs">';
  for (var i = 0; i < RANK_TYPES.length; i++) {
    var t = RANK_TYPES[i];
    h += '<button type="button" class="rank-tab' + (state.rankBy === t.k ? ' on' : '') + '" data-rank="' + t.k + '">' + esc(t.n) + '</button>';
  }
  h += '</div>';
  return h;
}
/* 一榜：覆盖度条 + 缺失说明 + 表格（列随来源可得性增减） */
function rankBoardHtml(g, multi) {
  var src = g.src, cols = rankColsOf(src);
  var rows = rankRows(g.rows, state.rankBy);
  var show = rows.slice(0, 50);
  var hint = (rankDef(state.rankBy).hint || '') + ' · 收录 ' + rows.length + ' 条，展示前 ' + Math.min(rows.length, 50) + ' 条（Top50 目标）';
  var h = '<div class="sec rank-sec">' + secHd('『' + src + '』榜', hint + (multi ? '' : ' · 已按来源筛选'), '共 ' + rows.length + ' 条');
  h += covBarHtml(src, g.rows, show.length);
  h += '<div class="card" style="padding:12px 4px 4px"><div class="rkt-wrap"><table class="rkt"><thead><tr>';
  for (var c = 0; c < cols.length; c++) h += '<th>' + esc(rankHead(cols[c], src)) + '</th>';
  h += '</tr></thead><tbody>';
  for (var i = 0; i < show.length; i++) {
    var r = show[i], ex = growExcluded(r) === '低基数';
    h += '<tr' + (ex ? ' class="ex"' : '') + '>';
    for (var j = 0; j < cols.length; j++) h += rankCell(cols[j], r, src, i + 1);
    h += '</tr>';
  }
  h += '</tbody></table></div></div>';
  h += '<div class="miss-note">缺失字段与原因：' + esc(srcNote(src)) + '。缺失一律显示「—」，不当 0，也不做推测填充。';
  h += ' 名次列显示来源原始名次（「第N名」，或抓取序「第P页第Q位」——分页位次不等于全局名次）。';
  if (exCount(g.rows)) h += ' 本榜有 <b>' + exCount(g.rows) + '</b> 条低基数样本（反推基期 < ' + GROW_BASE_MIN + ' 件），已打标；仅在「按增速排序」时置底，不参与增速类资格判定。';
  h += '</div></div>';
  return h;
}
function exCount(rows) {
  var n = 0;
  for (var i = 0; i < rows.length; i++) if (growExcluded(rows[i]) === '低基数') n++;
  return n;
}
function rankHead(col, src) {
  if (col.k === 'no') return state.rankBy === 'rank' ? '名次（原榜）' : '排序位';
  if (col.k === 'sold') return '销量 · ' + periodShort(src);
  if (col.k === 'gmv') return '销售额（原币）· ' + periodShort(src);
  return col.n;
}
/* 覆盖度条：N/50 + 有值字段数 + 数据截至 */
function covBarHtml(src, rows, shown) {
  var sold = 0, gmv = 0, grow = 0, asof = '', i;
  for (i = 0; i < rows.length; i++) {
    if (numField(rows[i], '销量') !== null) sold++;
    if (numField(rows[i], '销售额') !== null) gmv++;
    if (numField(rows[i], '环比增速') !== null) grow++;
    var a = asOfOf(rows[i]); if (a && a > asof) asof = a;
  }
  var h = '<div class="cov-bar">'
    + '<span class="pill">收录 <b>' + rows.length + '</b> 条 · Top50 目标</span>'
    + '<span class="pill">展示 <b>' + shown + '</b> 条</span>';
  if (srcHas(src, 'sold')) h += '<span class="pill">有销量 <b>' + sold + '/' + rows.length + '</b></span>';
  if (srcHas(src, 'gmv')) h += '<span class="pill">有金额 <b>' + gmv + '/' + rows.length + '</b></span>';
  if (srcHas(src, 'grow')) h += '<span class="pill">有增速 <b>' + grow + '/' + rows.length + '</b></span>';
  h += '<span class="pill">周期 <b>' + esc(periodShort(src)) + '</b></span>'
    + '<span class="pill">数据截至 <b>' + (asof || '—（来源未标注）') + '</b></span>'
    + '</div>';
  return h;
}
function rankCell(col, r, src, no) {
  if (col.k === 'no') {
    if (state.rankBy === 'rank') {
      var n0 = rankNoOf(r), pg0 = rankPageOf(r);
      var t0 = (n0 !== null) ? String(n0) : (pg0 ? pg0.page + '页' + pg0.pos + '位' : '—');
      return '<td class="rkno' + (n0 !== null && n0 <= 3 ? ' top' : '') + '" data-l="名次" title="'
        + esc(rankTextOf(r)) + '">' + t0 + '</td>';
    }
    return '<td class="rkno" data-l="排序位">' + no + '</td>';
  }
  if (col.k === 'prod') {
    var bd = growExcluded(r) === '低基数' ? '<span class="bdg">低基数</span>' : '';
    var meta = [];
    var o = rankNoText(r); if (o) meta.push(o);
    var cat2 = txtOf(r, '二级类目'); if (cat2) meta.push(cat2);
    var c3 = txtOf(r, '三级类目'); if (c3 && c3 !== cat2) meta.push(c3);
    if (isNewProd(r)) meta.push('新品');
    return '<td class="pc" data-l="商品"><button type="button" class="lnk pname" data-open="' + esc(ridOf(r)) + '">'
      + esc(txtOf(r, '商品名称') || '未命名') + '</button>' + bd
      + '<div class="pmeta">' + esc(meta.join(' · ')) + '</div></td>';
  }
  if (col.k === 'brand') return '<td data-l="品牌">' + esc(txtOf(r, '品牌') || '—') + '</td>';
  if (col.k === 'country') return '<td data-l="国家">' + esc(txtOf(r, '国家/地区') || '—') + '</td>';
  if (col.k === 'cat') {
    var a = txtOf(r, '品类'), b2 = txtOf(r, '二级类目');
    return '<td data-l="品类">' + esc(a ? (a + (b2 ? ' / ' + b2 : '')) : '—') + '</td>';
  }
  if (col.k === 'sold') {
    var s = numField(r, '销量');
    return '<td class="num" data-l="销量">' + (s === null ? '—' : fmtNum(s)) + '</td>';
  }
  if (col.k === 'gmv') {
    var v = numField(r, '销售额');
    return '<td class="num" data-l="销售额">' + (v === null ? '—' : fmtNum(v)) + '</td>';
  }
  if (col.k === 'grow') {
    var g = numField(r, '环比增速');
    if (g === null) return '<td class="num" data-l="增速">—</td>';
    var ex = growExcluded(r) === '低基数';
    return '<td class="num" data-l="增速"><span class="' + (ex ? 'muted' : pctCls(g)) + '">' + fmtPct(g) + '</span></td>';
  }
  if (col.k === 'asof') {
    var a2 = asOfOf(r);
    return '<td data-l="截至">' + (a2 ? esc(a2) : '—') + '<div class="pmeta">' + esc(periodOf(r)) + '</div></td>';
  }
  return '<td></td>';
}"""

# ================================================================ 补丁表
REPLACES = [
    ('A CSS', '</style>', CSS_ADD + '</style>'),
    ('B state', """  market: '全部', cat: '全部', c2: '全部', country: '全部', kw: '', src: '全部', rankBy: 'growth',
  busy: false, demoOnly: false, realOnly: false, libTab: 'cat', expL1: {}, expL2: {}""",
     """  market: '全部', cat: '全部', c2: '全部', c3: '全部', country: '全部', kw: '', src: '全部',
  period: '全部', rankBy: 'rank', fltOpen: '0',
  busy: false, demoOnly: false, realOnly: false, libTab: 'cat', expL1: {}, expL2: {}"""),
    ('C 引擎', 'RENDER.nav = function () {', ENGINE + 'RENDER.nav = function () {'),
    ('H 门槛常量', 'var MKT_MIN_GROWTH = 60;      /* 市场机会：格子平均增速门槛 */',
     'var MKT_MIN_GROWTH = 60;      /* 市场机会：格子稳健增长中枢门槛（v11 起为剔低基数后的中位数） */\nvar MKT_MIN_POS = 50;         /* 市场机会：正增长占比门槛（v11 新增，防单点拉出的「集体起量」误判） */'),
    ('I heroStat', HERO_STAT_OLD, HERO_STAT_NEW),
    ('J 下钻 / 收抽屉',
     "    if (el.hasAttribute('data-view')) { state.view = el.getAttribute('data-view'); closeAll(); refreshAll(); return; }",
     """    if (el.hasAttribute('data-view')) { state.view = el.getAttribute('data-view'); state.fltOpen = '0'; closeAll(); refreshAll(); return; }
    if (el.hasAttribute('data-drill')) {
      /* 热力格 / 国家行下钻：继承当前筛选，只叠加国家与（二级/一级）类目 */
      var dc = el.getAttribute('data-d-country'), dc2 = el.getAttribute('data-d-c2'), dcat = el.getAttribute('data-d-cat');
      if (dc !== null) state.country = dc || '全部';
      if (dc2 !== null) state.c2 = dc2 || '全部';
      if (dcat !== null) state.cat = dcat || '全部';
      state.view = 'rank'; state.fltOpen = '0'; closeAll(); refreshAll(); return;
    }"""),
    ('J2 委托选择器',
     "    var el = e.target && e.target.closest ? e.target.closest('[data-view],[data-f],[data-rank],[data-open],[data-close],[data-go]') : null;",
     "    var el = e.target && e.target.closest ? e.target.closest('[data-view],[data-f],[data-rank],[data-open],[data-close],[data-go],[data-drill]') : null;"),
    # ---- 口径统一：所有显示中位数的入口都改成同一个稳健口径，文案同步改 ----
    ('P9 注释口径 1', '/* 国家/地区维度：商品数、销售额、平均增速、平均达人、主力细分 */',
     '/* 国家/地区维度（v11 起）：样本数、样本结构占比、稳健增长中枢、正增长占比、来源与主力细分 */'),
    ('T 标题计数', """  var n = dataOf().length;
  $('#viewTitle').textContent = v.name;""",
     """  /* v11·复审：board/rank 用默认真实数据口径；lib/insight/review 保持 V10 */
  var n = isBrView() ? boardRankDataOf().length : dataOf().length;
  $('#viewTitle').textContent = v.name;"""),
    ('T 导出作用域', """function rowsForExport() {
  var list = dataOf(), out = [];""",
     """function rowsForExport() {
  var list = isBrView() ? boardRankDataOf() : dataOf(), out = [];"""),
    ('K 视图描述', "{ key: 'board', name: '全球看板', desc: '增长动能、竞争密度、价格带与概念带货力',",
     "{ key: 'board', name: '全球看板', desc: '全球覆盖、类目热度与来源分榜',"),
    ('J3 选择器委托上移',
     """  $('#chips').addEventListener('change', function (e) {
    var el = e.target;
    if (!el || !el.getAttribute) return;
    var f = el.getAttribute('data-f-sel');
    if (!f) return;
    state[f] = el.value;
    refreshAll();
  });""",
     """  /* v11：筛选抽屉挂在 body 直下的 #fltLayer（topbar 有 backdrop-filter，会劫持 fixed 包含块），
     选择器委托必须提到 document 层才能接住抽屉里的下拉 */
  document.addEventListener('change', function (e) {
    var el = e.target;
    if (!el || !el.getAttribute) return;
    var f = el.getAttribute('data-f-sel');
    if (!f) return;
    state[f] = el.value;
    refreshAll();
  });"""),
]

# (name, start_marker, old_block_or_None, new_text, term, keep_term)
#   term       = 原文的终止串（函数声明 '\n}' / 赋值 '\n};' / 自定义标记）
#   keep_term  = True 时终止串保留、不纳入替换范围（用于 "到下一个函数为止" 的切片）
SPLICES = [
    ('E countryStats', 'function countryStats(list) {', COUNTRY_OLD, COUNTRY_NEW, '\n}', False),
    ('F marketStats', 'function marketStats(list) {', MARKET_OLD, MARKET_NEW, '\n}', False),
    ('I heroHtml', 'function heroHtml(list) {', HERO_OLD, HERO_NEW, '\n}', False),
    ('J RENDER.filter', 'RENDER.filter = function () {', FILTER_OLD, FILTER_NEW, '\n};', False),
    ('K RENDER.board', 'RENDER.board = function () {', None, BOARD_NEW, '\n};', False),
    ('L RANK_TYPES', 'var RANK_TYPES = [', None, RANKTYPES_NEW, 'RENDER.rank = function () {', True),
    ('M RENDER.rank', 'RENDER.rank = function () {', None, RANK_NEW, '\n};', False),
]


def fit_term(text, term):
    """让新代码块以与原文一致的终止符结尾（'\n}' 或 '\n};'）。"""
    t = text.rstrip('\n')
    core = term.strip('\n')
    if core == '};':
        if not t.endswith('};'):
            t = (t + ';') if t.endswith('}') else (t + '};')
    else:
        if not t.endswith('}'):
            t = t + '}'
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--target', default=DEFAULT_TARGET)
    a = ap.parse_args()
    target = os.path.abspath(a.target)
    src = io.open(target, encoding='utf-8').read()

    bad = []
    for name, old, _new in REPLACES:
        n = src.count(old)
        if n != 1:
            bad.append(('替换 ' + name, n, (old.splitlines() or [''])[0][:70]))
    for name, start, old, _new, term, keep in SPLICES:
        if src.count(start) != 1:
            bad.append(('切片 ' + name + ' 起点', src.count(start), start[:70]))
        if old is not None and src.count(old) != 1:
            bad.append(('切片 ' + name + ' 旧文', src.count(old), (old.splitlines() or [''])[0][:70]))
        if term.startswith('\n'):
            if src.count(term) < 1:
                bad.append(('切片 ' + name + ' 终止符', src.count(term), repr(term)))
        elif src.count(term) != 1:
            bad.append(('切片 ' + name + ' 终止符', src.count(term), term[:70]))
        _ = keep
    if bad:
        print('!! 以下补丁未唯一命中，中止：')
        for name, n, head in bad:
            print('   %-22s 命中 %d 次 | %s' % (name, n, head))
        return 1
    print('%d 处替换 + %d 处整段切片 全部唯一命中（%s）'
          % (len(REPLACES), len(SPLICES), os.path.basename(target)))

    if not a.apply:
        print('（dry-run，未写入；加 --apply 执行）')
        return 0

    out = src
    for _name, old, new in REPLACES:
        out = out.replace(old, new, 1)
    for _name, start, _old, new, term, keep in SPLICES:
        i = out.index(start)
        if keep:
            j = out.index(term, i)
            body = fit_term(new, '\n}') + '\n\n'
        else:
            j = out.index(term, i) + len(term)
            body = fit_term(new, term)
        out = out[:i] + body + out[j:]

    # 在位性校验：关键新符号必须真的落进产物
    need = ['function growthStats', 'function heatOf', 'function rankColsOf', 'function comparableGmv',
            'flt-sheet', 'RANK_COLS', 'MKT_MIN_POS', 'data-drill', 'rankSrcTabs',
            'function boardRankDataOf', 'function boardC2Stats', 'function boardInsightsOf',
            'function currencyOf', 'function rankKeyOf', 'function rankPageOf', 'fltLayer',
            'flt-lock', 'CURRENCY_BY_COUNTRY']
    miss = [x for x in need if x not in out]
    if miss:
        print('!! 写入后校验失败，缺：%s' % miss)
        return 1
    io.open(target, 'w', encoding='utf-8').write(out)
    print('已写入 %s（%d -> %d 字节，+%d）' % (target, len(src), len(out), len(out) - len(src)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
