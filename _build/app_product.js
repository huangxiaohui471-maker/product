
/* =============================================================
   全球新品选品台 · 单文件工作台
   数据：WorkBuddy 资料库「全球新品库」在线数据表
   降级：运行环境没有数据表能力时，自动切换本机离线存储
   ============================================================= */
/* ---------- 1. 数据表 ---------- */
var DB = { product: { databaseId: 'Hu5q2PAyW17BmdP5JPQ9os' } };

/* ---------- 2. 视图定义 ---------- */
var VIEWS = [
  { key: 'product', name: '全球新品库', short: '新品库', type: 'list', desc: '全球新品档案，一条一个商品',
    icon: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12v9M12 12 4 7.5"/>' },
  { key: 'score', name: '选品评分卡', short: '评分卡', type: 'score', desc: '七个维度加权打分，够分才进打样',
    icon: '<path d="M4 20h16"/><path d="M7 20V10M12 20V4M17 20v-6"/>' },
  { key: 'board', name: '机会看板', short: '看板', type: 'board', desc: '价格带缺口与增长动能分布',
    icon: '<circle cx="7" cy="16" r="2"/><circle cx="12.5" cy="8.5" r="2.6"/><circle cx="17.5" cy="14" r="1.8"/><path d="M3 20h18"/>' }
];
function viewDef(k) { for (var i = 0; i < VIEWS.length; i++) { if (VIEWS[i].key === k) return VIEWS[i]; } return VIEWS[0]; }

/* ---------- 3. 字段定义（按平台可导出字段对齐） ---------- */
var GROUPS = ['商品主数据', '平台数据', '成分与功效', '口碑', '可行性', '决策'];
var FIELDS = [
  { n: '商品名称', t: 'text', req: true, g: '商品主数据', ph: '品牌+系列+品名，用官方名，不用达人叫法' },
  { n: '品牌', t: 'text', g: '商品主数据', ph: '如 Dr.Jart+' },
  { n: '商品ID', t: 'text', g: '商品主数据', ph: '平台商品ID，批量导入时自动带上' },
  { n: '品类', t: 'select', g: '商品主数据', opts: ['护肤', '彩妆', '个护', '身体', '香氛', '工具'] },
  { n: '细分品类', t: 'text', g: '商品主数据', ph: '如 身体冷霜' },
  { n: '价格', t: 'number', g: '商品主数据', ph: '到手价；海外品按统一汇率折算成人民币' },
  { n: '上市日期', t: 'date', g: '商品主数据' },

  { n: '数据来源', t: 'select', g: '平台数据', opts: ['抖音罗盘', '蝉妈妈', 'FastMoss', '其他'], def: '蝉妈妈' },
  { n: '所属市场', t: 'select', g: '平台数据', opts: ['中国', '韩国', '日本', '欧美', '东南亚'], def: '中国' },
  { n: '榜单排名', t: 'text', g: '平台数据', ph: '如 抖音身体护理第 12' },
  { n: '销量', t: 'number', g: '平台数据', ph: '件' },
  { n: '销售额', t: 'number', g: '平台数据', ph: '元' },
  { n: '环比增速', t: 'number', g: '平台数据', ph: '填数字：+42% 就填 42' },
  { n: '关联达人数', t: 'number', g: '平台数据', ph: '带货这个品的达人数' },
  { n: '退货率', t: 'number', g: '平台数据', ph: '填数字：8% 就填 8' },

  { n: '核心功效成分', t: 'text', g: '成分与功效', ph: '最多 3 个，顿号分隔' },
  { n: '剂型', t: 'select', g: '成分与功效', opts: ['水', '乳', '霜', '油', '膏', '喷雾', '粉'] },
  { n: '概念标签', t: 'text', g: '成分与功效', ph: '如 以油养肤、早C晚A' },
  { n: '质地描述', t: 'text', g: '成分与功效', ph: '保留原话，如「冷霜质地、夏天也敢用」' },
  { n: '功效宣称', t: 'text', g: '成分与功效', ph: '官方宣称，最多 3 条' },
  { n: '技术壁垒', t: 'select', g: '成分与功效', opts: ['无壁垒', '配方工艺', '独家原料', '专利技术'] },

  { n: '评分', t: 'number', g: '口碑', ph: '5 分制' },
  { n: '评价数', t: 'number', g: '口碑' },
  { n: '差评关键词', t: 'text', g: '口碑', ph: '从差评里提炼，这是开发机会的直接线索' },

  { n: '备案路径', t: 'select', g: '可行性', opts: ['普通化妆品备案', '特殊化妆品注册', '进口备案', '暂无'] },
  { n: '宣称支撑难度', t: 'select', g: '可行性', opts: ['无需评价', '需文献资料', '需人体功效试验'] },
  { n: '预估成本', t: 'number', g: '可行性', ph: '单件出厂成本' },
  { n: '与我方价格带匹配', t: 'select', g: '可行性', opts: ['匹配', '偏高', '偏低'] },
  { n: '与我方客群匹配', t: 'select', g: '可行性', opts: ['匹配', '需教育', '不符'] },

  { n: '与我方 SKU 重合度', t: 'select', g: '决策', opts: ['全新', '部分重合', '高度重合'] },
  { n: '决策状态', t: 'select', g: '决策', opts: ['待评', '候选池', '打样评估', '已否决'], def: '待评' },
  { n: '选品笔记', t: 'textarea', g: '决策', ph: '为什么值得做、风险在哪、下一步找谁' }
];
var MODULE = {
  key: 'product', primary: '商品名称', statusField: '决策状态', dateField: '上市日期',
  filterKeys: ['决策状态', '数据来源', '所属市场', '品类', '与我方价格带匹配'],
  fields: FIELDS
};
function fieldDef(name) { for (var i = 0; i < FIELDS.length; i++) { if (FIELDS[i].n === name) return FIELDS[i]; } return null; }

/* ---------- 4. 工具 ---------- */
function $(s, r) { return (r || document).querySelector(s); }
function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
function esc(v) {
  return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}
function pad(n) { return (n < 10 ? '0' : '') + n; }
function todayStr() { var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
function dayStr(v) {
  if (v == null || v === '') return '';
  if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v)) return v.slice(0, 10);
  var d = new Date(v);
  if (isNaN(d.getTime())) return String(v);
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
}
function msOf(v) { var s = dayStr(v); if (!s) return NaN; var t = new Date(s + 'T00:00:00').getTime(); return isNaN(t) ? NaN : t; }
function daysFromToday(v) {
  var a = msOf(v), b = msOf(todayStr());
  if (isNaN(a) || isNaN(b)) return null;
  return Math.round((a - b) / 86400000);
}
function cnDate(v) { var s = dayStr(v); if (!s) return ''; var p = s.split('-'); return p.length !== 3 ? s : Number(p[1]) + '月' + Number(p[2]) + '日'; }
function numOf(v) { if (v == null || v === '') return null; var n = Number(v); return isNaN(n) ? null : n; }
function fmtNum(v) { return v == null || v === '' || isNaN(Number(v)) ? '—' : Number(v).toLocaleString('zh-CN'); }
function fmtMoney(v) { return v == null || v === '' || isNaN(Number(v)) ? '—' : '¥' + Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 }); }
function uid() { return 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }
function firstLine(s, n) {
  var t = String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  return t.length > n ? t.slice(0, n) + '…' : t;
}
function toast(msg) {
  var el = $('#toast'); el.textContent = msg; el.classList.add('on');
  clearTimeout(el._t); el._t = setTimeout(function () { el.classList.remove('on'); }, 2400);
}
function isDemo(r) { return String(r[MODULE.primary] || '').indexOf('【示例】') === 0; }

/* ---------- 5. 运行环境：在线数据表 or 本机离线 ---------- */
var db = (window.__SMART_PAGE__ && window.__SMART_PAGE__.database) ? window.__SMART_PAGE__.database : null;
var ONLINE = !!db;
var LS_KEY = 'wb_beauty_product_v1';
var LS_DRAFT = 'wb_beauty_product_draft';
var LS_WT = 'wb_beauty_product_weights';

var state = {
  view: 'product', data: { product: [] }, schema: null, ready: false,
  filter: {}, query: '', editing: null, busy: false
};

function optText(name, val) {
  if (val == null || val === '') return '';
  var sc = state.schema;
  if (sc) {
    for (var i = 0; i < sc.length; i++) {
      if (sc[i].name === name && sc[i].options) {
        for (var j = 0; j < sc[i].options.length; j++) {
          if (sc[i].options[j].id === val) return sc[i].options[j].text;
        }
      }
    }
  }
  return String(val);
}
function optId(name, text) {
  var sc = state.schema;
  if (sc) {
    for (var i = 0; i < sc.length; i++) {
      if (sc[i].name === name && sc[i].options) {
        for (var j = 0; j < sc[i].options.length; j++) {
          if (sc[i].options[j].text === text) return sc[i].options[j].id;
        }
      }
    }
  }
  return text;
}
function optionsFor(name) {
  var sc = state.schema;
  if (sc) {
    for (var i = 0; i < sc.length; i++) {
      if (sc[i].name === name && sc[i].options && sc[i].options.length) return sc[i].options;
    }
  }
  var def = fieldDef(name);
  return (def && def.opts ? def.opts : []).map(function (t) { return { text: t, id: t }; });
}
function msgOf(err) { return (err && (err.message || err.msg)) ? String(err.message || err.msg) : '未知错误'; }

