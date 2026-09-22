#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页面 v8 补丁：国家市场 + 三级品类细分 + 成分库 + 4 条新洞察规则。

设计原则（沿用既有架构约定）：
  - 渲染函数之间严禁互调；所有交互 -> 改 state -> refreshAll() 单向重绘
  - 展开状态放在 state.expL1 / expL2，渲染只读不写
  - 不引任何外链，图表仍是内联 SVG

用法：
  python3 patch_page_v8.py                                  # 打本地页面
  python3 patch_page_v8.py --in X --out Y                   # 打任意件（线上基线也走这里）
"""
import argparse
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def replace_between(html, start, end, new, tag):
    i = html.find(start)
    if i < 0:
        return None
    j = html.find(end, i + len(start))
    if j < 0:
        return None
    return html[:i] + new + html[j:], tag


# ============================================================ 1. 新字段
F_FIELDS = [
    ("  { n: '细分品类', t: 'text', g: '商品主数据', src: 'auto' },",
     "  { n: '细分品类', t: 'text', g: '商品主数据', src: 'auto' },\n"
     "  { n: '二级类目', t: 'text', g: '商品主数据', src: 'auto', hint: '功能子类，如 底妆 / 面部清洁 / 身体清洁' },\n"
     "  { n: '三级类目', t: 'text', g: '商品主数据', src: 'auto', hint: '平台最细类目，如 遮瑕与粉底 / 沐浴露与香皂' },\n"
     "  { n: '类目ID', t: 'text', g: '商品主数据', src: 'auto', hint: '平台类目 cid 链（14/848648/601554），按它可精确复现取数' },",
     'field-cat'),

    ("  { n: '所属市场', t: 'select', g: '平台数据', src: 'auto', opts: ['中国', '韩国', '日本', '欧美', '东南亚'] },",
     "  { n: '所属市场', t: 'select', g: '平台数据', src: 'auto', opts: ['中国', '韩国', '日本', '欧美', '东南亚'] },\n"
     "  { n: '国家/地区', t: 'select', g: '平台数据', src: 'auto', hint: '平台原始 region，比「所属市场」大区细一级',"
     " opts: ['中国', '美国', '印度尼西亚', '泰国', '越南', '菲律宾', '马来西亚', '新加坡', '日本', '英国', '德国', '法国',"
     " '意大利', '西班牙', '巴西', '墨西哥', '奥地利', '比利时', '荷兰', '波兰', '葡萄牙'] },",
     'field-country'),

    ("  { n: '核心功效成分', t: 'text', g: '成分与功效', src: 'manual' },",
     "  { n: '核心功效成分', t: 'text', g: '成分与功效', src: 'auto',"
     " hint: '从商品标题抽出的显性成分词——标题没写就留空，不做推测' },",
     'field-ing'),
]

# ============================================================ 2. state
E_STATE = (
    "  market: '全部', cat: '全部', kw: '', src: '全部', rankBy: 'growth', busy: false, demoOnly: false, realOnly: false",
    "  market: '全部', cat: '全部', c2: '全部', country: '全部', kw: '', src: '全部', rankBy: 'growth',\n"
    "  busy: false, demoOnly: false, realOnly: false, libTab: 'cat', expL1: {}, expL2: {}",
    'state')

# ============================================================ 3. dataOf 筛选
E_DATAOF = (
    "    if (state.cat !== '全部' && txtOf(r, '品类') !== state.cat) continue;\n"
    "    if (state.src !== '全部' && txtOf(r, '数据来源') !== state.src) continue;",
    "    if (state.cat !== '全部' && txtOf(r, '品类') !== state.cat) continue;\n"
    "    if (state.c2 !== '全部' && txtOf(r, '二级类目') !== state.c2) continue;\n"
    "    if (state.country !== '全部' && txtOf(r, '国家/地区') !== state.country) continue;\n"
    "    if (state.src !== '全部' && txtOf(r, '数据来源') !== state.src) continue;",
    'dataof-filter')

E_KW = (
    "      var hay = [txtOf(r, '商品名称'), txtOf(r, '品牌'), txtOf(r, '概念标签'), txtOf(r, '核心功效成分'),\n"
    "        txtOf(r, '细分品类'), txtOf(r, '功效宣称'), txtOf(r, '差评关键词')].join(' ').toLowerCase();",
    "      var hay = [txtOf(r, '商品名称'), txtOf(r, '品牌'), txtOf(r, '概念标签'), txtOf(r, '核心功效成分'),\n"
    "        txtOf(r, '细分品类'), txtOf(r, '二级类目'), txtOf(r, '三级类目'), txtOf(r, '国家/地区'),\n"
    "        txtOf(r, '功效宣称'), txtOf(r, '差评关键词')].join(' ').toLowerCase();",
    'kw-hay')

# ============================================================ 4. 聚合工具
HELPERS = r'''/* ---------- 6b. 国家 / 品类细分 聚合（只做计算，不碰 DOM） ---------- */
function avgArr(a) {
  if (!a || !a.length) return null;
  var s = 0; for (var i = 0; i < a.length; i++) s += a[i];
  return s / a.length;
}
function topKey(o, n) {
  var out = [], k;
  for (k in o) if (Object.prototype.hasOwnProperty.call(o, k)) out.push([k, o[k]]);
  out.sort(function (a, b) { return b[1] - a[1]; });
  return out.slice(0, n || 1).map(function (x) { return x[0]; });
}
/* 库里实际出现的国家/地区，按条数排 */
function countriesIn() {
  var m = {}, i;
  for (i = 0; i < state.list.length; i++) {
    var v = txtOf(state.list[i], '国家/地区');
    if (v) m[v] = (m[v] || 0) + 1;
  }
  var out = [], k;
  for (k in m) if (Object.prototype.hasOwnProperty.call(m, k)) out.push({ k: k, n: m[k] });
  out.sort(function (a, b) { return b.n - a.n; });
  return out;
}
/* 库里实际出现的二级类目（功能子类） */
function c2In() {
  var m = {}, i;
  for (i = 0; i < state.list.length; i++) {
    var v = txtOf(state.list[i], '二级类目');
    if (v) m[v] = (m[v] || 0) + 1;
  }
  var out = [], k;
  for (k in m) if (Object.prototype.hasOwnProperty.call(m, k)) out.push({ k: k, n: m[k] });
  out.sort(function (a, b) { return b.n - a.n; });
  return out;
}
/* 国家/地区维度：商品数、销售额、平均增速、平均达人、主力细分 */
function countryStats(list) {
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
      sales: x.sn ? x.sales : null,          /* 一个有销售额的都没有就显示 —，别拿 0 冒充 */
      avgGrowth: ag, avgKol: ak === null ? null : Math.round(ak), topC2: tk.join(' / ') || '—'
    });
  }
  out.sort(function (a, b) { return b.sales - a.sales; });
  return out;
}
/* 二级类目维度：按平均增速排，用来找「在涨的赛道」 */
function c2Stats(list) {
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
      c2: x.c2, l1: x.l1, n: x.n, sales: x.sales, avgGrowth: avgArr(x.gs),
      c3n: Object.keys(x.c3).length, ctn: Object.keys(x.ct).length,
      topC3: topKey(x.c3, 3).join(' / ') || '—'
    });
  }
  out.sort(function (a, b) {
    return (b.avgGrowth === null ? -1e9 : b.avgGrowth) - (a.avgGrowth === null ? -1e9 : a.avgGrowth);
  });
  return out;
}
/* 三级品类树：一级业务大类 → 二级功能子类 → 三级平台类目，带展开态 */
function catTreeHtml(list) {
  var l1 = {}, i;
  for (i = 0; i < list.length; i++) {
    var r = list[i];
    var a = txtOf(r, '品类') || '未归类', b = txtOf(r, '二级类目') || '未归类', c = txtOf(r, '三级类目') || '未归类';
    var g = numField(r, '环比增速');
    if (!l1[a]) l1[a] = { n: 0, gs: [], c2: {} };
    l1[a].n++; if (g !== null) l1[a].gs.push(g);
    if (!l1[a].c2[b]) l1[a].c2[b] = { n: 0, gs: [], c3: {} };
    l1[a].c2[b].n++; if (g !== null) l1[a].c2[b].gs.push(g);
    if (!l1[a].c2[b].c3[c]) l1[a].c2[b].c3[c] = { n: 0, gs: [] };
    l1[a].c2[b].c3[c].n++; if (g !== null) l1[a].c2[b].c3[c].gs.push(g);
  }
  var keys = Object.keys(l1).sort(function (x, y) { return l1[y].n - l1[x].n; });
  var h = '<div class="card pad">';
  for (var i1 = 0; i1 < keys.length; i1++) {
    var k1 = keys[i1], v1 = l1[k1], ag1 = avgArr(v1.gs), o1 = !!state.expL1[k1];
    h += '<div class="ct-node">'
      + '<button type="button" class="ct-hd' + (o1 ? ' on' : '') + '" data-exp="l1" data-expk="' + esc(k1) + '">'
      + '<span class="ct-arw">' + (o1 ? '−' : '+') + '</span>'
      + '<span class="ct-nm">' + esc(k1) + '</span>'
      + '<span class="ct-n">' + v1.n + ' 个</span>'
      + '<span class="ct-g ' + pctCls(ag1) + '">' + fmtPct(ag1 === null ? null : Math.round(ag1)) + '</span>'
      + '</button>';
    if (o1) {
      var k2s = Object.keys(v1.c2).sort(function (x, y) { return v1.c2[y].n - v1.c2[x].n; });
      for (var j2 = 0; j2 < k2s.length; j2++) {
        var k2 = k2s[j2], v2 = v1.c2[k2], ag2 = avgArr(v2.gs), key2 = k1 + '>' + k2, o2 = !!state.expL2[key2];
        h += '<div class="ct-node lv2">'
          + '<button type="button" class="ct-hd' + (o2 ? ' on' : '') + '" data-exp="l2" data-expk="' + esc(key2) + '">'
          + '<span class="ct-arw">' + (o2 ? '−' : '+') + '</span>'
          + '<span class="ct-nm">' + esc(k2) + '</span>'
          + '<span class="ct-n">' + v2.n + ' 个</span>'
          + '<span class="ct-g ' + pctCls(ag2) + '">' + fmtPct(ag2 === null ? null : Math.round(ag2)) + '</span>'
          + '</button>';
        if (o2) {
          var k3s = Object.keys(v2.c3).sort(function (x, y) { return v2.c3[y].n - v2.c3[x].n; });
          for (var q3 = 0; q3 < k3s.length; q3++) {
            var k3 = k3s[q3], v3 = v2.c3[k3], ag3 = avgArr(v3.gs);
            h += '<div class="ct-row lv3">'
              + '<span class="ct-nm">' + esc(k3) + '</span>'
              + '<span class="ct-n">' + v3.n + ' 个</span>'
              + '<span class="ct-g ' + pctCls(ag3) + '">' + fmtPct(ag3 === null ? null : Math.round(ag3)) + '</span>'
              + '</div>';
          }
        }
        h += '</div>';
      }
    }
    h += '</div>';
  }
  h += '</div>';
  return h;
}
/* 成分库：按出现商品数排，附覆盖类目 / 中位增速 / 代表商品 */
function ingStats(list) {
  var m = {}, i, j;
  for (i = 0; i < list.length; i++) {
    var r = list[i], arr = splitTags(txtOf(r, '核心功效成分'), ' / ');
    if (!arr.length) continue;
    var g = numField(r, '环比增速');
    for (j = 0; j < arr.length; j++) {
      var k = arr[j];
      if (!k) continue;
      var a = m[k];
      if (!a) a = m[k] = { ing: k, n: 0, gs: [], sales: 0, c2: {}, c3: {}, ct: {}, eg: [] };
      a.n++;
      a.sales += numField(r, '销售额') || 0;
      if (g !== null) a.gs.push(g);
      var c2 = txtOf(r, '二级类目'); if (c2) a.c2[c2] = (a.c2[c2] || 0) + 1;
      var c3 = txtOf(r, '三级类目'); if (c3) a.c3[c3] = (a.c3[c3] || 0) + 1;
      var ct = txtOf(r, '国家/地区'); if (ct) a.ct[ct] = (a.ct[ct] || 0) + 1;
      if (a.eg.length < 2) a.eg.push({ n: txtOf(r, '商品名称') || '未命名', id: ridOf(r), ct: ct || '—' });
    }
  }
  var out = [], c;
  for (c in m) {
    if (!Object.prototype.hasOwnProperty.call(m, c)) continue;
    var x = m[c], gs = x.gs.slice().sort(function (a, b) { return a - b; });
    out.push({
      ing: x.ing, n: x.n, sales: x.sales, avgGrowth: avgArr(x.gs),
      medianGrowth: gs.length ? gs[Math.floor(gs.length / 2)] : null,
      maxGrowth: gs.length ? gs[gs.length - 1] : null,
      c2: topKey(x.c2, 3), c3: topKey(x.c3, 3), ct: topKey(x.ct, 4),
      c3n: Object.keys(x.c3).length, ctn: Object.keys(x.ct).length, eg: x.eg
    });
  }
  out.sort(function (a, b) { return b.n - a.n || (b.medianGrowth === null ? -1e9 : b.medianGrowth) - (a.medianGrowth === null ? -1e9 : a.medianGrowth); });
  return out;
}

'''
E_HELPERS = ("function srcsIn() {", HELPERS + "function srcsIn() {", 'helpers')

# ============================================================ 5. RENDER.filter 第二行
E_FILTER = (
    "  h += '<button type=\"button\" class=\"chip' + (state.demoOnly ? ' on' : '') + '\" data-f=\"demoOnly\" data-v=\"'"
    " + (state.demoOnly ? '0' : '1') + '\">只看示例</button>';\n  $('#chips').innerHTML = h;\n};",
    "  h += '<button type=\"button\" class=\"chip' + (state.demoOnly ? ' on' : '') + '\" data-f=\"demoOnly\" data-v=\"'"
    " + (state.demoOnly ? '0' : '1') + '\">只看示例</button>';\n"
    "  /* 第二行：国家/地区 + 二级类目细分。二级类目取值多，用下拉不铺 chip，手机上一行放得下 */\n"
    "  h += '<div class=\"chip-row2\">';\n"
    "  h += '<label class=\"flt\"><span>国家/地区</span><select class=\"flt-sel\" data-f-sel=\"country\">'\n"
    "    + '<option value=\"全部\"' + (state.country === '全部' ? ' selected' : '') + '>全部（' + state.list.length + ' 个商品）</option>';\n"
    "  var cos = countriesIn();\n"
    "  for (var ci = 0; ci < cos.length; ci++) {\n"
    "    h += '<option value=\"' + esc(cos[ci].k) + '\"' + (state.country === cos[ci].k ? ' selected' : '')\n"
    "      + '>' + esc(cos[ci].k) + '（' + cos[ci].n + '）</option>';\n"
    "  }\n"
    "  h += '</select></label>';\n"
    "  h += '<label class=\"flt\"><span>二级类目</span><select class=\"flt-sel\" data-f-sel=\"c2\">'\n"
    "    + '<option value=\"全部\"' + (state.c2 === '全部' ? ' selected' : '') + '>全部细分</option>';\n"
    "  var c2s = c2In();\n"
    "  for (var cj = 0; cj < c2s.length; cj++) {\n"
    "    h += '<option value=\"' + esc(c2s[cj].k) + '\"' + (state.c2 === c2s[cj].k ? ' selected' : '')\n"
    "      + '>' + esc(c2s[cj].k) + '（' + c2s[cj].n + '）</option>';\n"
    "  }\n"
    "  h += '</select></label>';\n"
    "  if (state.country !== '全部') h += '<button type=\"button\" class=\"chip\" data-f=\"country\" data-v=\"全部\">清空国家</button>';\n"
    "  if (state.c2 !== '全部') h += '<button type=\"button\" class=\"chip\" data-f=\"c2\" data-v=\"全部\">清空细分</button>';\n"
    "  h += '</div>';\n"
    "  $('#chips').innerHTML = h;\n};",
    'filter-row2')

# ============================================================ 6. 看板新增两节
BOARD_ADD = r'''  /* ---- 国家/地区市场：这一层回答「去哪个国家做」 ---- */
  var cn = countryStats(list);
  h += '<div class="sec">' + secHd('国家 / 地区市场', '按销售额排；增速讲的是这个国家在不在涨', cn.length + ' 个国家/地区');
  h += '<div class="card"><div class="cmp-hd cmp-hd6"><span>国家/地区</span><span>商品数</span><span>销售额</span><span>平均增速</span><span>平均达人</span><span>主力细分</span></div>';
  for (var cni = 0; cni < cn.length; cni++) {
    var cm = cn[cni];
    h += '<div class="cmp-r"><span><i class="dot" style="background:' + mktColor(cm.market) + '"></i>' + esc(cm.country) + '</span>'
      + '<span>' + cm.n + '</span><span>' + fmtBig(cm.sales) + (cm.sales === null ? '' : '') + '</span>'
      + '<span class="' + pctCls(cm.avgGrowth) + '">' + fmtPct(cm.avgGrowth === null ? null : Math.round(cm.avgGrowth * 10) / 10) + '</span>'
      + '<span>' + (cm.avgKol === null ? '—' : cm.avgKol) + '</span>'
      + '<span class="cmp-sub">' + esc(cm.topC2) + '</span></div>';
  }
  h += '</div></div>';

  /* ---- 二级类目增速榜：钱在哪个功能子类里长 ---- */
  var c2r = c2Stats(list).filter(function (x) { return x.n >= 2; });
  var c2bars = c2r.slice(0, 12).map(function (x) {
    return { k: x.c2, v: Math.max(0, x.avgGrowth || 0), t: fmtPct(x.avgGrowth === null ? null : Math.round(x.avgGrowth)) + ' · ' + x.n + ' 个', color: '#0E7C6B' };
  });
  h += '<div class="sec">' + secHd('二级类目增速榜', '只算样本 ≥ 2 个的细分，条长 = 平均环比增速', 'TOP 12');
  h += '<div class="card pad">'
    + (c2bars.length ? hbarSvg(c2bars, { labelW: 96, valW: 96 })
      : '<div class="empty">这批数据里二级类目样本太散，放宽筛选再看</div>') + '</div></div>';

'''
E_BOARD = ("  v.innerHTML = h;\n};\n\nvar RANK_TYPES = [", BOARD_ADD + "  v.innerHTML = h;\n};\n\nvar RANK_TYPES = [", 'board-add')

# ============================================================ 7. RENDER.lib 重写（Tab：品类树 / 成分库）
LIB_NEW = r'''RENDER.lib = function () {
  var list = dataOf();
  var v = $('#view');
  if (!list.length) {
    v.innerHTML = diagHtml(list);
    return;
  }
  var h = '';
  /* 两个 Tab 共用同一批筛选后的数据：品类树回答「赛道怎么分层」，成分库回答「靠什么在打」 */
  h += '<div class="tabs">'
    + '<button type="button" class="tab' + (state.libTab !== 'ing' ? ' on' : '') + '" data-tab="cat">品类细分树</button>'
    + '<button type="button" class="tab' + (state.libTab === 'ing' ? ' on' : '') + '" data-tab="ing">成分库</button>'
    + '</div>';

  if (state.libTab === 'ing') {
    var ings = ingStats(list);
    var cov = 0;
    for (var ci = 0; ci < list.length; ci++) if (txtOf(list[ci], '核心功效成分')) cov++;
    h += '<div class="sec">' + secHd('成分库', '按「被多少商品写进标题」排序——标题没写的不会被算进来', ings.length + ' 个成分');
    h += '<div class="card pad" style="margin-bottom:12px"><div class="hint">'
      + '本批 <b>' + list.length + '</b> 个商品里，<b>' + cov + '</b> 个标题显性写了成分词，抽到 <b>' + ings.length + '</b> 个不重复成分。'
      + '剩下的没写就不填——成分不做推测。要看全成分表得登录天猫 / 抖音商城 / TikTok 详情页，'
      + '或走国家药监局备案库（本次实测五条详情页通道都不可用，详见数据管理里的说明）。</div></div>';
    if (!ings.length) {
      h += '<div class="card pad"><div class="empty">这批数据里没有商品的标题写了成分词。'
        + '试试放宽筛选，或到「商品档案」里手工补「核心功效成分」。</div></div>';
    } else {
      h += '<div class="ing-grid">';
      for (var ii = 0; ii < ings.length; ii++) {
        var g = ings[ii];
        h += '<div class="card ing">'
          + '<div class="ing-hd"><span class="ing-nm">' + esc(g.ing) + '</span>'
          + '<span class="ing-ct">' + g.n + ' 个品</span></div>'
          + '<div class="ing-kv">'
          + '<span>中位增速</span><b class="' + pctCls(g.medianGrowth) + '">' + fmtPct(g.medianGrowth === null ? null : Math.round(g.medianGrowth)) + '</b>'
          + '<span>最大增速</span><b class="' + pctCls(g.maxGrowth) + '">' + fmtPct(g.maxGrowth === null ? null : Math.round(g.maxGrowth)) + '</b>'
          + '</div>'
          + '<div class="ing-kv">'
          + '<span>覆盖三级类目</span><b>' + g.c3n + ' 个</b>'
          + '<span>覆盖国家</span><b>' + g.ctn + ' 个</b>'
          + '</div>'
          + '<div class="ing-tags"><span class="tag b">' + esc(g.c2.join(' / ') || '—') + '</span></div>'
          + '<div class="ing-ct3">' + esc(g.c3.join(' / ') || '—') + '</div>'
          + '<div class="ing-eg">' + g.eg.map(function (e) {
              return '<button type="button" class="lnk" data-open="' + esc(e.id) + '">' + esc(e.n.slice(0, 26)) + '</button>';
            }).join('') + '</div>'
          + '</div>';
      }
      h += '</div>';
    }
    v.innerHTML = h;
    return;
  }

  /* 品类细分树 */
  var c2s = c2Stats(list);
  h += '<div class="sec">' + secHd('品类细分树', '一级业务大类 → 二级功能子类 → 三级平台类目', '点标题逐层展开');
  h += '<div class="card pad" style="margin-bottom:12px"><div class="hint">'
    + '三级类目来自平台自己的类目树（FastMoss 美妆个护：12 个二级 / 151 个三级），'
    + '每个都带 cid 链，可按它精确复现取数；二级是把三级按功能归的组，业务上更好读。</div></div>';
  h += catTreeHtml(list);
  h += '</div>';

  var top = c2s.slice(0, 12);
  h += '<div class="sec">' + secHd('细分赛道增速', '只看样本 ≥ 2 个的二级类目', 'TOP ' + top.length);
  h += '<div class="card"><div class="cmp-hd"><span>二级类目</span><span>商品数</span><span>三级数</span><span>覆盖国家</span><span>平均增速</span><span>三级类目明细</span></div>';
  for (var ti = 0; ti < top.length; ti++) {
    var x = top[ti];
    h += '<div class="cmp-r"><span>' + esc(x.c2) + '</span>'
      + '<span>' + x.n + '</span><span>' + x.c3n + '</span><span>' + x.ctn + '</span>'
      + '<span class="' + pctCls(x.avgGrowth) + '">' + fmtPct(x.avgGrowth === null ? null : Math.round(x.avgGrowth)) + '</span>'
      + '<span class="cmp-sub">' + esc(x.topC3) + '</span></div>';
  }
  h += '</div></div>';

  var rows = list.slice().sort(function (a, b) { return (numField(b, '销售额') || 0) - (numField(a, '销售额') || 0); });
  h += '<div class="sec">' + secHd('商品档案', '按销售额排序，点击查看完整字段', rows.length + ' 个');
  h += '<div class="cards">';
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    var gv = numField(r, '环比增速'), kol = numField(r, '关联达人数'), rt = numField(r, '评分'), rf = numField(r, '退货率');
    var tags = '';
    var ct = txtOf(r, '国家/地区'); if (ct) tags += '<span class="tag b">' + esc(ct) + '</span>';
    var ov = txtOf(r, '与我方 SKU 重合度');
    if (ov) tags += '<span class="tag' + (ov === '全新' ? ' g' : (ov === '高度重合' ? ' r' : '')) + '">' + esc(ov) + '</span>';
    var ig = txtOf(r, '核心功效成分');
    if (ig) tags += '<span class="tag t">' + esc(firstTag(ig)) + '</span>';
    if (isDemo(r)) tags += '<span class="tag">示例</span>';
    var catline = [txtOf(r, '品牌'), txtOf(r, '二级类目'), txtOf(r, '三级类目')].filter(function (x) { return x; }).join(' · ');
    h += '<button type="button" class="card pc" data-open="' + esc(ridOf(r)) + '">'
      + '<span class="pc-hd"><span class="pc-name">' + esc(txtOf(r, '商品名称') || '未命名') + '</span>'
      + '<span class="pc-price">' + fmtMoney(numField(r, '价格')) + '</span></span>'
      + '<span class="pc-brand">' + esc(catline || '—') + '</span>'
      + '<span class="pc-kv"><span>环比增速</span><b class="' + pctCls(gv) + '">' + fmtPct(gv) + '</b></span>'
      + '<span class="pc-kv"><span>关联达人</span><b>' + (kol === null ? '—' : kol + ' 个') + '</b></span>'
      + '<span class="pc-kv"><span>评分 / 评价</span><b>' + (rt === null ? '—' : rt) + ' / ' + fmtNum(numField(r, '评价数')) + '</b></span>'
      + '<span class="pc-kv"><span>核心成分</span><b>' + esc(firstTag(ig) || '—') + '</b></span>'
      + '<span class="pc-tags">' + tags + '</span>'
      + '</button>';
  }
  h += '</div></div>';
  v.innerHTML = h;
};
'''

LIB_END = "\nfunction firstTag(v) {"


# ============================================================ 8. 洞察新规则
INSIGHTS_NEW = r'''function insightsOf(list) {
  var win = [], fix = [], blank = [], ready = [], risk = [], mkt = [], gcat = [], newp = [], ingr = [];
  for (var i = 0; i < list.length; i++) {
    var r = list[i];
    var g = numField(r, '环比增速'), k = numField(r, '关联达人数');
    var sd = numField(r, '销量');
    var bad = txtOf(r, '差评关键词');
    var overlap = txtOf(r, '与我方 SKU 重合度');
    var filing = txtOf(r, '备案路径'), hard = txtOf(r, '宣称支撑难度');
    var ratio = ratioCost(r);
    if (g !== null && g >= WIN_MIN_GROWTH) win.push(r);
    if (bad !== '') fix.push(r);
    if (overlap === '全新' && g !== null && g >= 25) blank.push(r);
    if (filing === '普通化妆品备案' && hard === '无需评价' && ratio !== null && ratio <= 0.25) ready.push(r);
    if ((g !== null && g < 0) || HIGH_RISK_WORD.test(bad)) risk.push(r);
    /* 新品机会：上市 90 天内且已经在起量，说明这个方向刚被市场验证过 */
    var d = daysSince(r['上市日期']);
    if (d !== null && d <= NEW_MAX_DAYS && g !== null && g >= NEW_MIN_GROWTH && (sd === null || sd >= NEW_MIN_SOLD)) newp.push(r);
  }
  /* 市场机会：国家/地区 × 二级类目 的格子，样本够且平均在涨 */
  var cells = {}, j;
  for (j = 0; j < list.length; j++) {
    var rj = list[j], ct = txtOf(rj, '国家/地区'), c2 = txtOf(rj, '二级类目');
    if (!ct || !c2) continue;
    var gv = numField(rj, '环比增速');
    if (gv === null) continue;
    var key = ct + '\u0001' + c2;
    if (!cells[key]) cells[key] = { country: ct, c2: c2, n: 0, gs: [], rows: [] };
    cells[key].n++; cells[key].gs.push(gv);
    cells[key].rows.push(rj);
  }
  var ck;
  for (ck in cells) {
    if (!Object.prototype.hasOwnProperty.call(cells, ck)) continue;
    var cl = cells[ck], cg = avgArr(cl.gs);
    if (cl.n >= MKT_MIN_SAMPLE && cg !== null && cg >= MKT_MIN_GROWTH) {
      mkt.push({ country: cl.country, c2: cl.c2, n: cl.n, avgGrowth: cg, rows: cl.rows, key: ck });
    }
  }
  mkt.sort(function (a, b) { return b.avgGrowth - a.avgGrowth; });

  /* 增速品类：二级类目聚合，涨 + 还没被达人铺开 = 值得切 */
  var c2s = c2Stats(list);
  for (j = 0; j < c2s.length; j++) {
    var x = c2s[j];
    if (x.n >= GCAT_MIN_SAMPLE && x.avgGrowth !== null && x.avgGrowth >= GCAT_MIN_GROWTH) gcat.push(x);
  }
  gcat.sort(function (a, b) { return b.avgGrowth - a.avgGrowth; });

  /* 成分机会：成分被多个在涨的商品写进标题 = 这个成分在带增长 */
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
'''

INSIGHTS_END = "\n/* ---------- 7b. 引擎体检"

# 规则门槛常量（插在 WIN_MIN_GROWTH 之后）
E_THRESH = (
    "var WIN_MIN_GROWTH = 60;",
    "var WIN_MIN_GROWTH = 60;\n"
    "/* 新增的四条规则的门槛，集中放这里，改口径只动这一处 */\n"
    "var NEW_MAX_DAYS = 90;        /* 新品机会：上市多少天内算新 */\n"
    "var NEW_MIN_GROWTH = 100;     /* 新品机会：环比增速门槛 */\n"
    "var NEW_MIN_SOLD = 1000;      /* 新品机会：销量门槛（没有销量数据时不卡） */\n"
    "var MKT_MIN_SAMPLE = 3;       /* 市场机会：国家×二级类目 至少几条 */\n"
    "var MKT_MIN_GROWTH = 60;      /* 市场机会：格子平均增速门槛 */\n"
    "var GCAT_MIN_SAMPLE = 3;      /* 增速品类：二级类目至少几条 */\n"
    "var GCAT_MIN_GROWTH = 80;     /* 增速品类：平均增速门槛 */\n"
    "var ING_MIN_SAMPLE = 3;       /* 成分机会：成分至少出现在几个商品 */\n"
    "var ING_MIN_GROWTH = 80;      /* 成分机会：这些商品的中位增速门槛 */",
    'thresholds')

# 上市天数辅助（放在 HIGH_RISK_WORD 之前）
E_DAYS = (
    "var HIGH_RISK_WORD = /",
    "/* 距今天数：算「新品」用。日期缺失返回 null，不参与判定。 */\n"
    "function daysSince(v) {\n"
    "  var s = dayStr(v);\n"
    "  if (!s) return null;\n"
    "  var d = new Date(s + 'T00:00:00');\n"
    "  if (isNaN(d.getTime())) return null;\n"
    "  return Math.floor((Date.now() - d.getTime()) / 86400000);\n"
    "}\n"
    "var HIGH_RISK_WORD = /",
    'days-since')

# RULES_NEED 增加 4 条
E_RULES = (
    "  risk: { name: '风险提醒', need: ['环比增速', '差评关键词'] }\n};",
    "  risk: { name: '风险提醒', need: ['环比增速', '差评关键词'] },\n"
    "  mkt: { name: '市场机会', need: ['国家/地区', '二级类目', '环比增速'] },\n"
    "  gcat: { name: '增速品类', need: ['二级类目', '环比增速'] },\n"
    "  newp: { name: '新品机会', need: ['上市日期', '环比增速'] },\n"
    "  ingr: { name: '成分机会', need: ['核心功效成分', '环比增速'] }\n};",
    'rules-need')

# 引擎体检的 order + 文案
E_ORDER = (
    "  var order = ['win', 'fix', 'blank', 'ready', 'risk'];",
    "  var order = ['win', 'fix', 'blank', 'ready', 'risk', 'mkt', 'gcat', 'newp', 'ingr'];",
    'order')
E_HEALTH_TXT = (
    "'<div class=\"hint\" style=\"margin-bottom:10px\">引擎体检：5 条规则里 <b>' + (5 - blocked) + '</b> 条前提齐全、<b>' + blocked + '</b> 条缺字段算不出来。'",
    "'<div class=\"hint\" style=\"margin-bottom:10px\">引擎体检：' + order.length + ' 条规则里 <b>' + (order.length - blocked) + '</b> 条前提齐全、<b>' + blocked + '</b> 条缺字段算不出来。'",
    'health-txt')

# 新洞察卡片：插在最后的空态判断之前
INSIGHT_CARDS = r'''  /* ---- 市场机会：国家 × 二级类目 ---- */
  var mktRows = '';
  if (ins.mkt.length) {
    for (var mi = 0; mi < Math.min(5, ins.mkt.length); mi++) {
      var mx = ins.mkt[mi];
      mktRows += '<button type="button" class="ins-row" data-f="country" data-v="' + esc(mx.country) + '">'
        + '<span class="nm">[' + esc(mx.country) + '] ' + esc(mx.c2) + '　<small>' + mx.n + ' 个样本</small></span>'
        + '<span class="vv"><span class="' + pctCls(mx.avgGrowth) + '">' + fmtPct(Math.round(mx.avgGrowth)) + '</span></span></button>';
    }
  }
  h += card({
    cls: 'p', title: '市场机会', desc: '某个国家的某个细分正在整体起量——去哪个国家做，比做什么更容易做错',
    icon: ICON.compass,
    ev: '命中 <b>' + ins.mkt.length + '</b> 个「国家 × 二级类目」格子'
      + (ins.mkt.length ? '　·　最高 <b>' + esc(ins.mkt[0].country) + ' · ' + esc(ins.mkt[0].c2) + '</b> ' + fmtPct(Math.round(ins.mkt[0].avgGrowth)) : ''),
    rows: mktRows,
    warn: warnFor('mkt') || partWarn('mkt'),
    rule: '规则：同一个「国家/地区 × 二级类目」里至少 ' + MKT_MIN_SAMPLE + ' 个样本，且这些样本的平均环比增速 ≥ ' + MKT_MIN_GROWTH + '%。点一行就能把该国家筛出来。'
  });

  /* ---- 增速品类：赛道维度 ---- */
  var gcatRows = '';
  for (var gi = 0; gi < Math.min(5, ins.gcat.length); gi++) {
    var gx = ins.gcat[gi];
    gcatRows += '<button type="button" class="ins-row" data-f="c2" data-v="' + esc(gx.c2) + '">'
      + '<span class="nm">' + esc(gx.l1) + ' · ' + esc(gx.c2) + '　<small>' + gx.n + ' 个 / ' + gx.c3n + ' 个三级类目</small></span>'
      + '<span class="vv"><span class="' + pctCls(gx.avgGrowth) + '">' + fmtPct(Math.round(gx.avgGrowth)) + '</span> · ' + fmtBig(gx.sales) + '</span></button>';
  }
  h += card({
    cls: '', title: '增速品类', desc: '把商品汇总到赛道层看——单个品可能是运气，整个子类在涨才是趋势',
    icon: ICON.search,
    ev: '命中 <b>' + ins.gcat.length + '</b> 个二级类目　·　门槛：样本 ≥ ' + GCAT_MIN_SAMPLE + ' 且平均增速 ≥ ' + GCAT_MIN_GROWTH + '%',
    rows: gcatRows,
    warn: warnFor('gcat') || partWarn('gcat'),
    rule: '规则：二级类目（功能子类）内至少 ' + GCAT_MIN_SAMPLE + ' 个商品，且平均环比增速 ≥ ' + GCAT_MIN_GROWTH + '%。赛道层面的结论比单品稳，因为不受单个品的活动节奏影响。'
  });

  /* ---- 新品机会 ---- */
  var newRows = '';
  for (var ni = 0; ni < Math.min(5, ins.newp.length); ni++) {
    var nx = ins.newp[ni], nd = daysSince(nx['上市日期']);
    newRows += '<button type="button" class="ins-row" data-open="' + esc(ridOf(nx)) + '">'
      + '<span class="nm">' + esc(txtOf(nx, '国家/地区') || '') + ' ' + esc(txtOf(nx, '商品名称') || '未命名') + '</span>'
      + '<span class="vv"><span class="' + pctCls(numField(nx, '环比增速')) + '">' + fmtPct(numField(nx, '环比增速')) + '</span> · 上架 ' + nd + ' 天</span></button>';
  }
  h += card({
    cls: 'g', title: '新品机会', desc: '上市不到 ' + NEW_MAX_DAYS + ' 天就涨起来的品——刚被市场验证，还没形成壁垒',
    icon: ICON.check,
    ev: '命中 <b>' + ins.newp.length + '</b> 个　·　门槛：上架 ≤ ' + NEW_MAX_DAYS + ' 天、增速 ≥ ' + NEW_MIN_GROWTH + '%'
      + (ins.newp.length ? '　·　最新 <b>' + daysSince(ins.newp[0]['上市日期']) + ' 天</b>' : ''),
    rows: newRows,
    warn: warnFor('newp') || partWarn('newp'),
    rule: '规则：上市 ≤ ' + NEW_MAX_DAYS + ' 天 且 环比增速 ≥ ' + NEW_MIN_GROWTH + '% 且 销量 ≥ ' + NEW_MIN_SOLD + '（有销量数据时）。新品能冲进榜说明需求真实存在，此时竞品少、达人还在试，跟进成本最低。'
  });

  /* ---- 成分机会 ---- */
  var ingRows = '';
  for (var gi2 = 0; gi2 < Math.min(5, ins.ingr.length); gi2++) {
    var ix = ins.ingr[gi2];
    ingRows += '<button type="button" class="ins-row" data-f="kw" data-v="' + esc(ix.ing) + '">'
      + '<span class="nm">' + esc(ix.ing) + '　<small>' + ix.n + ' 个品 / 覆盖 ' + ix.c3n + ' 个三级类目</small></span>'
      + '<span class="vv">中位 <span class="' + pctCls(ix.medianGrowth) + '">' + fmtPct(Math.round(ix.medianGrowth)) + '</span> · 最高 ' + fmtPct(Math.round(ix.maxGrowth)) + '</span></button>';
  }
  h += card({
    cls: 'g', title: '成分机会', desc: '被多个在涨的商品写进标题的成分——成分是配方的锚点，也是宣称的抓手',
    icon: ICON.check,
    ev: '命中 <b>' + ins.ingr.length + '</b> 个成分　·　门槛：出现 ≥ ' + ING_MIN_SAMPLE + ' 个商品且中位增速 ≥ ' + ING_MIN_GROWTH + '%',
    rows: ingRows,
    warn: warnFor('ingr') || partWarn('ingr'),
    rule: '规则：成分出现在 ≥ ' + ING_MIN_SAMPLE + ' 个商品标题里，且这些商品的中位环比增速 ≥ ' + ING_MIN_GROWTH + '%。成分数据是从标题抽取的显性成分词，标题没写的不参与——所以这条规则的下限是「商家愿意把成分写出来」，这也恰好是宣称敏感度高的成分。'
  });

'''

E_INSIGHT_CARDS = (
    "  if (ins.win.length + ins.fix.length + ins.blank.length + ins.ready.length === 0) {",
    INSIGHT_CARDS + "  if (ins.win.length + ins.fix.length + ins.blank.length + ins.ready.length === 0) {",
    'insight-cards')
E_EMPTY_COND = (
    "  if (ins.win.length + ins.fix.length + ins.blank.length + ins.ready.length === 0) {",
    "  if (ins.win.length + ins.fix.length + ins.blank.length + ins.ready.length + ins.mkt.length + ins.gcat.length + ins.newp.length + ins.ingr.length === 0) {",
    'empty-cond')

# ============================================================ 9. 事件：下拉 & 展开 & Tab
E_BIND = (
    "  kw.addEventListener('input', function () {\n"
    "    clearTimeout(timer);\n"
    "    timer = setTimeout(function () { state.kw = kw.value.trim(); refreshAll(); }, 220);\n"
    "  });",
    "  kw.addEventListener('input', function () {\n"
    "    clearTimeout(timer);\n"
    "    timer = setTimeout(function () { state.kw = kw.value.trim(); refreshAll(); }, 220);\n"
    "  });\n"
    "  /* 下拉筛选 + 品类树展开 + 库内 Tab：一律「改 state → refreshAll」，不在渲染里触发渲染 */\n"
    "  $('#chips').addEventListener('change', function (e) {\n"
    "    var el = e.target;\n"
    "    if (!el || !el.getAttribute) return;\n"
    "    var f = el.getAttribute('data-f-sel');\n"
    "    if (!f) return;\n"
    "    state[f] = el.value;\n"
    "    refreshAll();\n"
    "  });\n"
    "  $('#view').addEventListener('click', function (e) {\n"
    "    var t = e.target && e.target.closest ? e.target.closest('[data-exp],[data-tab]') : null;\n"
    "    if (!t) return;\n"
    "    var tb = t.getAttribute('data-tab');\n"
    "    if (tb) { state.libTab = tb; refreshAll(); return; }\n"
    "    var lv = t.getAttribute('data-exp'), k = t.getAttribute('data-expk') || '';\n"
    "    if (lv === 'l1') { if (state.expL1[k]) delete state.expL1[k]; else state.expL1[k] = 1; }\n"
    "    else if (lv === 'l2') { if (state.expL2[k]) delete state.expL2[k]; else state.expL2[k] = 1; }\n"
    "    refreshAll();\n"
    "  });",
    'bind')

# ============================================================ 10. 导入别名
E_ALIAS = (
    "  '细分品类': ['细分品类', '二级类目', '子类目', '三级类目', 'subcategory'],",
    "  '细分品类': ['细分品类', '子类目', 'subcategory'],\n"
    "  '二级类目': ['二级类目', '功能子类', '子类目'],\n"
    "  '三级类目': ['三级类目', '叶类目', '最细类目', 'leafcategory'],\n"
    "  '国家/地区': ['国家/地区', '国家', '地区', '站点', 'region', 'country'],",
    'alias')

# ============================================================ 11. CSS
CSS_ADD = r'''
/* ---- v8：国家市场 / 品类细分树 / 成分库 ---- */
.chip-row2{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:8px}
.flt{display:inline-flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:11px;padding:0 10px;min-height:44px}
.flt>span{font-size:12.5px;color:var(--t2);white-space:nowrap}
.flt-sel{border:0;background:transparent;font-size:16px;color:var(--t1);font-family:inherit;padding:0;max-width:200px;-webkit-appearance:none;appearance:none;cursor:pointer}
.flt-sel:focus{outline:none}
.cmp-hd6{grid-template-columns:1.1fr .6fr .9fr .8fr .7fr 1.3fr}
.cmp-sub{color:var(--t2);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tabs{display:flex;gap:8px;margin-bottom:14px}
.tab{border:1px solid var(--line);background:var(--card);color:var(--t2);font-family:inherit;font-size:14px;padding:0 16px;min-height:44px;border-radius:11px;cursor:pointer}
.tab.on{background:var(--t1);border-color:var(--t1);color:#fff;font-weight:600}
.ct-node{margin-top:6px}
.ct-node.lv2{margin-left:20px}
.ct-hd{display:flex;align-items:center;gap:10px;width:100%;min-height:44px;padding:0 12px;border:1px solid var(--line);background:var(--card);border-radius:11px;font-family:inherit;font-size:14.5px;color:var(--t1);cursor:pointer;text-align:left}
.ct-hd.on{border-color:var(--accent);background:#F2F7FF}
.ct-arw{width:16px;text-align:center;color:var(--t2);font-weight:600;flex:0 0 16px}
.ct-nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ct-n{color:var(--t2);font-size:12.5px;white-space:nowrap}
.ct-g{font-weight:600;min-width:62px;text-align:right;font-variant-numeric:tabular-nums}
.ct-row{display:flex;align-items:center;gap:10px;min-height:38px;padding:0 12px;margin:4px 0 0 20px;border-left:2px solid var(--line);font-size:13.5px}
.ct-row .ct-nm{color:var(--t2)}
.ing-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(258px,1fr));gap:12px}
.ing{padding:13px 14px}
.ing-hd{display:flex;align-items:baseline;justify-content:space-between;gap:8px;margin-bottom:9px}
.ing-nm{font-size:16px;font-weight:600}
.ing-ct{font-size:12px;color:var(--t2);white-space:nowrap}
.ing-kv{display:flex;align-items:baseline;justify-content:space-between;font-size:12.5px;color:var(--t2);padding:3px 0}
.ing-kv b{color:var(--t1);font-variant-numeric:tabular-nums}
.ing-tags{margin-top:7px}
.ing-ct3{font-size:12px;color:var(--t2);margin-top:5px;line-height:1.5}
.ing-eg{margin-top:9px;display:flex;flex-direction:column;gap:3px}
.lnk{border:0;background:transparent;padding:0;font-family:inherit;font-size:12px;color:var(--accent);text-align:left;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:768px){
  .cmp-hd6{display:none}
  .flt{width:100%}
  .flt-sel{max-width:none;flex:1}
  .ing-grid{grid-template-columns:1fr}
  .ct-node.lv2{margin-left:10px}
  .ct-row{margin-left:10px}
}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', default=os.path.join(ROOT, '全球选品平台.html'))
    ap.add_argument('--out', dest='dst', default=None)
    args = ap.parse_args()
    dst = args.dst or args.src

    html = io.open(args.src, encoding='utf-8').read()
    print('输入 %s（%d 字符）' % (args.src, len(html)))
    fails = []

    # 简单替换
    for old, new, tag in [E_STATE, E_DATAOF, E_KW, E_FILTER, E_BOARD, E_INSIGHT_CARDS,
                          E_EMPTY_COND, E_BIND, E_ALIAS, E_THRESH, E_DAYS, E_RULES,
                          E_ORDER, E_HEALTH_TXT, E_HELPERS] + F_FIELDS:
        n = html.count(old)
        if n != 1:
            fails.append('%-14s 命中 %d 次' % (tag, n))
            continue
        html = html.replace(old, new)
        print('  [ok]   %-14s' % tag)

    # 区间替换
    for start, end, new, tag in [
        ('function insightsOf(list) {', INSIGHTS_END, INSIGHTS_NEW, 'insightsOf'),
        ('RENDER.lib = function () {', LIB_END, LIB_NEW, 'render-lib'),
    ]:
        r = replace_between(html, start, end, new, tag)
        if r is None:
            fails.append('%-14s 找不到区间' % tag)
            continue
        html = r[0]
        print('  [ok]   %-14s' % tag)

    # CSS
    if html.count('</style>') == 1:
        html = html.replace('</style>', CSS_ADD + '</style>')
        print('  [ok]   %-14s' % 'css')
    else:
        fails.append('css 的 </style> 不唯一')

    if fails:
        print()
        for f in fails:
            print('  [FAIL] ' + f)
        sys.exit(1)

    io.open(dst, 'w', encoding='utf-8').write(html)
    print('写出 %s（%d 字符，+%d）' % (dst, len(html), len(html) - len(io.open(args.src, encoding='utf-8').read())))


if __name__ == '__main__':
    main()
