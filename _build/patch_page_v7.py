#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地「全球选品平台.html」v6 -> v7：
   新增第 5 个视图「口碑诊断」，数据源是第二张云表「自有店铺口碑库」（抖音罗盘·用户原声）。

设计原则（沿用页面既有架构）：
   - 只加 VIEWS 一项 + 一个 RENDER.review + 一处 dispatch，不动通用引擎；
   - 数据出口仍走 dbQueryAll，不新增直连 SDK 的写法；
   - 新增绑定用 data-bind-review 标注，bindDb 里统一 setAttribute（DSDK011/012 要求）。

用法: python3 patch_page_v7.py [--in <html>] [--out <html>] [--db-id <id>]
"""
import argparse
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
REVIEW_DB = 'ZOiFonS5w7psZlgM5kJjiD'

EDITS = []


def edit(old, new, tag):
    EDITS.append((old, new, tag))


# ---------------------------------------------------------------- 1. 第二张表
edit(
    "var DATABASE_ID = 'Hu5q2PAyW17BmdP5JPQ9os';\n"
    "var DB = { product: { databaseId: DATABASE_ID } };",
    "var DATABASE_ID = 'Hu5q2PAyW17BmdP5JPQ9os';\n"
    "/* 第二张表：自有店铺口碑库（抖音罗盘「体验 · 用户原声」）——口碑诊断视图的数据源 */\n"
    "var DB = { product: { databaseId: DATABASE_ID }, review: { databaseId: '%s' } };" % REVIEW_DB,
    'DB')

# ---------------------------------------------------------------- 2. 视图定义
edit(
    "  { key: 'insight', name: '机会洞察', desc: '从数据里自动提炼值得动手的方向',\n"
    "    icon: '<path d=\"M12 3a6 6 0 0 0-3.6 10.8V17h7.2v-3.2A6 6 0 0 0 12 3z\"/><path d=\"M10 20h4\"/>' }\n"
    "];",
    "  { key: 'insight', name: '机会洞察', desc: '从数据里自动提炼值得动手的方向',\n"
    "    icon: '<path d=\"M12 3a6 6 0 0 0-3.6 10.8V17h7.2v-3.2A6 6 0 0 0 12 3z\"/><path d=\"M10 20h4\"/>' },\n"
    "  { key: 'review', name: '口碑诊断', desc: '自有店铺的好评/差评原声，直接指向可改良点',\n"
    "    icon: '<path d=\"M21 12a8 8 0 0 1-11.5 7.2L4 21l1.8-5.5A8 8 0 1 1 21 12z\"/><path d=\"M9 11h6M9 14.5h3.5\"/>' }\n"
    "];",
    'VIEWS')

# ---------------------------------------------------------------- 3. state
edit(
    "  view: 'board', list: [], schema: null, ready: false,",
    "  view: 'board', list: [], review: [], schema: null, ready: false,",
    'state')

# ---------------------------------------------------------------- 4. 数据加载
edit(
    "  if (!ONLINE) {\n"
    "    state.list = lsRead().product || [];\n"
    "    state.ready = true;\n"
    "    return Promise.resolve();\n"
    "  }",
    "  if (!ONLINE) {\n"
    "    state.list = lsRead().product || [];\n"
    "    state.review = lsRead().review || [];\n"
    "    state.ready = true;\n"
    "    return Promise.resolve();\n"
    "  }",
    'load-local')
edit(
    "    return dbQueryAll(DB.product.databaseId).then(function (rows) {\n"
    "      state.list = (rows || []).filter(function (r) { return r && ridOf(r); });\n"
    "      state.ready = true;\n"
    "    });",
    "    return dbQueryAll(DB.product.databaseId).then(function (rows) {\n"
    "      state.list = (rows || []).filter(function (r) { return r && ridOf(r); });\n"
    "      state.ready = true;\n"
    "    }).then(function () {\n"
    "      /* 口碑库是第二张表：拉失败不影响主表，只把口碑区置空 */\n"
    "      return dbQueryAll(DB.review.databaseId).then(function (rv) {\n"
    "        state.review = (rv || []).filter(function (r) { return r && ridOf(r); });\n"
    "      }).catch(function () { state.review = []; });\n"
    "    });",
    'load-online')

# ---------------------------------------------------------------- 5. 导航短名
edit(
    "  var SHORT = { board: '看板', rank: '榜单', lib: '品类库', insight: '洞察' };",
    "  var SHORT = { board: '看板', rank: '榜单', lib: '品类库', insight: '洞察', review: '口碑' };",
    'nav-short')

# ---------------------------------------------------------------- 6. 标题
edit(
    "RENDER.titles = function () {\n"
    "  var v = viewDef(state.view);\n"
    "  var n = dataOf().length;",
    "RENDER.titles = function () {\n"
    "  var v = viewDef(state.view);\n"
    "  if (state.view === 'review') {\n"
    "    var nr = (state.review || []).length;\n"
    "    $('#viewTitle').textContent = v.name;\n"
    "    $('#viewDesc').textContent = v.desc + '　·　自有店铺在售 ' + nr + ' 个商品'\n"
    "      + (state.ready ? '' : ' · 加载中…');\n"
    "    return;\n"
    "  }\n"
    "  var n = dataOf().length;",
    'titles')

# ---------------------------------------------------------------- 7. 筛选条
edit(
    "RENDER.filter = function () {\n  var h = '';",
    "RENDER.filter = function () {\n"
    "  if (state.view === 'review') {\n"
    "    $('#chips').innerHTML = '<span class=\"hint\" style=\"margin:2px 0\">"
    "口碑诊断读的是第二张表「自有店铺口碑库」，与上面的商品筛选无关；切回其它视图即恢复筛选。</span>';\n"
    "    return;\n"
    "  }\n"
    "  var h = '';",
    'filter')

# ---------------------------------------------------------------- 8. 渲染函数
REVIEW_JS = r"""
/* ---------- 口碑诊断：自有店铺（抖音罗盘 · 体验 · 用户原声） ----------
   与选品库分开的原因：评价只有「自己店铺」的后台才看得到，
   第三方商品的评价需要登录天猫/小红书/抖音商城，浏览器里拿不到。
   所以这一区回答的问题不是「选什么」，而是「已在卖的这些，该改什么」。 */