/* ---------- 6. 数据读写（统一出口，上层不直接碰 SDK） ---------- */
function dbQueryAll(DATABASE_ID, startCursor, acc, guard) {
  acc = acc || []; guard = guard || 0;
  if (guard > 100) return Promise.resolve(acc);
  return db.query({ databaseId: DATABASE_ID, pageSize: 200, startCursor: startCursor })
    .then(function (qres) {
      acc = acc.concat(qres.results || []);
      var next = qres.nextCursor;
      if (qres.hasMore && next && next !== startCursor && (qres.results || []).length) {
        return dbQueryAll(DATABASE_ID, next, acc, guard + 1);
      }
      return acc;
    });
}
function dbGetSchema(DATABASE_ID) { return db.getSchema({ databaseId: DATABASE_ID }); }
function dbAdd(DATABASE_ID, payload) { return db.addRecord({ databaseId: DATABASE_ID, properties: payload }); }
function dbUpdate(DATABASE_ID, recordId, payload) { return db.updateRecord({ databaseId: DATABASE_ID, recordId: recordId, properties: payload }); }
function dbDelete(DATABASE_ID, recordId) { return db.deleteRecord({ databaseId: DATABASE_ID, recordId: recordId }); }

function lsRead() { try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}') || {}; } catch (e) { return {}; } }
function lsWrite(d) { try { localStorage.setItem(LS_KEY, JSON.stringify(d)); } catch (e) { } }
function lsDel() { try { localStorage.removeItem(LS_KEY); } catch (e) { } }

function flatFromPayload(name, pv) {
  var f = fieldDef(name) || { t: 'text' };
  if (pv == null) return null;
  if (f.t === 'number') return pv.number;
  if (f.t === 'date') return pv.date;
  if (f.t === 'select') return optText(name, pv.select);
  return pv.text;
}
function loadOne() {
  if (!ONLINE) {
    state.data.product = lsRead().product || [];
    state.ready = true;
    return Promise.resolve();
  }
  return dbGetSchema(DB.product.databaseId).then(function (sc) {
    var list = [];
    ((sc && sc.properties) || []).forEach(function (f) {
      list.push({ name: f.name, type: f.type, options: (f.config && f.config.options) ? f.config.options.slice() : null });
    });
    state.schema = list;
  }).catch(function () { state.schema = null; }).then(function () {
    return dbQueryAll(DB.product.databaseId).then(function (rows) {
      state.data.product = (rows || []).filter(function (r) { return r && r._id; });
      state.ready = true;
    });
  }).catch(function (err) {
    state.ready = true;
    toast('新品库读取失败：' + msgOf(err));
  });
}
function loadAll() {
  setSync('busy', '同步中…');
  return loadOne().then(function () { setSync(ONLINE ? 'ok' : 'off', ONLINE ? '云端已同步' : '离线模式'); });
}
function writeOne(recId, payload) {
  if (!ONLINE) {
    var flat = {};
    for (var fname in payload) { if (Object.prototype.hasOwnProperty.call(payload, fname)) flat[fname] = flatFromPayload(fname, payload[fname]); }
    var all = lsRead();
    var rows = all.product || [];
    if (recId) {
      rows = rows.map(function (r) { if (r._id === recId) { for (var k in flat) r[k] = flat[k]; } return r; });
    } else { flat._id = uid(); rows.push(flat); }
    all.product = rows; lsWrite(all);
    return Promise.resolve();
  }
  return recId ? dbUpdate(DB.product.databaseId, recId, payload) : dbAdd(DB.product.databaseId, payload);
}
function removeOne(recId) {
  if (!ONLINE) {
    var all = lsRead();
    all.product = (all.product || []).filter(function (r) { return r._id !== recId; });
    lsWrite(all);
    return Promise.resolve();
  }
  return dbDelete(DB.product.databaseId, recId);
}
function setSync(kind, text) {
  var d = $('#syncDot');
  d.className = 'sync-dot' + (kind === 'off' ? ' off' : (kind === 'busy' ? ' busy' : ''));
  $('#syncText').textContent = text;
}
/* ---------- 7. 计算层（只读 state，不碰 DOM） ---------- */
var DIMS = [
  { n: '需求缺口', w: 20, basis: '与我方 SKU 重合度' },
  { n: '增长动能', w: 15, basis: '环比增速' },
  { n: '竞争密度', w: 15, basis: '关联达人数（越少越不挤）' },
  { n: '成分与概念壁垒', w: 15, basis: '技术壁垒' },
  { n: '价格带与客群匹配', w: 15, basis: '价格带 + 客群匹配' },
  { n: '法规可行性', w: 10, basis: '备案路径 + 宣称支撑难度' },
  { n: '供应链可行性', w: 10, basis: '预估成本 ÷ 价格' }
];
var DEF_W = DIMS.map(function (d) { return d.w; });

function getWeights() {
  try {
    var a = JSON.parse(localStorage.getItem(LS_WT) || 'null');
    if (a && a.length === DIMS.length && a.every(function (x) { return typeof x === 'number' && x >= 0; })) return a;
  } catch (e) { }
  return DEF_W.slice();
}
function setWeights(a) { try { localStorage.setItem(LS_WT, JSON.stringify(a)); } catch (e) { } }
function resetWeights() { try { localStorage.removeItem(LS_WT); } catch (e) { } }

function txtOf(r, name) {
  var v = r[name];
  if (v == null || v === '') return '';
  return optText(name, v) || String(v);
}

function rateOf(dim, r) {
  if (dim === '需求缺口') {
    var g = txtOf(r, '与我方 SKU 重合度');
    if (g === '全新') return 1;
    if (g === '部分重合') return 0.55;
    if (g === '高度重合') return 0.15;
    return 0.5;
  }
  if (dim === '增长动能') {
    var gr = numOf(r['环比增速']);
    if (gr === null) return 0.5;
    if (gr >= 50) return 1;
    if (gr >= 30) return 0.85;
    if (gr >= 10) return 0.65;
    if (gr >= 0) return 0.45;
    return 0.1;
  }
  if (dim === '竞争密度') {
    var d = numOf(r['关联达人数']);
    if (d === null) return 0.5;
    if (d <= 5) return 1;
    if (d <= 20) return 0.7;
    if (d <= 50) return 0.45;
    return 0.2;
  }
  if (dim === '成分与概念壁垒') {
    var b = txtOf(r, '技术壁垒');
    if (b === '专利技术') return 1;
    if (b === '独家原料') return 0.85;
    if (b === '配方工艺') return 0.6;
    if (b === '无壁垒') return 0.2;
    return 0.5;
  }
  if (dim === '价格带与客群匹配') {
    var p = txtOf(r, '与我方价格带匹配'), c = txtOf(r, '与我方客群匹配');
    if (!p && !c) return 0.5;
    if (p === '匹配' && c === '匹配') return 1;
    if (p === '匹配' || c === '匹配') return 0.65;
    return 0.3;
  }
  if (dim === '法规可行性') {
    var a = txtOf(r, '备案路径'), s = txtOf(r, '宣称支撑难度');
    var ar = a === '普通化妆品备案' ? 1 : (a === '进口备案' ? 0.7 : (a === '特殊化妆品注册' ? 0.35 : (a ? 0.5 : null)));
    var sr = s === '无需评价' ? 1 : (s === '需文献资料' ? 0.75 : (s === '需人体功效试验' ? 0.4 : null));
    if (ar !== null && sr !== null) return (ar + sr) / 2;
    if (ar !== null) return ar;
    if (sr !== null) return sr;
    return 0.5;
  }
  if (dim === '供应链可行性') {
    var cost = numOf(r['预估成本']), price = numOf(r['价格']);
    if (cost === null || price === null || price <= 0) return 0.5;
    var k = cost / price;
    if (k <= 0.2) return 1;
    if (k <= 0.3) return 0.75;
    if (k <= 0.4) return 0.5;
    return 0.25;
  }
  return 0.5;
}
function hasBasis(dim, r) {
  if (dim === '需求缺口') return !!txtOf(r, '与我方 SKU 重合度');
  if (dim === '增长动能') return numOf(r['环比增速']) !== null;
  if (dim === '竞争密度') return numOf(r['关联达人数']) !== null;
  if (dim === '成分与概念壁垒') return !!txtOf(r, '技术壁垒');
  if (dim === '价格带与客群匹配') return !!(txtOf(r, '与我方价格带匹配') || txtOf(r, '与我方客群匹配'));
  if (dim === '法规可行性') return !!(txtOf(r, '备案路径') || txtOf(r, '宣称支撑难度'));
  if (dim === '供应链可行性') return numOf(r['预估成本']) !== null && numOf(r['价格']) !== null;
  return false;
}
function scoreOf(r, w) {
  w = w || getWeights();
  var dims = [], got = 0, sum = 0, filled = 0;
  for (var i = 0; i < DIMS.length; i++) {
    var rate = rateOf(DIMS[i].n, r);
    var has = hasBasis(DIMS[i].n, r);
    if (has) filled++;
    dims.push({ n: DIMS[i].n, basis: DIMS[i].basis, rate: rate, w: w[i], got: rate * w[i], has: has });
    got += rate * w[i];
    sum += w[i];
  }
  return { total: sum > 0 ? got / sum * 100 : 0, dims: dims, filled: filled, of: DIMS.length };
}
function lvOf(total) {
  if (total >= 85) return { k: '打样评估', cls: 'green' };
  if (total >= 70) return { k: '候选池', cls: 'blue' };
  return { k: '留档', cls: 'gray' };
}
var BANDS = ['<100', '100–300', '300–600', '600–1000', '>1000', '未标价'];
function bandOf(price) {
  var p = numOf(price);
  if (p === null) return '未标价';
  if (p < 100) return '<100';
  if (p < 300) return '100–300';
  if (p < 600) return '300–600';
  if (p < 1000) return '600–1000';
  return '>1000';
}
function fmtPct(v) { var n = numOf(v); return n === null ? '—' : (n > 0 ? '+' : '') + n + '%'; }

