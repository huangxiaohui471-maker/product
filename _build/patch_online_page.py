#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本地页面的语义改动，精确打到从线上拉下来的 index.html 上（保留平台 pnid 锚点）。

只做替换，不重排任何其它内容；每处替换都断言命中且仅命中一次。
"""
import sys

P = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/.page_tmp/index.html'
src = open(P, encoding='utf-8').read()

PATCHES = [
    # P1 线上版入口常量
    ("var LS_DRAFT = 'wb_global_select_draft';\n\nvar state = {",
     "var LS_DRAFT = 'wb_global_select_draft';\n\n"
     "/* 线上版入口：本机打开的文件天然拿不到资料库通道，用它一键切到线上那一份 */\n"
     "var ONLINE_URL = 'https://www.workbuddy.cn/space/d/lMO9EIAM8o5cIwqudwUDr1';\n"
     "var IS_LOCAL = /^(file:|https?:\\/\\/(127\\.0\\.0\\.1|localhost|\\[::1\\]))/i.test(location.href);\n\n"
     "var state = {"),

    # P2 state 增加 realOnly
    ("busy: false, demoOnly: false\n};",
     "busy: false, demoOnly: false, realOnly: false\n};"),

    # P3 envLabel / setEnvUi
    ("  d.className = 'sync-dot' + (kind === 'off' ? ' off' : (kind === 'busy' ? ' busy' : ''));\n"
     "  t.textContent = text;\n}\nfunction loadOne() {",
     "  d.className = 'sync-dot' + (kind === 'off' ? ' off' : (kind === 'busy' ? ' busy' : ''));\n"
     "  t.textContent = text;\n}\n"
     "/* 运行环境提示：本机打开 ≠ 功能坏了，只是没接上云端那一份 */\n"
     "function envLabel() {\n"
     "  if (ONLINE) return '云端已同步';\n"
     "  return IS_LOCAL ? '本地打开 · 未连线上' : '线上通道未就绪';\n"
     "}\n"
     "function setEnvUi() {\n"
     "  setSync(ONLINE ? 'ok' : 'off', envLabel());\n"
     "  var b = $('#btnOnline');\n"
     "  if (b) b.style.display = ONLINE ? 'none' : '';\n"
     "}\n"
     "function loadOne() {"),

    # P4 loadAll 走统一环境提示
    ("return loadOne().then(function () { setSync(ONLINE ? 'ok' : 'off', ONLINE ? '云端已同步' : '离线模式'); });",
     "return loadOne().then(function () { setEnvUi(); });"),

    # P5 dataOf 增加 realOnly 过滤
    ("    if (state.demoOnly && !isDemo(r)) continue;\n    if (state.kw) {",
     "    if (state.demoOnly && !isDemo(r)) continue;\n"
     "    if (state.realOnly && isDemo(r)) continue;\n"
     "    if (state.kw) {"),

    # P6 覆盖度估算同口径
    ("function isDemoFilteredOut(r) { return state.demoOnly && !isDemo(r); }",
     "/* 示例/真实开关造成的过滤（覆盖度估算与列表过滤共用同一口径） */\n"
     "function isDemoFilteredOut(r) { return (state.demoOnly && !isDemo(r)) || (state.realOnly && isDemo(r)); }"),

    # P7 只看真实 chip
    ("  h += '<span class=\"chip-sep\"></span>';\n"
     "  h += '<button type=\"button\" class=\"chip' + (state.demoOnly ? ' on' : '') + '\" data-f=\"demoOnly\" data-v=\"' + (state.demoOnly ? '0' : '1') + '\">只看示例</button>';",
     "  h += '<span class=\"chip-sep\"></span>';\n"
     "  h += '<button type=\"button\" class=\"chip' + (state.realOnly ? ' on' : '') + '\" data-f=\"realOnly\" data-v=\"' + (state.realOnly ? '0' : '1') + '\">只看真实</button>';\n"
     "  h += '<button type=\"button\" class=\"chip' + (state.demoOnly ? ' on' : '') + '\" data-f=\"demoOnly\" data-v=\"' + (state.demoOnly ? '0' : '1') + '\">只看示例</button>';"),

    # P8 数据管理弹层文案
    ("    + (ONLINE ? '数据实时存在资料库云端，任意设备打开都是同一份。' : '当前为离线模式，数据只存在这台设备上。') + '</div>'",
     "    + (ONLINE ? '数据实时存在资料库云端，任意设备打开都是同一份。' : (IS_LOCAL ? "
     "'你现在打开的是本机那份文件，云端通道没接上，改动只留在这台设备。要和其他设备共用同一份数据，用下面的「打开线上版」。' : "
     "'线上通道暂未就绪，先存在这台设备上。')) + '</div>'"),

    # P9 数据管理弹层加「打开线上版」
    ("  var foot = '<button type=\"button\" class=\"btn sec\" id=\"btnClearDemo\"' + (demoN ? '' : ' disabled style=\"opacity:.45\"') + '>清空示例数据</button>'",
     "  var foot = (ONLINE ? '' : '<button type=\"button\" class=\"btn\" id=\"btnOnline2\">打开线上版 · 云端同步</button>')\n"
     "    + '<button type=\"button\" class=\"btn sec\" id=\"btnClearDemo\"' + (demoN ? '' : ' disabled style=\"opacity:.45\"') + '>清空示例数据</button>'"),

    # P10 弹层按钮监听
    ("  $('#btnClearDemo').addEventListener('click', clearDemo);\n}",
     "  $('#btnClearDemo').addEventListener('click', clearDemo);\n"
     "  var bO2 = $('#btnOnline2');\n"
     "  if (bO2) bO2.addEventListener('click', function () { window.open(ONLINE_URL, '_blank'); });\n}"),

    # P11 侧栏「打开线上版」按钮
    ("        数据源地图 · 各国数据从哪来\n      </button>\n    </div>\n  </aside>",
     "        数据源地图 · 各国数据从哪来\n      </button>\n"
     "      <button type=\"button\" id=\"btnOnline\" style=\"display:none;width:100%;margin-top:7px;min-height:38px;border:0;border-radius:9px;background:var(--blue);color:#fff;font-size:12.5px;font-weight:600\">\n"
     "        打开线上版 · 云端同步\n      </button>\n    </div>\n  </aside>"),

    # P12 侧栏按钮监听
    ("  $('#btnMore').addEventListener('click', openMore);",
     "  $('#btnMore').addEventListener('click', openMore);\n"
     "  var bo = $('#btnOnline');\n"
     "  if (bo) bo.addEventListener('click', function () { window.open(ONLINE_URL, '_blank'); });"),

    # P13 只看示例/只看真实互斥
    ("      if (f === 'demoOnly') state.demoOnly = (v === '1');\n      else state[f] = v;",
     "      if (f === 'demoOnly') { state.demoOnly = (v === '1'); if (state.demoOnly) state.realOnly = false; }\n"
     "      else if (f === 'realOnly') { state.realOnly = (v === '1'); if (state.realOnly) state.demoOnly = false; }\n"
     "      else state[f] = v;"),
]

for i, (old, new) in enumerate(PATCHES, 1):
    n = src.count(old)
    if n != 1:
        print('PATCH %d 命中 %d 次，中止' % (i, n))
        sys.exit(1)
    src = src.replace(old, new)
    print('PATCH %d ok' % i)

open(P, 'w', encoding='utf-8').write(src)
print('已写回', P)