RENDER.review = function () {
  var v = $('#view');
  var rows = state.review || [];
  if (!rows.length) {
    v.innerHTML = '<div class="card pad"><div class="empty">还没有口碑数据（或第二张表未连上）。'
      + '数据来自抖音电商罗盘「体验 · 用户原声」，取数脚本 <b>_build/wb_douyin_usersound.py</b>，'
      + '落在「自有店铺口碑库」表里。</div></div>';
    return;
  }
  var i, r;
  var evalSum = 0, goodSum = 0, badOrdSum = 0, withReason = 0;
  for (i = 0; i < rows.length; i++) {
    evalSum += numField(rows[i], '评价数') || 0;
    goodSum += numField(rows[i], '好评数') || 0;
    badOrdSum += numField(rows[i], '差评订单数') || 0;
    if (txtOf(rows[i], '差评原因')) withReason++;
  }
  var avgGood = evalSum ? Math.round(goodSum / evalSum * 1000) / 10 : null;

  var h = '';
  h += '<div class="grid g-3">'
    + kpiCard('在售商品', String(rows.length), '个')
    + kpiCard('累计评价', fmtNum(evalSum), '条')
    + kpiCard('整体好评率', avgGood === null ? '—' : avgGood + '%', '')
    + '</div>';
  h += '<div class="grid g-3" style="margin-top:12px">'
    + kpiCard('差评订单', fmtNum(badOrdSum), '单')
    + kpiCard('本期有差评原因的商品', String(withReason), '个')
    + kpiCard('采集周期', txtOf(rows[0], '采集周期') || '—', '')
    + '</div>';
  h += '<div class="hint" style="margin:10px 0 0">口径：差评率 = 商品差评订单数 / 物流签收订单数；'
    + '好评率 = 好评数 / 评价数。数据来自「' + esc(txtOf(rows[0], '数据来源') || '抖音罗盘')
    + ' / ' + esc(txtOf(rows[0], '评价来源') || '抖音评价') + '」。</div>';

  /* --- 该改的：有差评原因的商品 --- */
  var bad = rows.filter(function (x) { return txtOf(x, '差评原因') !== ''; })
    .sort(function (a, b) { return (numField(b, '差评订单数') || 0) - (numField(a, '差评订单数') || 0); });
  h += '<div class="sec">' + secHd('该改的', '差评原因就是改良清单，点开看买家原话', bad.length + ' 个') + '';
  if (!bad.length) {
    h += '<div class="card pad"><div class="empty">本期没有产生差评标签的商品。</div></div>';
  } else {
    for (i = 0; i < bad.length; i++) {
      r = bad[i];
      var tags = '';
      var labels = splitTags(txtOf(r, '差评原因'));
      for (var t = 0; t < Math.min(labels.length, 8); t++) {
        var lb = labels[t];
        var hi = /过敏|不适|人身伤害|虚假|不符|质量|不安全/.test(lb);
        tags += '<span class="tag' + (hi ? ' r' : '') + '">' + esc(lb) + '</span>';
      }
      var voices = String(txtOf(r, '差评原声') || '').split(' | ').filter(function (s) { return s; }).slice(0, 3);
      var vh = '';
      for (var q = 0; q < voices.length; q++) {
        vh += '<div class="ins-row" style="display:block"><span class="vv">「' + esc(voices[q]) + '」</span></div>';
      }
      h += '<div class="card pad" style="margin-bottom:10px">'
        + '<div style="display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap">'
        + '<b style="flex:1;min-width:200px;font-size:14px">' + esc(txtOf(r, '商品名称') || '未命名') + '</b>'
        + '<span class="tag">差评订单 ' + (numField(r, '差评订单数') || 0) + '</span>'
        + '<span class="tag">差评率 ' + (numField(r, '差评率') === null ? '—' : numField(r, '差评率') + '%') + '</span>'
        + '<span class="tag b">好评率 ' + (numField(r, '好评率') === null ? '—' : numField(r, '好评率') + '%') + '</span>'
        + '</div>'
        + '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' + tags + '</div>'
        + (vh ? '<div style="margin-top:8px">' + vh + '</div>' : '')
        + '</div>';
    }
  }
  h += '</div>';

  /* --- 全部商品口碑 --- */
  var all = rows.slice().sort(function (a, b) { return (numField(b, '评价数') || 0) - (numField(a, '评价数') || 0); });
  h += '<div class="sec">' + secHd('本店全部商品口碑', '按评价数排序', all.length + ' 个');
  h += '<div class="cards">';
  for (i = 0; i < all.length; i++) {
    r = all[i];
    var gk = txtOf(r, '好评关键词'), bk = txtOf(r, '差评关键词');
    h += '<div class="card pc">'
      + '<span class="pc-hd"><span class="pc-name">' + esc(txtOf(r, '商品名称') || '未命名') + '</span></span>'
      + '<span class="pc-brand">' + esc(txtOf(r, '店铺类目') || '—') + '</span>'
      + '<span class="pc-kv"><span>评价数</span><b>' + fmtNum(numField(r, '评价数')) + '</b></span>'
      + '<span class="pc-kv"><span>好评率</span><b>' + (numField(r, '好评率') === null ? '—' : numField(r, '好评率') + '%') + '</b></span>'
      + '<span class="pc-kv"><span>差评订单</span><b class="' + ((numField(r, '差评订单数') || 0) > 0 ? 'up' : '') + '">'
      + (numField(r, '差评订单数') || 0) + '</b></span>'
      + '<span class="pc-tags">'
      + (gk ? '<span class="tag g">' + esc(gk.split(' / ').slice(0, 2).join('·')) + '</span>' : '')
      + (bk ? '<span class="tag r">' + esc(bk.split(' / ').slice(0, 2).join('·')) + '</span>' : '')
      + '</span></div>';
  }
  h += '</div></div>';

  h += '<div class="card pad" style="margin-top:12px"><div class="hint">'
    + '<b>这一区为什么只覆盖自有店铺：</b>评价原文只有店铺后台（抖音电商罗盘「用户原声」）看得到；'
    + '第三方商品的评价要在天猫/小红书/抖音商城里登录后才可见，浏览器里拿不到。'
    + '想补第三方口碑，需要先在已登录的浏览器里打通对应后台，再照 <b>_build/wb_douyin_usersound.py</b> 的写法接一条取数脚本。'
    + '</div></div>';
  v.innerHTML = h;
};
function kpiCard(lb, vl, unit) {
  return '<div class="card kpi"><div class="lb">' + esc(lb) + '</div><div class="vl">'
    + esc(vl) + (unit ? '<small>' + esc(unit) + '</small>' : '') + '</div></div>';
}
"""
edit(
    "/* database 绑定标注：成对写入 data-sp-bindable / data-sp-database-id */",
    REVIEW_JS.strip() + "\n\n/* database 绑定标注：成对写入 data-sp-bindable / data-sp-database-id */",
    'render-review')

# ---------------------------------------------------------------- 9. dispatch
edit(
    "  if (v === 'board') RENDER.board();\n"
    "  else if (v === 'rank') RENDER.rank();\n"
    "  else if (v === 'lib') RENDER.lib();\n"
    "  else RENDER.insight();",
    "  if (v === 'board') RENDER.board();\n"
    "  else if (v === 'rank') RENDER.rank();\n"
    "  else if (v === 'lib') RENDER.lib();\n"
    "  else if (v === 'review') RENDER.review();\n"
    "  else RENDER.insight();",
    'dispatch')

# ---------------------------------------------------------------- 10. bindDb
edit(
    "  var id = DB.product.databaseId;\n"
    "  $$('[data-bind]', root || document).forEach(function (el) {\n"
    "    el.setAttribute('data-sp-bindable', 'database');\n"
    "    el.setAttribute('data-sp-database-id', id);\n"
    "  });",
    "  $$('[data-bind]', root || document).forEach(function (el) {\n"
    "    el.setAttribute('data-sp-bindable', 'database');\n"
    "    el.setAttribute('data-sp-database-id', DB.product.databaseId);\n"
    "  });\n"
    "  $$('[data-bind-review]', root || document).forEach(function (el) {\n"
    "    el.setAttribute('data-sp-bindable', 'database');\n"
    "    el.setAttribute('data-sp-database-id', DB.review.databaseId);\n"
    "  });",
    'bindDb')

# ---------------------------------------------------------------- 11. 静态绑定锚点
# 本地 v6 与线上 v6 的属性顺序/注释不同（线上带 data-page-node-id 与 pnid 注释），
# 所以这里给候选锚点，按序取第一个「唯一命中」的。
ANCHOR_NEW = ('<span id="syncText">初始化…</span></div>',
              '<span data-bind-review="1" hidden></span></div>')
ANCHOR_FALLBACK = [('初始化…</span></div>', '<span data-bind-review="1" hidden></span></div>')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', default=os.path.join(ROOT, '全球选品平台.html'))
    ap.add_argument('--out', dest='dst', default=None)
    ap.add_argument('--db-id', dest='dbid', default=REVIEW_DB)
    args = ap.parse_args()
    dst = args.dst or args.src

    html = open(args.src, encoding='utf-8').read()
    orig_len = len(html)
    print('输入 %s（%d 字符）' % (args.src, len(html)))
    for old, new, tag in EDITS:
        if args.dbid != REVIEW_DB:
            new = new.replace(REVIEW_DB, args.dbid)
        n = html.count(old)
        if n != 1:
            print('  [FAIL] %-12s 命中 %d 次（应为 1）' % (tag, n))
            sys.exit(1)
        html = html.replace(old, new)
        print('  [ok]   %-12s' % tag)

    # 绑定锚点：候选按序试，取唯一命中的那个（本地/线上标记略有差异）
    done = False
    for old, new in [ANCHOR_NEW] + ANCHOR_FALLBACK:
        if html.count(old) == 1:
            html = html.replace(old, new)
            print('  [ok]   %-12s（锚点：%s…）' % ('bind-anchor', old[:28]))
            done = True
            break
    if not done:
        print('  [FAIL] bind-anchor 所有候选都未唯一命中')
        sys.exit(1)

    open(dst, 'w', encoding='utf-8').write(html)
    print('写出 %s（%d -> %d 字符，+%d）' % (dst, orig_len, len(html), len(html) - orig_len))


if __name__ == '__main__':
    main()