function recs() { return state.data.product || []; }
function cellText(r, name) {
  var f = fieldDef(name), v = r[name];
  if (f && f.t === 'date') return dayStr(v);
  if (f && f.t === 'select') return optText(name, v);
  return v == null ? '' : String(v);
}
function matches(r) {
  var q = state.query;
  if (q) {
    var hay = '';
    FIELDS.forEach(function (f) { hay += ' ' + (f.t === 'select' ? optText(f.n, r[f.n]) : (r[f.n] == null ? '' : r[f.n])); });
    if (hay.toLowerCase().indexOf(q.toLowerCase()) === -1) return false;
  }
  for (var k in state.filter) {
    if (!state.filter[k]) continue;
    if ((cellText(r, k) || '') !== state.filter[k]) return false;
  }
  return true;
}
function filtered() { return recs().filter(matches); }
function scoredList() {
  var w = getWeights();
  return filtered().map(function (r) { return { r: r, s: scoreOf(r, w) }; });
}
function avgOf(list, f) {
  var vals = list.map(f).filter(function (x) { return x !== null && !isNaN(x); });
  if (!vals.length) return null;
  return vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
}
function bandStats() {
  var list = recs();
  return BANDS.map(function (b) {
    var inB = list.filter(function (r) { return bandOf(r['价格']) === b; });
    return {
      band: b, n: inB.length,
      avgScore: avgOf(inB, function (r) { return scoreOf(r).total; }),
      avgGrowth: avgOf(inB, function (r) { return numOf(r['环比增速']); }),
      revenue: inB.reduce(function (a, r) { return a + (numOf(r['销售额']) || 0); }, 0)
    };
  });
}
function todayItems() {
  var out = [], w = getWeights();
  recs().forEach(function (r) {
    var s = scoreOf(r, w);
    var st = txtOf(r, '决策状态');
    var lv = lvOf(s.total);
    var name = r['商品名称'] || '(未命名)';
    if (st === '待评' && s.filled >= 4) {
      out.push({ id: r._id, title: name, flag: '', o: 1,
        meta: '数据够了（' + s.filled + '/' + s.of + ' 项有依据）· 建议 ' + Math.round(s.total) + ' 分 / ' + lv.k,
        act: 'rate', actText: '按建议定级', to: lv.k });
    }
    var rt = numOf(r['退货率']);
    if (rt !== null && rt >= 15 && st !== '已否决') {
      out.push({ id: r._id, title: name, flag: 'over', o: 0,
        meta: '退货率 <b>' + rt + '%</b> 偏高，去看差评里说了什么',
        act: 'edit', actText: '看差评' });
    }
    if (st === '候选池' && s.total >= 85) {
      out.push({ id: r._id, title: name, flag: 'soon', o: 2,
        meta: '总分 ' + Math.round(s.total) + ' 分，已够打样线',
        act: 'rate', actText: '升级为打样评估', to: '打样评估' });
    }
  });
  out.sort(function (a, b) { return (a.flag === 'over' ? -1 : 0) - (b.flag === 'over' ? -1 : 0) || a.o - b.o; });
  return out.slice(0, 6);
}
/* ---------- 8. 渲染层（只写自己的容器，互不调用） ---------- */
function bindDb(container) {
  var id = DB.product.databaseId;
  $$('.bind', container).forEach(function (el) {
    el.setAttribute('data-sp-bindable', 'database');
    el.setAttribute('data-sp-database-id', id);
  });
}
var STATUS_TAG = {
  '待评': 'amber', '候选池': 'blue', '打样评估': 'green', '已否决': 'gray',
  '全新': 'green', '部分重合': 'amber', '高度重合': 'gray',
  '匹配': 'green', '偏高': 'amber', '偏低': 'amber', '需教育': 'amber', '不符': 'red',
  '普通化妆品备案': 'green', '进口备案': 'amber', '特殊化妆品注册': 'red', '暂无': 'gray',
  '无需评价': 'green', '需文献资料': 'amber', '需人体功效试验': 'red',
  '专利技术': 'green', '独家原料': 'green', '配方工艺': 'blue', '无壁垒': 'gray',
  '抖音罗盘': 'gray', '蝉妈妈': 'gray', 'FastMoss': 'gray', '其他': 'gray'
};
var LV_COLOR = { green: '#1d8a3a', blue: '#0071e3', gray: '#9a9aa0' };

function renderNav() {
  var navHtml = '', tabHtml = '';
  VIEWS.forEach(function (v) {
    var n = v.type === 'list' ? recs().length : '';
    var badge = (n === '' ? '' : '<span class="nav-count">' + n + '</span>');
    navHtml += '<button class="nav-item' + (state.view === v.key ? ' on' : '') + '" data-go="' + v.key + '">' +
      '<svg class="ico" viewBox="0 0 24 24">' + v.icon + '</svg>' +
      '<span class="nav-label">' + esc(v.name) + '</span>' + badge + '</button>';
    tabHtml += '<button class="tab' + (state.view === v.key ? ' on' : '') + '" data-go="' + v.key + '">' +
      '<svg viewBox="0 0 24 24">' + v.icon + '</svg><span>' + esc(v.short) + '</span></button>';
  });
  $('#nav').innerHTML = navHtml;
  $('#tabbar').innerHTML = tabHtml;
}

function renderToday() {
  var items = todayItems(), box = $('#todayList');
  var d = new Date(), wk = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()];
  $('#todayDate').textContent = (d.getMonth() + 1) + '月' + d.getDate() + '日 ' + wk;
  var over = items.filter(function (i) { return i.flag === 'over'; }).length;
  var badge = $('#todayOver');
  if (over > 0) { badge.textContent = '需注意 ' + over; badge.classList.remove('hide'); }
  else badge.classList.add('hide');
  if (!items.length) {
    box.innerHTML = '<div class="today-empty">今天没有要处理的。去新品库补几条商品，或从蝉妈妈导出一批粘进来。</div>';
    return;
  }
  box.innerHTML = items.map(function (i) {
    return '<div class="today-row">' +
      '<span class="today-flag ' + (i.flag || '') + '"></span>' +
      '<div class="today-main"><div class="today-title bind">' + esc(i.title) + '</div>' +
      '<div class="today-meta">' + i.meta + '</div></div>' +
      '<button class="btn sm" data-act="' + i.act + '" data-id="' + i.id + '" data-to="' + esc(i.to || '') + '">' + esc(i.actText) + '</button>' +
      '</div>';
  }).join('');
}

function renderFilterBar() {
  var host = $('#fProduct');
  var html = '';
  MODULE.filterKeys.forEach(function (fn) {
    var cur = state.filter[fn] || '';
    html += '<select class="sel" data-filter="' + esc(fn) + '" style="margin-right:6px">' +
      '<option value="">全部' + esc(fn) + '</option>' +
      optionsFor(fn).map(function (o) { return '<option value="' + esc(o.text) + '"' + (cur === o.text ? ' selected' : '') + '>' + esc(o.text) + '</option>'; }).join('') +
      '</select>';
  });
  if (Object.keys(state.filter).some(function (k) { return state.filter[k]; })) {
    html += '<button class="sel" data-filter-clear="1">清除筛选</button>';
  }
  host.innerHTML = html;
}

function cardHtml(r) {
  var s = scoreOf(r), lv = lvOf(s.total), st = txtOf(r, '决策状态');
  var title = r['商品名称'] || '(未命名)';
  var sub = [txtOf(r, '品牌'), txtOf(r, '细分品类'), txtOf(r, '概念标签')].filter(Boolean).join(' · ');
  var price = numOf(r['价格']), growth = numOf(r['环比增速']), rt = numOf(r['退货率']);
  var sales = numOf(r['销量']) || numOf(r['销售额']);
  var numTxt = sales === null ? '' : (numOf(r['销量']) !== null ? '销 ' + fmtNum(r['销量']) : '');
  var scoreTxt = s.filled === 0
    ? '<span class="mini">未评分</span>'
    : '<span class="score-pill" style="color:' + LV_COLOR[lv.cls] + '"><b>' + Math.round(s.total) + '</b><i>分</i></span>';
  return '<article class="card">' +
    '<div class="card-top"><div class="card-title bind">' + esc(title) + '</div>' + scoreTxt + '</div>' +
    (sub ? '<div class="card-note">' + esc(sub) + '</div>' : '') +
    (r['选品笔记'] ? '<div class="card-note">' + esc(firstLine(r['选品笔记'], 54)) + '</div>' : '') +
    '<div class="card-foot">' +
    (s.filled > 0 ? '<span class="tag ' + lv.cls + '">' + lv.k + '</span>' : '') +
    '<span class="tag ' + (STATUS_TAG[st] || 'gray') + '">' + esc(st || '待评') + '</span>' +
    (price !== null ? '<span class="mini">' + fmtMoney(price) + '</span>' : '') +
    (growth !== null ? '<span class="mini">' + fmtPct(growth) + '</span>' : '') +
    (numTxt ? '<span class="mini">' + numTxt + '</span>' : '') +
    (rt !== null && rt >= 15 ? '<span class="mini" style="color:var(--red)">退货 ' + rt + '%</span>' : '') +
    '<span class="card-acts">' +
    '<button class="icon-btn" data-edit="' + r._id + '" title="编辑"><svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg></button>' +
    '<button class="icon-btn" data-del="' + r._id + '" title="删除"><svg viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg></button>' +
    '</span></div></article>';
}

function renderProduct() {
  var host = $('#productBody'), list = filtered();
  if (!list.length) {
    host.innerHTML = '<div class="empty"><b>' + (recs().length ? '没有符合筛选的商品' : '新品库还是空的') + '</b>' +
      (recs().length
        ? '换个筛选条件，或清除筛选。'
        : '点右上角「批量导入」，把蝉妈妈导出的表格或 FastMoss 榜单直接粘进来；也可以点「新建」手工录一条。') + '</div>';
    return;
  }
  list = list.slice().sort(function (a, b) {
    var d = scoreOf(b).total - scoreOf(a).total;
    if (Math.abs(d) > 0.01) return d;
    return String(a['商品名称'] || '').localeCompare(String(b['商品名称'] || ''), 'zh');
  });
  host.innerHTML = '<div class="grid">' + list.map(cardHtml).join('') + '</div>';
  bindDb(host);
}

function renderScore() {
  var host = $('#scoreBody'), w = getWeights(), sum = w.reduce(function (a, b) { return a + b; }, 0);
  var list = scoredList().slice().sort(function (a, b) { return b.s.total - a.s.total; });

  var html = '<div class="panelbox"><h3>维度权重</h3>' +
    '<div class="h3s">拖动调整。每一项的分值 = 该维度得分率 × 权重，再按总权重归一成 100 分。</div>' +
    '<div class="wts">' + DIMS.map(function (d, i) {
      return '<div class="wt-row"><label>' + esc(d.n) + '</label>' +
        '<input type="range" min="0" max="30" step="1" value="' + w[i] + '" data-wt="' + i + '">' +
        '<span class="wt-out">' + w[i] + '</span></div>';
    }).join('') + '</div>' +
    '<div class="wt-sum">合计 <b class="' + (sum === 100 ? 'ok-flag' : 'warn-flag') + '">' + sum + '</b> ' +
    (sum === 100 ? '（标准配置）' : '（不是 100 也可以，页面会按总权重归一）') +
    '<button class="sel" id="btnResetWt" style="margin-left:auto">恢复默认</button></div></div>';

  html += '<div class="panelbox"><h3>每个维度看什么</h3>' +
    '<div class="h3s">分数是从你填的字段自动推出来的，不是拍脑袋——所以字段越全，分越准。</div>' +
    '<div class="tbl-wrap"><table><thead><tr><th>维度</th><th>权重</th><th>依据字段</th><th>满分条件</th><th>零分条件</th></tr></thead><tbody>' +
    [
      ['需求缺口', '与我方 SKU 重合度', '标「全新」', '标「高度重合」'],
      ['增长动能', '环比增速', '增速 ≥ 50%', '增速为负'],
      ['竞争密度', '关联达人数', '≤ 5 个达人', '> 50 个达人'],
      ['成分与概念壁垒', '技术壁垒', '标「专利技术」', '标「无壁垒」'],
      ['价格带与客群匹配', '价格带 + 客群匹配', '两项都「匹配」', '两项都不匹配'],
      ['法规可行性', '备案路径 + 宣称支撑难度', '普通备案 + 无需评价', '特殊注册 + 需人体试验'],
      ['供应链可行性', '预估成本 ÷ 价格', '成本占售价 ≤ 20%', '成本占售价 > 40%']
    ].map(function (row, i) {
      return '<tr><td><b>' + esc(row[0]) + '</b></td><td class="num">' + w[i] + '</td>' +
        '<td>' + esc(row[1]) + '</td><td>' + esc(row[2]) + '</td><td>' + esc(row[3]) + '</td></tr>';
    }).join('') + '</tbody></table></div>' +
    '<div class="lv-legend">' +
    '<span><i class="dot" style="background:#1d8a3a"></i>85 分及以上 → 进打样评估</span>' +
    '<span><i class="dot" style="background:#0071e3"></i>70–84 分 → 进候选池</span>' +
    '<span><i class="dot" style="background:#9a9aa0"></i>70 分以下 → 留档观察</span>' +
    '</div></div>';

  html += '<div class="sec-head"><h2>打分排名</h2><span class="sub">' +
    (list.length ? '共 ' + list.length + ' 个商品，按总分降序' : '') + '</span></div>';
  if (!list.length) {
    html += '<div class="empty"><b>还没有可打分的商品</b>先把商品录进来，分数会自动算。</div>';
  } else {
    html += '<div class="tbl-wrap"><table><thead><tr><th>商品</th><th style="text-align:right">总分</th><th>建议</th>' +
      '<th>最弱的一项</th><th>数据完整度</th><th></th></tr></thead><tbody>' +
      list.map(function (x) {
        var r = x.r, s = x.s, lv = lvOf(s.total);
        var weak = s.dims.slice().sort(function (a, b) { return a.rate - b.rate; })[0];
        return '<tr><td class="wrap bind">' + esc(r['商品名称'] || '(未命名)') + '</td>' +
          '<td class="num bind" style="font-weight:600;color:' + LV_COLOR[lv.cls] + '">' +
          (s.filled === 0 ? '—' : s.total.toFixed(1)) + '</td>' +
          '<td><span class="tag ' + lv.cls + '">' + lv.k + '</span></td>' +
          '<td>' + esc(weak.n) + ' <span style="color:var(--text3)">' + Math.round(weak.rate * 100) + '%</span></td>' +
          '<td>' + s.filled + ' / ' + s.of + '</td>' +
          '<td><span class="card-acts">' +
          '<button class="icon-btn" data-edit="' + r._id + '" title="编辑"><svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg></button>' +
          '</span></td></tr>';
      }).join('') + '</tbody></table></div>';
  }
  host.innerHTML = html;
  bindDb(host);
}

function renderBoard() {
  var host = $('#boardBody'), list = scoredList();
  var total = recs().length;
  var ready = list.filter(function (x) { return x.s.total >= 70 && x.s.filled > 0; }).length;
  var sample = list.filter(function (x) { return x.s.total >= 85 && x.s.filled > 0; }).length;
  var avg = avgOf(list.filter(function (x) { return x.s.filled > 0; }), function (x) { return x.s.total; });
  var hot = list.filter(function (x) { var g = numOf(x.r['环比增速']); return g !== null && g >= 30; }).length;

  var html = '<div class="kpis">' +
    [['新品总数', total, '已建档的商品'], ['够候选池', ready, '70 分及以上'],
     ['够打样线', sample, '85 分及以上'], ['平均总分', avg === null ? '—' : avg.toFixed(1), '有数据的商品'],
     ['高增速品', hot, '环比 ≥ 30%']].map(function (k) {
      return '<div class="kpi"><div class="kpi-l">' + k[0] + '</div><div class="kpi-v bind">' + esc(k[1]) + '</div><div class="kpi-s">' + k[2] + '</div></div>';
    }).join('') + '</div>';

  html += '<div class="panelbox"><h3>增速 × 得分 分布</h3>' +
    '<div class="h3s">右上角是「有人买、还值得做」的区。横轴越往右涨得越快，纵轴越高越符合我方资源。</div>' +
    scatterSvg(list) + '</div>';

  var stats = bandStats().filter(function (b) { return b.n > 0; });
  var maxN = stats.length ? Math.max.apply(null, stats.map(function (b) { return b.n; })) : 0;
  html += '<div class="panelbox"><h3>各价格带的密度</h3>' +
    '<div class="h3s">条越长说明这个价格带越拥挤；结合平均分看，就是缺口在哪。</div>';
  if (!stats.length) {
    html += '<div class="today-empty">还没有带价格的商品。补上价格，这里就能看出哪个价格带被填满了。</div>';
  } else {
    html += '<div class="bars">' + stats.map(function (b) {
      var wd = maxN ? Math.round(b.n / maxN * 100) : 0;
      return '<div class="pb-row"><span class="pb-name">' + esc(b.band) + '</span>' +
        '<span class="pb-bar"><span class="pb-fill" style="width:' + wd + '%"></span></span>' +
        '<span class="pb-val">' + b.n + ' 个' +
        (b.avgScore === null ? '' : ' · 均分 ' + b.avgScore.toFixed(0)) +
        (b.avgGrowth === null ? '' : ' · ' + fmtPct(Math.round(b.avgGrowth))) + '</span></div>';
    }).join('') + '</div>';
  }
  html += '</div>';

  var picks = list.filter(function (x) {
    var g = numOf(x.r['环比增速']);
    return x.s.filled > 0 && x.s.total >= 70 && (g === null || g > 0);
  }).sort(function (a, b) { return b.s.total - a.s.total; }).slice(0, 6);
  html += '<div class="panelbox"><h3>值得先看这几个</h3>' +
    '<div class="h3s">同时满足「够到候选池」和「没有在跌」的商品。</div>';
  if (!picks.length) {
    html += '<div class="today-empty">还没有够分的商品。把字段补全，分数会自动上来。</div>';
  } else {
    html += '<div class="rows">' + picks.map(function (x) {
      var r = x.r, lv = lvOf(x.s.total);
      var sub = [txtOf(r, '与我方 SKU 重合度') ? '重合度 ' + txtOf(r, '与我方 SKU 重合度') : '',
        numOf(r['价格']) !== null ? fmtMoney(r['价格']) : '',
        numOf(r['环比增速']) !== null ? '环比 ' + fmtPct(r['环比增速']) : '',
        txtOf(r, '概念标签')].filter(Boolean).join(' · ');
      return '<div class="row"><div class="row-main">' +
        '<div class="row-title bind">' + esc(r['商品名称'] || '(未命名)') +
        '<span class="tag ' + lv.cls + '">' + x.s.total.toFixed(0) + ' 分</span></div>' +
        '<div class="row-sub">' + esc(sub) + '</div></div>' +
        '<div class="row-right"><button class="icon-btn" data-edit="' + r._id + '" title="编辑">' +
        '<svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg></button></div></div>';
    }).join('') + '</div>';
  }
  html += '</div>';

  host.innerHTML = html;
  bindDb(host);
}

function scatterSvg(list) {
  var pts = list.filter(function (x) { return numOf(x.r['环比增速']) !== null && x.s.filled > 0; });
  var W = 680, H = 320, padL = 46, padR = 18, padT = 18, padB = 38;
  var pw = W - padL - padR, ph = H - padT - padB;
  if (!pts.length) {
    return '<div class="today-empty">还没有同时具备「环比增速」和评分依据的商品，暂时画不出分布。</div>';
  }
  var xs = pts.map(function (x) { return numOf(x.r['环比增速']); });
  var ys = pts.map(function (x) { return x.s.total; });
  var xLo = Math.min.apply(null, xs), xHi = Math.max.apply(null, xs);
  var yLo = Math.min.apply(null, ys), yHi = Math.max.apply(null, ys);
  if (xHi - xLo < 10) { xLo -= 5; xHi += 5; }
  if (yHi - yLo < 10) { yLo -= 5; yHi += 5; }
  xLo = Math.floor(xLo / 10) * 10; xHi = Math.ceil(xHi / 10) * 10;
  yLo = Math.max(0, Math.floor(yLo / 10) * 10 - 5); yHi = Math.min(100, Math.ceil(yHi / 10) * 10 + 5);
  if (xHi === xLo) xHi = xLo + 10;
  if (yHi === yLo) yHi = yLo + 10;
  var sx = function (v) { return padL + (v - xLo) / (xHi - xLo) * pw; };
  var sy = function (v) { return padT + (1 - (v - yLo) / (yHi - yLo)) * ph; };

  var grid = '', gx, gy;
  for (gy = yLo; gy <= yHi + 0.001; gy += Math.max(10, Math.round((yHi - yLo) / 4 / 10) * 10)) {
    grid += '<line x1="' + padL + '" y1="' + sy(gy).toFixed(1) + '" x2="' + (W - padR) + '" y2="' + sy(gy).toFixed(1) + '" stroke="#efeff2" stroke-width="1"/>' +
      '<text x="' + (padL - 8) + '" y="' + (sy(gy) + 4).toFixed(1) + '" font-size="10" fill="#9a9aa0" text-anchor="end">' + Math.round(gy) + '</text>';
  }
  for (gx = xLo; gx <= xHi + 0.001; gx += Math.max(10, Math.round((xHi - xLo) / 5 / 10) * 10)) {
    grid += '<line x1="' + sx(gx).toFixed(1) + '" y1="' + padT + '" x2="' + sx(gx).toFixed(1) + '" y2="' + (H - padB) + '" stroke="#f6f6f8" stroke-width="1"/>' +
      '<text x="' + sx(gx).toFixed(1) + '" y="' + (H - padB + 16) + '" font-size="10" fill="#9a9aa0" text-anchor="middle">' + (gx > 0 ? '+' : '') + Math.round(gx) + '%</text>';
  }
  var thresh = (yLo <= 70 && yHi >= 70)
    ? '<line x1="' + padL + '" y1="' + sy(70).toFixed(1) + '" x2="' + (W - padR) + '" y2="' + sy(70).toFixed(1) + '" stroke="#c9e0fb" stroke-width="1" stroke-dasharray="4 3"/>' +
      '<text x="' + (W - padR) + '" y="' + (sy(70) - 5).toFixed(1) + '" font-size="10" fill="#0071e3" text-anchor="end">候选线 70</text>'
    : '';
  var dots = pts.map(function (x) {
    var lv = lvOf(x.s.total);
    return '<circle cx="' + sx(numOf(x.r['环比增速'])).toFixed(1) + '" cy="' + sy(x.s.total).toFixed(1) + '" r="5" fill="' + LV_COLOR[lv.cls] + '" fill-opacity="0.72" stroke="#fff" stroke-width="1"><title>' +
      esc(x.r['商品名称'] || '') + '　' + x.s.total.toFixed(1) + ' 分　' + fmtPct(numOf(x.r['环比增速'])) + '</title></circle>';
  }).join('');
  return '<div class="scatter-wrap"><svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="商品增速与得分分布散点图">' +
    grid + thresh + dots +
    '<line x1="' + padL + '" y1="' + (H - padB) + '" x2="' + (W - padR) + '" y2="' + (H - padB) + '" stroke="#e5e5ea" stroke-width="1"/>' +
    '<line x1="' + padL + '" y1="' + padT + '" x2="' + padL + '" y2="' + (H - padB) + '" stroke="#e5e5ea" stroke-width="1"/>' +
    '</svg></div>' +
    '<div class="lv-legend" style="margin-top:10px">' +
    '<span><i class="dot" style="background:#1d8a3a"></i>够打样线</span>' +
    '<span><i class="dot" style="background:#0071e3"></i>够候选池</span>' +
    '<span><i class="dot" style="background:#9a9aa0"></i>先留档</span>' +
    '<span style="color:var(--text3)">圆点悬停可看商品名</span></div>';
}

function renderShell() {
  var v = viewDef(state.view);
  $('#pageTitle').textContent = v.name;
  $('#pageDesc').textContent = v.desc;
  $('#btnNew').classList.toggle('hide', v.type !== 'list');
  $('#btnImport').classList.toggle('hide', v.type !== 'list');
  $$('.view').forEach(function (el) { el.classList.toggle('on', el.getAttribute('data-view') === state.view); });
}

/* 唯一刷新入口：按固定顺序调度所有渲染，渲染函数之间互不调用 */
function refreshAll() {
  renderShell();
  renderNav();
  renderToday();
  renderFilterBar();
  renderProduct();
  renderScore();
  renderBoard();
}
/* ---------- 9. 表单抽屉 ---------- */
var formVals = {}, draftTimer = null;
function openDrawer(sel) { $(sel).classList.add('on'); $('#mask').classList.add('on'); }
function closeDrawers() {
  $$('.drawer').forEach(function (d) { d.classList.remove('on'); });
  $('#mask').classList.remove('on');
}
function toValue(f, v) {
  var s = v == null ? '' : String(v);
  if (f.t === 'number') return s === '' ? null : { number: Number(s) };
  if (f.t === 'date') return s === '' ? null : { date: s };
  if (f.t === 'select') return s === '' ? null : { select: optId(f.n, s) };
  return { text: s };
}
function fromValue(f, raw) {
  if (raw == null) return '';
  if (f.t === 'number') return String(raw);
  if (f.t === 'date') return dayStr(raw);
  if (f.t === 'select') return optText(f.n, raw);
  return String(raw);
}
function fieldHtml(f) {
  var v = formVals[f.n] || '';
  var label = '<label>' + esc(f.n) + (f.req ? ' <span style="color:var(--red)">*</span>' : '') + '</label>';
  if (f.t === 'textarea') {
    return '<div class="field">' + label + '<textarea data-f="' + esc(f.n) + '" placeholder="' + esc(f.ph || '') + '">' + esc(v) + '</textarea></div>';
  }
  if (f.t === 'select') {
    return '<div class="field">' + label + '<div class="opt-row" data-optgroup="' + esc(f.n) + '">' +
      '<button type="button" class="opt' + (v === '' ? ' on' : '') + '" data-opt="" data-of="' + esc(f.n) + '">未选</button>' +
      optionsFor(f.n).map(function (o) {
        return '<button type="button" class="opt' + (v === o.text ? ' on' : '') + '" data-opt="' + esc(o.text) + '" data-of="' + esc(f.n) + '">' + esc(o.text) + '</button>';
      }).join('') + '</div></div>';
  }
  var type = f.t === 'number' ? 'number' : (f.t === 'date' ? 'date' : 'text');
  return '<div class="field">' + label + '<input type="' + type + '" data-f="' + esc(f.n) + '" value="' + esc(v) + '" placeholder="' + esc(f.ph || '') + '"></div>';
}
function formGroupsHtml() {
  return GROUPS.map(function (g) {
    var fs = FIELDS.filter(function (f) { return f.g === g; });
    if (!fs.length) return '';
    return '<div class="fgroup"><div class="fgroup-t">' + esc(g) + '</div>' + fs.map(fieldHtml).join('') + '</div>';
  }).join('');
}
function openForm(rec) {
  state.editing = { id: rec ? rec._id : null };
  formVals = {};
  FIELDS.forEach(function (f) { formVals[f.n] = rec ? fromValue(f, rec[f.n]) : ''; });
  if (!rec) {
    FIELDS.forEach(function (f) { if (!formVals[f.n] && f.def === 'today') formVals[f.n] = todayStr(); else if (!formVals[f.n] && f.def) formVals[f.n] = f.def; });
    var d = readDraft();
    if (d) { for (var k in d) { if (formVals[k] === '' && d[k]) formVals[k] = d[k]; } }
  }
  $('#formTitle').textContent = rec ? '编辑商品' : '新建商品';
  $('#formBody').innerHTML = formGroupsHtml();
  openDrawer('#formDrawer');
}
function collectForm() {
  $$('#formBody [data-f]').forEach(function (el) { formVals[el.getAttribute('data-f')] = el.value; });
  return formVals;
}
function readDraft() {
  try { var d = JSON.parse(localStorage.getItem(LS_DRAFT) || 'null'); if (d && !d.id) return d.vals || null; } catch (e) { }
  return null;
}
function saveDraft() {
  if (!state.editing) return;
  try { localStorage.setItem(LS_DRAFT, JSON.stringify({ id: state.editing.id, vals: collectForm() })); } catch (e) { }
}
function clearDraft() { try { localStorage.removeItem(LS_DRAFT); } catch (e) { } }
function saveForm() {
  collectForm();
  var payload = {}, missing = [];
  FIELDS.forEach(function (f) {
    var v = formVals[f.n];
    if (f.req && !String(v == null ? '' : v).trim()) missing.push(f.n);
    var pv = toValue(f, v);
    if (pv !== null) payload[f.n] = pv;
    else if (state.editing.id && (f.t === 'text' || f.t === 'textarea')) payload[f.n] = { text: '' };
  });
  if (missing.length) { toast('还差必填：' + missing.join('、')); return; }
  var btn = $('#formSave'); btn.disabled = true; btn.textContent = '保存中…';
  writeOne(state.editing.id, payload).then(function () {
    clearDraft(); closeDrawers(); toast(state.editing.id ? '已保存' : '已新建');
    return refreshTable();
  }).catch(function (err) {
    toast('保存失败：' + msgOf(err));
  }).then(function () { btn.disabled = false; btn.textContent = '保存'; });
}
function refreshTable() { return loadOne().then(function () { refreshAll(); }); }

/* ---------- 10. 批量导入（对齐三个平台的导出字段） ---------- */
var ALIAS = {
  '商品名称': ['商品名称', '商品名', '商品标题', '标题', '名称', '商品', 'title', 'productname'],
  '品牌': ['品牌', '品牌名', '店铺', '店铺名称', 'shopname', 'brand'],
  '商品ID': ['商品id', '商品编号', '货号', 'productid'],
  '价格': ['价格', '单价', '到手价', '售价', '客单价', '平均客单价', 'price'],
  '销量': ['销量', '销售量', '月销量', '近30天销量', '销售件数', '总销量', 'unitssold', 'totalsalecnt'],
  '销售额': ['销售额', '成交额', '总额', 'gmv', 'usdgmv', 'totalsalegmvamt'],
  '环比增速': ['环比增速', '环比', '增速', '增长率', '增长', 'growthrate'],
  '关联达人数': ['关联达人数', '达人数', '带货达人数', '关联达人'],
  '退货率': ['退货率', '退款率'],
  '评分': ['评分', '好评率', 'rating'],
  '评价数': ['评价数', '评论数'],
  '榜单排名': ['榜单排名', '排名', '名次', '榜单'],
  '所属市场': ['所属市场', '国家', '地区', '市场', 'region'],
  '上市日期': ['上架时间', '上市日期', '上市时间', '首次上架', '发布时间'],
  '品类': ['品类', '类目', '分类'],
  '细分品类': ['细分品类', '二级类目', '子类目', '三级类目'],
  '核心功效成分': ['核心功效成分', '核心成分', '成分', '功效成分'],
  '概念标签': ['概念标签', '概念', '标签', '卖点'],
  '功效宣称': ['功效宣称', '宣称'],
  '剂型': ['剂型', '形态'],
  '数据来源': ['数据来源', '来源']
};
var LOOKUP = {};
(function () {
  for (var k in ALIAS) { LOOKUP[normKey(k)] = k; ALIAS[k].forEach(function (a) { LOOKUP[normKey(a)] = k; }); }
})();
function normKey(s) { return String(s == null ? '' : s).replace(/[\s_\-]/g, '').replace(/[（(][^）)]*[）)]/g, '').toLowerCase(); }
function mapColumn(name) {
  var nk = normKey(name);
  if (!nk) return null;
  if (LOOKUP[nk]) return LOOKUP[nk];
  var best = null, bestLen = 0;
  for (var k in ALIAS) {
    var list = ALIAS[k].concat([k]);
    for (var i = 0; i < list.length; i++) {
      var a = normKey(list[i]);
      if (a && a.length > bestLen && (nk.indexOf(a) >= 0 || a.indexOf(nk) >= 0)) { best = k; bestLen = a.length; }
    }
  }
  return best;
}
function splitLine(line, sep) {
  var out = [], cur = '', q = false;
  for (var i = 0; i < line.length; i++) {
    var c = line.charAt(i);
    if (q) {
      if (c === '"') { if (line.charAt(i + 1) === '"') { cur += '"'; i++; } else q = false; }
      else cur += c;
    } else if (c === '"') q = true;
    else if (c === sep) { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out.map(function (s) { return s.trim(); });
}
function parseSheet(text) {
  var lines = String(text).replace(/\r\n?/g, '\n').split('\n').filter(function (l) { return l.trim() !== ''; });
  if (!lines.length) return [];
  var tabN = (lines[0].match(/\t/g) || []).length;
  var comN = (lines[0].match(/,/g) || []).length;
  var sep = (tabN > 0 && tabN >= comN) ? '\t' : (comN > 0 ? ',' : '\t');
  return lines.map(function (l) { return splitLine(l, sep); });
}
function parseNum(v) {
  if (v == null || v === '') return null;
  var s = String(v).replace(/[,，\s¥$€£%]/g, '').replace(/(元|件|个|人|分)$/, '');
  var m = /(-?\d+(?:\.\d+)?)\s*(万|w|k|千)?/i.exec(s);
  if (!m) return null;
  var n = Number(m[1]);
  if (isNaN(n)) return null;
  var u = String(m[2] || '').toLowerCase();
  if (u === '万' || u === 'w') n *= 10000;
  else if (u === 'k' || u === '千') n *= 1000;
  return Math.round(n * 100) / 100;
}
function parseDate(v) {
  if (!v) return null;
  var m = /(\d{4})[-\/年.](\d{1,2})(?:[-\/月.](\d{1,2}))?/.exec(String(v));
  if (!m) return null;
  return m[1] + '-' + pad(Number(m[2])) + '-' + pad(Number(m[3] || 1));
}
function matchOpt(name, val) {
  var opts = optionsFor(name).map(function (o) { return o.text; });
  var v = String(val == null ? '' : val).trim();
  if (!v) return null;
  for (var i = 0; i < opts.length; i++) { if (opts[i] === v) return opts[i]; }
  for (var j = 0; j < opts.length; j++) { if (v.indexOf(opts[j]) >= 0 || opts[j].indexOf(v) >= 0) return opts[j]; }
  return null;
}
function payloadFromRow(obj) {
  var payload = {};
  for (var name in obj) {
    if (!Object.prototype.hasOwnProperty.call(obj, name)) continue;
    var val = obj[name], f = fieldDef(name);
    if (!f || val == null || val === '') continue;
    if (f.t === 'number') { var n = parseNum(val); if (n !== null) payload[name] = { number: n }; }
    else if (f.t === 'date') { var d = parseDate(val); if (d) payload[name] = { date: d }; }
    else if (f.t === 'select') { var o = matchOpt(name, val); if (o) payload[name] = { select: optId(name, o) }; }
    else payload[name] = { text: String(val) };
  }
  return payload;
}
var impRows = null;
function doParseImport() {
  var text = $('#impText').value;
  var grid = parseSheet(text), stat = $('#impStat');
  impRows = null;
  if (!grid.length) { stat.className = 'imp-stat bad'; stat.textContent = '没读到内容，检查一下是否粘贴成功。'; return; }
  var head = grid[0], cols = head.map(mapColumn);
  var mapped = cols.filter(Boolean).length;
  var hasHeader = mapped >= 2;
  var bodyRows = hasHeader ? grid.slice(1) : grid;
  if (hasHeader && !cols.some(function (c) { return c === '商品名称'; })) {
    var gi = head.findIndex(function (h) { return /名称|标题|商品|title|product/i.test(h); });
    if (gi >= 0) cols[gi] = '商品名称';
  }
  if (!hasHeader) {
    cols = ['商品名称', '品牌', '商品ID', '价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分'];
  }
  var useCols = [];
  cols.forEach(function (c, i) { if (c) useCols.push({ i: i, n: c }); });
  var out = [];
  bodyRows.forEach(function (row) {
    var obj = {};
    useCols.forEach(function (u) { if (row[u.i] != null && row[u.i] !== '') obj[u.n] = row[u.i]; });
    if (!obj['商品名称']) return;
    out.push(obj);
  });
  if (!out.length) { stat.className = 'imp-stat bad'; stat.textContent = '识别到 ' + bodyRows.length + ' 行，但没有一列对得上商品名称。检查首行是不是列名。'; return; }
  impRows = out;
  var names = useCols.map(function (u) { return u.n; });
  $('#impMap').innerHTML = '<div><b>识别到 ' + out.length + ' 行</b>' + (hasHeader ? '（按首行列名对应）' : '（无列名，按默认列序对应）') + '</div>' +
    '<div>对应字段：' + names.map(function (n) { return esc(n); }).join('、') + '</div>' +
    (names.indexOf('价格') < 0 && names.indexOf('销量') < 0 ? '<div style="color:var(--amber)">没识别到价格或销量列，导入后这些商品不会有分数。</div>' : '');
  stat.className = 'imp-stat';
  stat.textContent = '再点一次「确认导入」写入这 ' + out.length + ' 条。已存在的同名商品会自动跳过。';
  $('#impDo').textContent = '确认导入';
}
function doWriteImport() {
  if (!impRows || !impRows.length) return;
  var exist = {};
  recs().forEach(function (r) { exist[String(r['商品名称'] || '').trim()] = 1; });
  var fresh = [], skip = 0;
  impRows.forEach(function (o) {
    var nm = String(o['商品名称'] || '').trim();
    if (exist[nm]) { skip++; return; }
    exist[nm] = 1;
    fresh.push(o);
  });
  if (!fresh.length) { toast('这 ' + skip + ' 条都已经在库里了'); impRows = null; $('#impDo').textContent = '识别并导入'; return; }
  var btn = $('#impDo'); btn.disabled = true; btn.textContent = '导入中…';
  var chain = Promise.resolve(), ok = 0;
  fresh.forEach(function (o) {
    var payload = payloadFromRow(o);
    if (!payload['商品名称']) return;
    chain = chain.then(function () { return writeOne(null, payload).then(function () { ok++; }); });
  });
  chain.then(function () { return refreshTable(); }).then(function () {
    toast('导入完成：新增 ' + ok + ' 条' + (skip ? '，跳过重复 ' + skip + ' 条' : ''));
    impRows = null; $('#impText').value = ''; $('#impMap').innerHTML = '';
    var stat = $('#impStat'); stat.className = 'imp-stat'; stat.textContent = '本次新增 ' + ok + ' 条。可以继续粘贴下一批。';
    btn.disabled = false; btn.textContent = '识别并导入';
  }).catch(function (err) {
    btn.disabled = false; btn.textContent = '确认导入';
    toast('导入出错：' + msgOf(err));
  });
}

/* ---------- 11. 设置 / 备份 ---------- */
function download(content, filename, mime) {
  var blob = new Blob([content], { type: mime });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(a.href); }, 3000);
}
function exportJson() {
  var dump = { app: '全球新品选品台', exportedAt: new Date().toISOString(), weights: getWeights(), data: state.data };
  download(JSON.stringify(dump, null, 2), '全球新品选品台_备份_' + todayStr() + '.json', 'application/json');
  toast('已导出备份文件');
}
function exportCsv() {
  var heads = FIELDS.map(function (f) { return f.n; });
  var lines = [heads.join(',')];
  recs().forEach(function (r) {
    lines.push(heads.map(function (h) {
      var v = h === MODULE.dateField ? dayStr(r[h]) : r[h];
      return '"' + String(v == null ? '' : (typeof v === 'object' ? (v.text || v.link || '') : v)).replace(/"/g, '""') + '"';
    }).join(','));
  });
  download('\ufeff' + lines.join('\r\n'), '全球新品库_' + todayStr() + '.csv', 'text/csv;charset=utf-8');
  toast('已导出 CSV');
}
function importJson(text) {
  var parsed;
  try { parsed = JSON.parse(text); } catch (e) { toast('文件不是有效的 JSON'); return; }
  if (parsed && parsed.weights) setWeights(parsed.weights);
  var data = (parsed && parsed.data) ? parsed.data : parsed;
  var rows = data && data.product;
  if (!Array.isArray(rows) || !rows.length) { toast('文件里没有可恢复的新品记录'); return; }
  var chain = Promise.resolve(), added = 0;
  rows.forEach(function (r) {
    var payload = {};
    FIELDS.forEach(function (f) {
      var pv = toValue(f, fromValue(f, r[f.n]));
      if (pv !== null) payload[f.n] = pv;
    });
    if (!payload['商品名称']) return;
    chain = chain.then(function () { added++; return writeOne(null, payload); });
  });
  chain.then(function () { return refreshTable(); })
    .then(function () { toast('导入完成，新增 ' + added + ' 条'); })
    .catch(function (err) { toast('导入出错：' + msgOf(err)); });
}
function clearDemo() {
  var jobs = [];
  recs().forEach(function (r) { if (isDemo(r)) jobs.push(removeOne(r._id)); });
  if (!jobs.length) { toast('没有找到示例数据'); return; }
  Promise.all(jobs).then(function () { return loadOne(); }).then(function () { refreshAll(); toast('示例数据已清空'); })
    .catch(function (err) { toast('清空失败：' + msgOf(err)); });
}
function clearAll() {
  if (!window.confirm('确定要清空全部新品记录吗？不可恢复。')) return;
  if (!window.confirm('再确认一次：真的删除新品库里的全部商品？')) return;
  var jobs = recs().map(function (r) { return removeOne(r._id); });
  if (!ONLINE) lsDel();
  Promise.all(jobs).then(function () { lsDel(); return loadOne(); }).then(function () { refreshAll(); toast('已清空全部记录'); })
    .catch(function (err) { toast('清空失败：' + msgOf(err)); });
}
/* ---------- 12. 今日动作 ---------- */
function doAction(act, id, to) {
  var r = null;
  recs().forEach(function (x) { if (x._id === id) r = x; });
  if (!r) return;
  if (act === 'edit') { openForm(r); return; }
  if (act === 'rate') {
    writeOne(id, { '决策状态': { select: optId('决策状态', to) } })
      .then(function () { return refreshTable(); })
      .then(function () { toast('已设为「' + to + '」'); })
      .catch(function (err) { toast('更新失败：' + msgOf(err)); });
  }
}
function delRecord(id) {
  var name = '';
  recs().forEach(function (r) { if (r._id === id) name = r['商品名称']; });
  if (!window.confirm('删除「' + (name || '这个商品') + '」？无法恢复。')) return;
  removeOne(id).then(function () { return refreshTable(); }).then(function () { toast('已删除'); })
    .catch(function (err) { toast('删除失败：' + msgOf(err)); });
}
function updateWtSum() {
  var arr = getWeights();
  var sum = arr.reduce(function (a, b) { return a + b; }, 0);
  var el = $('.wt-sum b');
  if (el) { el.textContent = sum; el.className = sum === 100 ? 'ok-flag' : 'warn-flag'; }
}

/* ---------- 13. 事件绑定 ---------- */
function bindEvents() {
  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('[data-go],[data-edit],[data-del],[data-act],[data-opt],[data-filter-clear],#btnResetWt') : null;
    if (!t) return;
    var g;
    if (t.id === 'btnResetWt') { resetWeights(); refreshAll(); toast('权重已恢复默认'); return; }
    if ((g = t.getAttribute('data-go'))) { state.view = g; refreshAll(); return; }
    if (t.hasAttribute('data-filter-clear')) { MODULE.filterKeys.forEach(function (k) { state.filter[k] = ''; }); refreshAll(); return; }
    if (t.hasAttribute('data-opt')) {
      var of = t.getAttribute('data-of');
      formVals[of] = t.getAttribute('data-opt');
      $$('[data-of="' + of + '"]', $('#formBody')).forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-opt') === formVals[of]); });
      saveDraft(); return;
    }
    if ((g = t.getAttribute('data-edit'))) {
      var r = null; recs().forEach(function (x) { if (x._id === t.getAttribute('data-edit')) r = x; });
      if (r) openForm(r);
      return;
    }
    if ((g = t.getAttribute('data-del'))) { delRecord(g); return; }
    if ((g = t.getAttribute('data-act'))) { doAction(g, t.getAttribute('data-id'), t.getAttribute('data-to')); return; }
  });
  document.addEventListener('change', function (e) {
    var el = e.target;
    if (el.getAttribute && el.getAttribute('data-filter') !== null && el.getAttribute('data-filter')) {
      state.filter[el.getAttribute('data-filter')] = el.value; refreshAll(); return;
    }
    if (el.getAttribute && el.getAttribute('data-wt') !== null && el.getAttribute('data-wt') !== undefined) {
      refreshAll(); return;
    }
  });
  document.addEventListener('input', function (e) {
    var el = e.target;
    var f = el.getAttribute && el.getAttribute('data-f');
    if (f) { formVals[f] = el.value; clearTimeout(draftTimer); draftTimer = setTimeout(saveDraft, 300); return; }
    if (el.id === 'qProduct') { state.query = el.value; clearTimeout(el._t); el._t = setTimeout(refreshAll, 170); return; }
    var wi = el.getAttribute && el.getAttribute('data-wt');
    if (wi !== null && wi !== undefined) {
      var arr = getWeights(); arr[Number(wi)] = Number(el.value); setWeights(arr);
      var out = el.parentNode.querySelector('.wt-out');
      if (out) out.textContent = el.value;
      updateWtSum(); return;
    }
  });
  $('#btnNew').addEventListener('click', function () { openForm(null); });
  $('#btnRefresh').addEventListener('click', function () { loadAll().then(function () { refreshAll(); toast('已刷新'); }); });
  $('#btnSettings').addEventListener('click', function () { openDrawer('#setDrawer'); });
  $('#btnImport').addEventListener('click', function () { impRows = null; $('#impDo').textContent = '识别并导入'; openDrawer('#impDrawer'); });
  $('#impClose').addEventListener('click', closeDrawers);
  $('#impCancel').addEventListener('click', closeDrawers);
  $('#impDo').addEventListener('click', function () { if (impRows) doWriteImport(); else doParseImport(); });
  $('#mask').addEventListener('click', closeDrawers);
  $('#formClose').addEventListener('click', closeDrawers);
  $('#formCancel').addEventListener('click', closeDrawers);
  $('#setClose').addEventListener('click', closeDrawers);
  $('#formSave').addEventListener('click', saveForm);
  $('#btnExport').addEventListener('click', exportJson);
  $('#btnExportCsv').addEventListener('click', exportCsv);
  $('#btnImportJson').addEventListener('click', function () { $('#fileImportJson').click(); });
  $('#fileImportJson').addEventListener('change', function (e) {
    var f = e.target.files && e.target.files[0];
    if (!f) return;
    var fr = new FileReader();
    fr.onload = function () { importJson(String(fr.result)); };
    fr.onerror = function () { toast('读取文件失败'); };
    fr.readAsText(f);
    e.target.value = '';
  });
  $('#btnClearDemo').addEventListener('click', clearDemo);
  $('#btnClearAll').addEventListener('click', clearAll);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDrawers(); });
}

/* ---------- 14. 变更订阅（整页只注册一次） ---------- */
function subscribeUpdates() {
  if (!db || typeof db.onUpdated !== 'function') return;
  var timer = null;
  db.onUpdated(function (payload) {
    var ids = (payload && payload.databaseIds) || [];
    if (ids.indexOf(DB.product.databaseId) === -1) return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () { timer = null; loadOne().then(refreshAll); }, 400);
  });
}

/* ---------- 15. 示例数据（首次打开不空） ---------- */
function seedRecords() {
  var t = todayStr();
  var d1 = new Date(Date.now() - 26 * 86400000);
  var d2 = new Date(Date.now() - 58 * 86400000);
  var d3 = new Date(Date.now() - 120 * 86400000);
  var d4 = new Date(Date.now() - 40 * 86400000);
  function ds(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  return [
    { '商品名称': '【示例】韩系屏障修护身体冷霜 50g', '品牌': 'K-Barrier', '品类': '身体', '细分品类': '身体冷霜',
      '价格': 199, '上市日期': ds(d1), '数据来源': 'FastMoss', '所属市场': '韩国', '销量': 42000, '销售额': 8360000,
      '环比增速': 62, '关联达人数': 8, '退货率': 4.2, '榜单排名': 'TikTok 韩国个护第 7',
      '核心功效成分': '神经酰胺、角鲨烷', '剂型': '霜', '概念标签': '屏障修护', '质地描述': '冷霜质地、抹开即化',
      '功效宣称': '屏障修护', '技术壁垒': '配方工艺', '评分': 4.7, '评价数': 3100,
      '差评关键词': '味道偏浓', '备案路径': '进口备案', '宣称支撑难度': '需文献资料',
      '与我方价格带匹配': '匹配', '与我方客群匹配': '匹配', '与我方 SKU 重合度': '部分重合', '决策状态': '待评',
      '选品笔记': '示例：增速很猛但达人只有 8 个，说明还没被推爆，窗口期就在这里。对照自家身体冷霜的质地表达。' },
    { '商品名称': '【示例】日系以油养肤面部精华油 30ml', '品牌': 'Y-Squalane', '品类': '护肤', '细分品类': '面部精华油',
      '价格': 328, '上市日期': ds(d2), '数据来源': '抖音罗盘', '所属市场': '日本', '销量': 18600, '销售额': 6100800,
      '环比增速': 118, '关联达人数': 3, '退货率': 2.8, '榜单排名': '抖音面部精华第 3',
      '核心功效成分': '角鲨烷、霍霍巴油', '剂型': '油', '概念标签': '以油养肤', '质地描述': '轻薄不闷、上脸即吸',
      '功效宣称': '滋润修护', '技术壁垒': '独家原料', '评分': 4.8, '评价数': 5400,
      '差评关键词': '泵头不好按', '备案路径': '普通化妆品备案', '宣称支撑难度': '无需评价', '预估成本': 58,
      '与我方价格带匹配': '匹配', '与我方客群匹配': '匹配', '与我方 SKU 重合度': '全新', '决策状态': '待评',
      '选品笔记': '示例：全新品类、独家原料、备案最省事，三个条件都占。差评只指向包装，不指向配方。' },
    { '商品名称': '【示例】欧美视黄醇晚霜 50ml', '品牌': 'R-Retinol', '品类': '护肤', '细分品类': '面霜',
      '价格': 620, '上市日期': ds(d4), '数据来源': 'FastMoss', '所属市场': '欧美', '销量': 9200, '销售额': 5704000,
      '环比增速': 34, '关联达人数': 26, '退货率': 9.1, '榜单排名': 'Amazon 面霜第 21',
      '核心功效成分': '视黄醇、胜肽', '剂型': '霜', '概念标签': '早C晚A', '质地描述': '厚重但好推',
      '功效宣称': '抗皱', '技术壁垒': '专利技术', '评分': 4.4, '评价数': 1800,
      '差评关键词': '闷痘、搓泥', '备案路径': '特殊化妆品注册', '宣称支撑难度': '需人体功效试验',
      '与我方价格带匹配': '偏高', '与我方客群匹配': '匹配', '与我方 SKU 重合度': '全新', '决策状态': '待评',
      '选品笔记': '示例：概念和壁垒都不错，卡在备案——特殊注册要做人体功效试验，周期和费用都要算进去。' },
    { '商品名称': '【示例】国货冻纹修色眼油 15ml', '品牌': '某国货', '品类': '彩妆', '细分品类': '眼油',
      '价格': 89, '上市日期': ds(d3), '数据来源': '蝉妈妈', '所属市场': '中国', '销量': 156000, '销售额': 13884000,
      '环比增速': -12, '关联达人数': 240, '退货率': 19.5, '榜单排名': '抖音眼部彩妆第 2',
      '核心功效成分': '色粉、油脂', '剂型': '油', '概念标签': '冻纹修色', '质地描述': '偏油润',
      '功效宣称': '遮盖细纹', '技术壁垒': '无壁垒', '评分': 3.9, '评价数': 21000,
      '差评关键词': '卡纹、半天就花', '备案路径': '普通化妆品备案', '宣称支撑难度': '需人体功效试验',
      '与我方价格带匹配': '偏低', '与我方客群匹配': '需教育', '与我方 SKU 重合度': '高度重合', '决策状态': '待评',
      '选品笔记': '示例：销量很大但在跌，240 个达人在推说明已经很挤，退货率接近 20%——是反面教材，留着对照。' }
  ];
}
function seedLocalIfEmpty() {
  var all = lsRead();
  if ((all.product || []).length) return;
  all.product = seedRecords().map(function (r) { r._id = uid(); return r; });
  lsWrite(all);
}

/* ---------- 16. 初始化（固定顺序：读数据 → 绑事件 → 订阅 → 渲染） ---------- */
function init() {
  if (!ONLINE) {
    seedLocalIfEmpty();
    $('#offBanner').classList.remove('hide');
  }
  $('#setWhere').textContent = ONLINE
    ? '新品库存放在 WorkBuddy 资料库，云端存储、多设备自动同步。'
    : '数据只存在这台设备的浏览器里（离线模式），建议定期导出备份。';
  state.view = 'product';
  bindEvents();
  subscribeUpdates();
  refreshAll();
  loadAll().then(refreshAll);
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
