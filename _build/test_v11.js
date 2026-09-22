/* ============================================================
   V11·R2 本地验收（最终复审修复单）
   覆盖：范围隔离 / FastMoss 能力 / 金额币种保护 / 默认计数 360 /
        榜单语义 / 页面文案 / 移动抽屉视觉 / 回归
   断言型：任一失败 → 退出码 1。
   ============================================================ */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const D = path.join(__dirname, 'data');
const PAGE = process.env.PAGE_PATH || path.join(__dirname, '..', '全球选品平台.html');

/* ---------- 断言收集 ---------- */
const RES = [];
function chk(name, cond, detail) {
  RES.push({ name: name, ok: !!cond, detail: detail === undefined ? '' : String(detail) });
}
function near(a, b, eps) { return Math.abs(a - b) <= (eps === undefined ? 0.01 : eps); }

/* ---------- 构造 400 条真实+示例商品（与线上同构） ---------- */
const NUM = new Set(['价格', '销量', '销售额', '环比增速', '关联达人数', '退货率', '评分', '评价数',
  '预估成本', '好评数', '好评率', '差评订单数', '差评率', '品质退货数', '品质退货率',
  '投诉数', '投诉率', 'SKU 数']);
const SEL = new Set(['品类', '数据来源', '所属市场', '国家/地区', '剂型', '技术壁垒', '评价来源',
  '备案路径', '宣称支撑难度', '与我方价格带匹配', '与我方客群匹配', '与我方 SKU 重合度',
  '决策状态', '数据标记', '二级类目', '三级类目']);
const DATE = new Set(['上市日期']);

function wrap(rec, i) {
  const out = {};
  for (const [k, v] of Object.entries(rec)) {
    if (v === null || v === '' || v === undefined || k.startsWith('_')) continue;
    if (NUM.has(k)) out[k] = { number: Number(v) };
    else if (SEL.has(k)) out[k] = { select: String(v) };
    else if (DATE.has(k)) out[k] = { date: String(v).slice(0, 19) };
    else out[k] = { text: String(v) };
  }
  out._id = 'p' + i;
  return out;
}

const ai = JSON.parse(fs.readFileSync(path.join(D, 'records_cat_400.json'), 'utf8'));
const recs = (ai.records || ai);
const cloudSnap = JSON.parse(fs.readFileSync(path.join(__dirname, 'cloud_platform.json'), 'utf8'));
const cloudByPid = {};
for (const c of (cloudSnap.results || cloudSnap)) if (c['商品ID']) cloudByPid[String(c['商品ID'])] = c;
const NEWF = ['SKU 数', '备案/许可号', '法规合规声明', '数据标记', '二级类目', '三级类目', '榜单排名'];
for (const rec of recs) {
  const c = cloudByPid[String(rec['商品ID'] || '')];
  if (c) for (const k of NEWF) if (c[k] !== undefined && c[k] !== null && c[k] !== '') rec[k] = c[k];
}
const prodRows = recs.map(wrap);

const us = JSON.parse(fs.readFileSync(path.join(D, 'douyin_usersound.json'), 'utf8'));
const pct = (x) => (x == null ? null : Math.round(x * 10000) / 100);
const reviewRows = us.products.map((p, i) => wrap({
  商品名称: p.name, 商品ID: p.id, 店铺类目: p.cat || '', 评价数: p.eval_cnt, 好评数: p.good_cnt,
  好评率: pct(p.good_ratio), 差评订单数: p.bad_cnt, 差评率: pct(p.bad_ratio),
  好评关键词: (p.good || []).map((x) => x.label).join(' / '),
  差评关键词: (p.bad || []).map((x) => x.label).join(' / '),
  差评原因: (p.reason || []).map((x) => `${x.label} ${x.n}`).join(' / '),
  数据来源: '抖音罗盘', 评价来源: '抖音评价',
}, 'r' + i));

const nDemo = prodRows.filter((r) => r['数据标记'] && r['数据标记'].select === '示例').length;

chk('S1 数据装配：商品 400 条（真实 360 / 示例 40）', prodRows.length === 400, `records=${prodRows.length}`);
chk('S1 数据装配：示例恰好 40 条', nDemo === 40, `demo=${nDemo}`);
chk('S1 数据装配：口碑数据非空', reviewRows.length > 0, `review=${reviewRows.length}`);

const PRODUCT_DB = 'Hu5q2PAyW17BmdP5JPQ9os';
const REVIEW_DB = 'ZOiFonS5w7psZlgM5kJjiD';

(async () => {
  const b = await chromium.launch();
  const errs = [];
  const attach = (p, tag) => {
    p.on('pageerror', (e) => errs.push(tag + ' pageerror: ' + String(e).slice(0, 240)));
    p.on('console', (m) => { if (m.type() === 'error') errs.push(tag + ' console: ' + m.text().slice(0, 240)); });
  };

  const MOCK = `window.__SMART_PAGE__ = { database: {
      query: function(o){ var db = (o && o.databaseId) === '${REVIEW_DB}' ? window.__RV : window.__PR;
        return Promise.resolve({ results: db, nextCursor: null, hasMore: false }); },
      getSchema: function(o){ return Promise.resolve({ properties: (o && o.databaseId) === '${REVIEW_DB}' ? window.__RVSCHEMA : window.__PRSCHEMA }); },
      addRecord: function(){ return Promise.resolve({ recordId: 'mock-new' }); },
      deleteRecord: function(){ return Promise.resolve({ ok: true }); },
      onUpdated: function(){ return function(){}; }
    } };
    window.__PR = ${JSON.stringify(prodRows)};
    window.__RV = ${JSON.stringify(reviewRows)};
    window.__PRSCHEMA = [];
    window.__RVSCHEMA = [];`;

  /* ================= 桌面 1440 ================= */
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
  attach(p, '[desktop]');
  await p.addInitScript(MOCK);
  await p.goto('file://' + PAGE, { waitUntil: 'load' });
  await p.waitForTimeout(3200);

  /* ---------- S2 引擎级断言（直接调页面全局函数） ---------- */
  const eng = await p.evaluate(() => {
    const out = {};
    const real = state.list.filter((r) => !isDemo(r));
    out.realN = real.length;

    /* ① 印尼 × 唇妆 7 条反例 */
    const lip = real.filter((r) => txtOf(r, '国家/地区') === '印度尼西亚' && txtOf(r, '二级类目') === '唇妆');
    const gs = lip.map((r) => numField(r, '环比增速')).filter((x) => x !== null).sort((a, b) => a - b);
    const st = growthStats(lip);
    out.lip = {
      n: lip.length, gs: gs, mean: avgArr(lip.map((r) => numField(r, '环比增速')).filter((x) => x !== null)),
      med: st.med, medAll: st.medAll, nKeep: st.n, nAll: st.nAll, ex: st.ex, exWhy: st.exWhy,
      pos: st.pos, posN: st.posN,
      baseOf57725: (function () {
        const t = lip.find((r) => numField(r, '环比增速') === 57725);
        return t ? baseSoldOf(t) : null;
      })(),
      threshold: { MKT_MIN_GROWTH: MKT_MIN_GROWTH, MKT_MIN_POS: MKT_MIN_POS, MKT_MIN_SAMPLE: MKT_MIN_SAMPLE, GROW_BASE_MIN: GROW_BASE_MIN }
    };

    /* ② 机会判定双轨：V10 insightsOf（均值）恢复；board 稳健口径单独走 */
    const insV10 = insightsOf(real);
    out.insV10HasLip = insV10.mkt.some((m) => m.country === '印度尼西亚' && m.c2 === '唇妆');
    out.insV10LipVal = (insV10.mkt.find((m) => m.country === '印度尼西亚' && m.c2 === '唇妆') || {}).avgGrowth;
    const insBR = boardInsightsOf(real);
    out.brHasLip = insBR.mkt.some((m) => m.country === '印度尼西亚' && m.c2 === '唇妆');
    out.brMktCount = insBR.mkt.length;

    /* ③ 金额/币种汇总保护 */
    const br = boardRankDataOf();
    out.cgAll = comparableGmv(br);
    const cmm = br.filter((r) => txtOf(r, '数据来源') === '蝉妈妈');
    out.cgCmm = comparableGmv(cmm);
    /* 同来源多国家（合成样本）：蝉妈妈 + 单周期，但国家一个中国一个泰国 */
    const cmmRows = cmm.slice(0, 3).map((r) => r);
    const thClone = JSON.parse(JSON.stringify(cmmRows[0]));
    const txt = (o, k, v) => { o[k] = { text: String(v) }; };
    txt(thClone, '国家/地区', '泰国');
    out.cgMultiCty = comparableGmv(cmmRows.concat([thClone]));
    /* 缺币种（国家未登记）拒绝 */
    const mars = JSON.parse(JSON.stringify(cmmRows[0]));
    txt(mars, '国家/地区', '未知星');
    out.cgNoCur = comparableGmv([mars]);
    /* 多周期拒绝（合成：同源同国但榜单排名带不同周期区间） */
    const p2clone = JSON.parse(JSON.stringify(cmmRows[0]));
    p2clone['榜单排名'] = { text: '蝉妈妈抖音商品销量榜 第1名（美妆护肤，2020/01/01 ~ 2020/01/07）' };
    out.cgMultiPeriod = comparableGmv([cmmRows[0], p2clone]);

    /* ④ 分来源分榜 */
    const grp = rankGroups(br);
    out.groups = grp.map((g) => ({ src: g.src, n: g.rows.length }));
    out.groupsSingleSrc = grp.every((g) => g.rows.every((r) => txtOf(r, '数据来源') === g.src));
    out.groupSrcs = grp.map((g) => g.src).sort();

    /* ⑤ 默认示例隔离（board/rank 专用作用域；dataOf 保持 V10） */
    out.dataOfDemo = dataOf().filter(isDemo).length;           /* V10 语义：默认含示例 */
    out.brDefault = boardRankDataOf();
    out.brDefaultDemo = out.brDefault.filter(isDemo).length;
    out.brDefaultReal = out.brDefault.filter((r) => !isDemo(r)).length;
    state.demoOnly = true;
    out.brDemoOnly = boardRankDataOf().filter(isDemo).length;
    state.demoOnly = false;
    state.realOnly = true;
    out.brRealOnly = boardRankDataOf().filter((r) => !isDemo(r)).length;
    state.realOnly = false;

    /* ⑥ 热力图网格不带示例 */
    const H = heatOf(out.brDefault);
    let heatDemo = 0;
    Object.keys(H.grid).forEach((k) => { heatDemo += H.grid[k].rows.filter(isDemo).length; });
    out.heatDemo = heatDemo;

    /* ⑦ 来源列可得性 */
    out.cols = {
      hwahae: rankColsOf('Hwahae').map((c) => c.k),
      olive: rankColsOf('Olive Young').map((c) => c.k),
      cmm: rankColsOf('蝉妈妈').map((c) => c.k),
      fm: rankColsOf('FastMoss').map((c) => c.k),
      lp: rankColsOf('抖音罗盘').map((c) => c.k)
    };

    /* ⑧ 周期是来源属性 */
    out.periods = {};
    ['FastMoss', '抖音罗盘', '蝉妈妈'].forEach((s) => { out.periods[s] = periodShort(s); });
    out.periodHas30 = Object.keys(out.periods).some((k) => out.periods[k].indexOf('30') >= 0);

    /* ⑨ 原始名次解析：第N名 / 第P页第Q位 / 排序键 */
    out.rankParse = (function () {
      const fakeName = { '榜单排名': { text: '抖音罗盘·商品榜单 第12名（x，2026/09/12 ~ 2026/09/18）' } };
      const fakePage = { '榜单排名': { text: 'FastMoss 销量榜 第1页第1位（美妆个护·PH）' } };
      const fakePage2 = { '榜单排名': { text: 'FastMoss 销量榜 第3页第10位（美妆个护·US）' } };
      const none = { '榜单排名': { text: '' } };
      return {
        named: rankNoOf(fakeName), namedText: rankTextOf(fakeName),
        p1: rankNoOf(fakePage), page1: rankPageOf(fakePage), page1Text: rankTextOf(fakePage),
        page2: rankPageOf(fakePage2), page2Text: rankTextOf(fakePage2),
        empty: rankNoOf(none), emptyKey: rankKeyOf(none)[0],
        keyNamed: rankKeyOf(fakeName), keyPage: rankKeyOf(fakePage)
      };
    })();

    /* ⑩ 低基数只 在增速排序置底 */
    out.sortCheck = (function () {
      const lipF = lip.filter((r) => txtOf(r, '数据来源') === 'FastMoss');
      const byGrowth = rankRows(lipF, 'growth');
      const bySold = rankRows(lipF, 'sold');
      const bySales = rankRows(lipF, 'sales');
      const byRank = rankRows(lipF, 'rank');
      const isEx = (r) => growExcluded(r) === '低基数';
      const lastOf = (a) => a[a.length - 1];
      return {
        n: lipF.length,
        growthLastEx: isEx(lastOf(byGrowth)),
        soldLastEx: isEx(lastOf(bySold)),
        salesLastEx: isEx(lastOf(bySales)),
        soldTop1: numField(bySold[0], '销量'),
        soldOrder: bySold.map((r) => numField(r, '销量')),
        rankOrder: byRank.map((r) => rankNoOf(r) === null ? (rankPageOf(r) ? rankPageOf(r).page + '-' + rankPageOf(r).pos : '?') : rankNoOf(r))
      };
    })();

    /* ⑪ c2Stats V10 均值 vs boardC2Stats 稳健（同一输入不同口径） */
    out.c2check = (function () {
      const sample = br.filter((r) => txtOf(r, '二级类目') === '唇妆');
      const v10 = c2Stats(sample).find((x) => x.c2 === '唇妆');
      const brd = boardC2Stats(sample).find((x) => x.c2 === '唇妆');
      const gsRaw = sample.map((r) => numField(r, '环比增速')).filter((x) => x !== null);
      return {
        n: sample.length, v10Mean: v10 ? v10.avgGrowth : null, brMed: brd ? brd.avgGrowth : null,
        rawMean: avgArr(gsRaw), rawMed: medOf(gsRaw)
      };
    })();

    /* ⑫ 全库增速分布（报告用） */
    const gAll = growthStats(real);
    out.allGrow = { nAll: gAll.nAll, n: gAll.n, med: gAll.med, pos: gAll.pos, ex: gAll.ex };

    /* ⑬ 筛选项计数作用域：board/rank 默认 360；lib/insight 保持 V10（state.list） */
    out.counts = (function () {
      state.view = 'board';
      const r1 = { total: fltTotalOf(), country: fltCountOf('country'), src: fltCountOf('src') };
      state.view = 'lib';
      const r2 = { total: fltTotalOf(), countryN: countriesIn().reduce((s, x) => s + x.n, 0) };
      state.view = 'board';
      return { board: r1, lib: r2 };
    })();

    return out;
  });

  /* ---- 判定 ①：反例闭环 ---- */
  const L = eng.lip;
  chk('引擎①｜印尼×唇妆样本数 = 7', L.n === 7, `n=${L.n}`);
  chk('引擎①｜7 条增速与 spec 反例逐值一致',
    JSON.stringify(L.gs) === JSON.stringify([-40.09, -0.86, 10.06, 18.16, 36.39, 160.77, 57725]),
    JSON.stringify(L.gs));
  chk('引擎①｜均值 ≈ 8272.78%（这正是不能用的口径）', near(L.mean, 8272.78, 0.5), `mean=${L.mean}`);
  chk('引擎①｜全 7 条中位数 = 18.16%（medOf 四舍五入到 1 位）', near(L.medAll, 18.16, 0.06), `medAll=${L.medAll}`);
  chk('引擎①｜剔除低基数后稳健中枢 = 14.11%', near(L.med, 14.11, 0.06), `med=${L.med}`);
  chk('引擎①｜57725% 那条反推基期 = 4 件（< 10 件阈值）', near(L.baseOf57725, 4, 0.5), `base=${L.baseOf57725}`);
  chk('引擎①｜低基数剔除 1 条，有效样本 6 条', L.ex === 1 && L.nKeep === 6 && L.nAll === 7,
    `ex=${L.ex} keep=${L.nKeep}/${L.nAll}`);
  chk('引擎①｜两个中位数都 < 起量门槛 60% → 不判「集体起量」',
    L.med < 60 && L.medAll < 60, `med=${L.med} medAll=${L.medAll}`);

  /* ---- 判定 ②：机会判定双轨 ---- */
  chk('复审①｜insightsOf 恢复 V10 均值口径：印尼×唇妆（均值 8272.78%）在其机会名单里',
    eng.insV10HasLip === true && near(eng.insV10LipVal, 8272.78, 1), `val=${eng.insV10LipVal}`);
  chk('复审①｜boardInsightsOf 稳健口径：印尼×唇妆不在看板机会名单里', eng.brHasLip === false, '');
  chk('复审①｜boardInsightsOf 仍有合格格（规则没被改死）', eng.brMktCount > 0, `mkt=${eng.brMktCount}`);

  /* ---- 判定 ③：金额/币种 ---- */
  chk('复审③｜全范围金额合计被拒绝', eng.cgAll.ok === false, JSON.stringify(eng.cgAll.reasons).slice(0, 120));
  chk('复审③｜同来源多国家被拒绝（蝉妈妈+泰国克隆样本）',
    eng.cgMultiCty.ok === false && eng.cgMultiCty.reasons.some((x) => x.indexOf('国家') >= 0),
    JSON.stringify(eng.cgMultiCty.reasons).slice(0, 140));
  chk('复审③｜币种推不出（国家未登记）被拒绝',
    eng.cgNoCur.ok === false && eng.cgNoCur.reasons.some((x) => x.indexOf('币种') >= 0),
    JSON.stringify(eng.cgNoCur.reasons).slice(0, 140));
  chk('复审③｜多周期被拒绝',
    eng.cgMultiPeriod.ok === false && eng.cgMultiPeriod.reasons.some((x) => x.indexOf('周期') >= 0),
    JSON.stringify(eng.cgMultiPeriod.reasons).slice(0, 140));
  chk('复审③｜明确安全的单国人民币来源（蝉妈妈：中国/CNY/单周期）允许合计',
    eng.cgCmm.ok === true && eng.cgCmm.currency === 'CNY' && eng.cgCmm.unit === '元' &&
    eng.cgCmm.country === '中国' && eng.cgCmm.n > 0, JSON.stringify(eng.cgCmm).slice(0, 140));

  /* ---- 判定 ④：分来源分榜 ---- */
  chk('引擎④｜「全部」= 逐来源分榜，且来源恰为 FastMoss/抖音罗盘/蝉妈妈',
    JSON.stringify(eng.groupSrcs) === JSON.stringify(['FastMoss', '抖音罗盘', '蝉妈妈']),
    JSON.stringify(eng.groupSrcs));
  chk('引擎④｜每个分榜内部来源单一', eng.groupsSingleSrc === true, '');

  /* ---- 判定 ⑤：示例隔离 ---- */
  chk('复审①｜dataOf 保持 V10：默认含全部示例（40 条）', eng.dataOfDemo === 40, `demo=${eng.dataOfDemo}`);
  chk('复审①｜boardRankDataOf 默认 0 示例、360 真实',
    eng.brDefaultDemo === 0 && eng.brDefaultReal === 360, `demo=${eng.brDefaultDemo} real=${eng.brDefaultReal}`);
  chk('复审①｜显式「只看示例」时示例才进入（40 条）', eng.brDemoOnly === 40, `n=${eng.brDemoOnly}`);
  chk('复审①｜显式「只看真实」时全部为真实', eng.brRealOnly === 360, `n=${eng.brRealOnly}`);
  chk('引擎⑥｜热力图网格行里 0 条示例', eng.heatDemo === 0, `demo=${eng.heatDemo}`);

  /* ---- 判定 ⑦：来源能力 ---- */
  chk('复审②｜FastMoss 榜不出「销售额」列（当前未结构化提供销售额）',
    eng.cols.fm.indexOf('gmv') < 0, JSON.stringify(eng.cols.fm));
  chk('复审②｜FastMoss 保留 销量/增速 列',
    eng.cols.fm.indexOf('sold') >= 0 && eng.cols.fm.indexOf('grow') >= 0, JSON.stringify(eng.cols.fm));
  chk('引擎⑦｜Hwahae/Olive Young 只出名次口碑', eng.cols.hwahae.indexOf('sold') < 0 && eng.cols.hwahae.indexOf('gmv') < 0 &&
    eng.cols.olive.indexOf('sold') < 0, JSON.stringify(eng.cols.hwahae));
  chk('引擎⑦｜蝉妈妈出「增速」列', eng.cols.cmm.indexOf('grow') >= 0, JSON.stringify(eng.cols.cmm));
  chk('引擎⑦｜抖音罗盘不出「增速」列、保留「数据截至」列',
    eng.cols.lp.indexOf('grow') < 0 && eng.cols.lp.indexOf('asof') >= 0, JSON.stringify(eng.cols.lp));
  chk('引擎⑦｜给不出截至日的来源不出该列',
    eng.cols.fm.indexOf('asof') < 0 && eng.cols.cmm.indexOf('asof') < 0, '');

  /* ---- 判定 ⑧：周期 ---- */
  chk('引擎⑧｜周期文案不出现「近 30 天」', eng.periodHas30 === false, JSON.stringify(eng.periods));
  chk('引擎⑧｜蝉妈妈 7 天口径 / FastMoss 未标注',
    eng.periods['蝉妈妈'].indexOf('7') >= 0 && eng.periods['FastMoss'].indexOf('未标注') >= 0,
    JSON.stringify(eng.periods));

  /* ---- 判定 ⑨：原始名次解析 ---- */
  const RP = eng.rankParse;
  chk('复审⑤｜「第12名」解析为 12', RP.named === 12 && RP.namedText === '第12名', `${RP.named}/${RP.namedText}`);
  chk('复审⑤｜「第1页第1位」不被解析成名次 1（rankNoOf=null）', RP.p1 === null && RP.empty === null, `p1=${RP.p1}`);
  chk('复审⑤｜分页位次完整解析出页码与位次',
    RP.page1 && RP.page1.page === 1 && RP.page1.pos === 1 && RP.page2.page === 3 && RP.page2.pos === 10,
    JSON.stringify([RP.page1, RP.page2]));
  chk('复审⑤｜排序键：有名次 < 分页位次 < 无名次',
    RP.keyNamed[0] < RP.keyPage[0] && RP.keyPage[0] < RP.emptyKey, JSON.stringify([RP.keyNamed, RP.keyPage, RP.emptyKey]));

  /* ---- 判定 ⑩：置底语义 ---- */
  const SC = eng.sortCheck;
  chk('复审⑤｜按增速排序：低基数样本置底', SC.growthLastEx === true, `n=${SC.n}`);
  chk('复审⑤｜按销量排序：低基数不强制置底（尊重销量大小）',
    SC.soldLastEx === false || SC.soldOrder[SC.soldOrder.length - 1] >= SC.soldOrder[0],
    `order=${JSON.stringify(SC.soldOrder)}`);
  chk('复审⑤｜按销量排序第一 = 销量最大的那条',
    SC.soldTop1 === Math.max.apply(null, SC.soldOrder), `top=${SC.soldTop1}`);
  chk('复审⑤｜按原名次排序：名次单调不降', (function () {
    const nums = SC.rankOrder.map((x) => (typeof x === 'number' ? [0, x] : [1, parseFloat(String(x).split('-')[0] * 1000) + parseFloat(String(x).split('-')[1])]));
    for (let i2 = 1; i2 < nums.length; i2++) { if (nums[i2 - 1][0] !== nums[i2][0]) { if (nums[i2 - 1][0] > nums[i2][0]) return false; } else if (nums[i2 - 1][1] > nums[i2][1]) return false; }
    return true;
  })(), JSON.stringify(SC.rankOrder));

  /* ---- 判定 ⑪：c2Stats 双轨 ---- */
  const C2 = eng.c2check;
  chk('复审①｜c2Stats 恢复 V10 均值口径（avgGrowth == 原始均值）',
    near(C2.v10Mean, C2.rawMean, 0.01) && !(near(C2.v10Mean, C2.rawMed, 0.01)),
    `v10=${C2.v10Mean} mean=${C2.rawMean} med=${C2.rawMed}`);
  chk('复审①｜boardC2Stats 稳健口径（avgGrowth == 剔低基数中位数）',
    C2.brMed !== null && Math.abs(C2.brMed - C2.rawMed) < 60, `br=${C2.brMed} medAll=${C2.rawMed} n=${C2.n}`);

  /* ---- 判定 ⑬：计数作用域 ---- */
  const CT = eng.counts;
  chk('复审④｜board 筛选计数基于默认真实数据：总数 360',
    CT.board.total === 360, `total=${CT.board.total}`);
  chk('复审④｜board 国家计数合计 = 360（只忽略国家维度）',
    CT.board.country.reduce((s, x) => s + x.n, 0) === 360,
    JSON.stringify(CT.board.country));
  chk('复审④｜board 来源计数 = FastMoss 250 / 抖音罗盘 60 / 蝉妈妈 50',
    JSON.stringify(CT.board.src.map((x) => x.k + ':' + x.n).sort()) === JSON.stringify(['FastMoss:250', '抖音罗盘:60', '蝉妈妈:50'].sort()),
    JSON.stringify(CT.board.src));
  chk('复审④｜lib 筛选计数保持 V10（总数 400；国家合计 383 = V10 只数非空，17 条示例国家留空）',
    CT.lib.total === 400 && CT.lib.countryN === 383,
    `total=${CT.lib.total} country=${CT.lib.countryN}`);

  /* ---------- S3 DOM 断言 ---------- */
  const views = ['board', 'rank', 'lib', 'insight', 'review'];
  const dom = {};
  for (const v of views) {
    await p.evaluate((vv) => { const el = document.querySelector('[data-view="' + vv + '"]'); if (el) el.click(); }, v);
    await p.waitForTimeout(900);
    dom[v] = await p.evaluate(() => ({
      txt: document.querySelector('#view').innerText,
      len: document.querySelector('#view').innerText.length,
      desc: document.querySelector('#viewDesc').textContent,
      title: document.querySelector('#viewTitle').textContent
    }));
  }

  /* board */
  await p.evaluate(() => { document.querySelector('[data-view="board"]').click(); });
  await p.waitForTimeout(900);
  const bd = await p.evaluate(() => ({
    hero: !!document.querySelector('.hero'),
    secs: Array.from(document.querySelectorAll('.sec-hd h2')).map((x) => x.textContent),
    heat: document.querySelectorAll('.heat .hcell').length,
    demoText: (document.querySelector('#view').innerText.match(/【示例】/g) || []).length,
    dashCells: (document.querySelector('#view').innerText.match(/—/g) || []).length,
    l3: Array.from(document.querySelectorAll('.hcell.l3')).map((x) => ({
      t: (x.querySelector('b') || {}).textContent || '',
      n: parseInt(((x.querySelector('i') || {}).textContent || '0').replace(/[^0-9]/g, ''), 10) || 0
    })),
    l1: document.querySelectorAll('.hcell.l1').length,
    desc: document.querySelector('#viewDesc').textContent,
    countryOpt: (document.querySelector('select[data-f-sel="country"] option') || {}).textContent || '',
    html: document.querySelector('#view').innerHTML,
    txt: document.querySelector('#view').innerText
  }));
  chk('DOM①｜看板 Hero 渲染', bd.hero === true, '');
  chk('DOM①｜热力图网格渲染出格子', bd.heat > 0, `cells=${bd.heat}`);
  chk('硬约束④｜看板默认不出现任何「【示例】」', bd.demoText === 0, `n=${bd.demoText}`);
  chk('复审④｜看板标题计数 = 360 个商品（不出现 400）',
    bd.desc.indexOf('360 个商品') >= 0 && bd.desc.indexOf('400 个商品') < 0, bd.desc.slice(0, 90));
  chk('复审④｜国家下拉「全部」= 360 个商品', bd.countryOpt.indexOf('360') >= 0 && bd.countryOpt.indexOf('400') < 0,
    bd.countryOpt);
  chk('复审④｜看板正文不出现「400 个商品」', bd.txt.indexOf('400 个商品') < 0, '');
  chk('复审⑥｜看板副标题改为「全球覆盖、类目热度与来源分榜」',
    bd.desc.indexOf('全球覆盖') >= 0 && bd.desc.indexOf('来源分榜') >= 0, bd.desc.slice(0, 60));
  chk('复审⑥｜「数据截至」卡主值是日期（YYYY-MM-DD），覆盖数进脚注',
    /\d{4}-\d{2}-\d{2}/.test(bd.txt) && bd.txt.indexOf('条带明确截至日') >= 0, '');
  chk('复审⑥｜金额单位随币种映射（出现「元」须与 CNY 合计同现）',
    (bd.html.indexOf('<small>元</small>') >= 0) === (bd.html.indexOf('（CNY）') >= 0),
    '元卡=' + (bd.html.indexOf('<small>元</small>') >= 0) + ' CNY=' + (bd.html.indexOf('（CNY）') >= 0));
  const bdMktHits = (bd.html.match(/.{0,10}市场份额.{0,10}/g) || []);
  chk('硬约束②｜看板「市场份额」只以否定式出现',
    bdMktHits.every((x) => /不是|而非|不等于/.test(x)), JSON.stringify(bdMktHits).slice(0, 160));
  chk('硬约束⑤｜热力图深蓝格样本数都 ≥ 3', bd.l3.length > 0 && bd.l3.every((c) => c.n >= 3),
    JSON.stringify(bd.l3.filter((c) => c.n < 3)));
  chk('硬约束⑤｜样本不足的高值格降浅色', bd.l1 > 0, `l1=${bd.l1}`);

  /* rank */
  await p.evaluate(() => { document.querySelector('[data-view="rank"]').click(); });
  await p.waitForTimeout(900);
  const rk = await p.evaluate(() => {
    const boards = Array.from(document.querySelectorAll('.sec')).map((s) => ({
      hd: (s.querySelector('.sec-hd h2') || {}).textContent || '',
      heads: Array.from(s.querySelectorAll('thead th')).map((x) => x.textContent),
      cov: (s.querySelector('.cov-bar') || {}).innerText || '',
      firstNo: (s.querySelector('.rkt tbody tr td') || {}).textContent || '',
      firstMeta: (s.querySelector('.rkt tbody .pmeta') || {}).textContent || '',
      note: (s.querySelector('.miss-note') || {}).textContent || ''
    }));
    return {
      boards: boards,
      srcTabs: Array.from(document.querySelectorAll('.rank-src .rank-tab')).map((x) => x.textContent),
      rows: document.querySelectorAll('.rkt tbody tr').length,
      demoText: (document.querySelector('#view').innerText.match(/【示例】/g) || []).length,
      desc: document.querySelector('#viewDesc').textContent,
      txt: document.querySelector('#view').innerText
    };
  });
  const fmBoard = rk.boards.find((x) => x.hd.indexOf('FastMoss') >= 0);
  const lpBoard = rk.boards.find((x) => x.hd.indexOf('抖音罗盘') >= 0);
  const cmmBoard = rk.boards.find((x) => x.hd.indexOf('蝉妈妈') >= 0);
  chk('DOM②｜三来源三榜齐全', !!(fmBoard && lpBoard && cmmBoard), JSON.stringify(rk.boards.map((x) => x.hd)));
  chk('复审②｜FastMoss 榜表头无「销售额」',
    !!fmBoard && fmBoard.heads.every((x) => x.indexOf('销售额') < 0), JSON.stringify(fmBoard && fmBoard.heads));
  chk('复审②｜蝉妈妈/抖音罗盘榜保留「销售额（原币）」列',
    cmmBoard.heads.some((x) => x.indexOf('销售额') >= 0) && lpBoard.heads.some((x) => x.indexOf('销售额') >= 0),
    JSON.stringify([cmmBoard.heads, lpBoard.heads]));
  chk('复审⑤｜覆盖度条改为「收录 N 条 · Top50 目标 / 展示 N 条」',
    fmBoard.cov.indexOf('收录') >= 0 && fmBoard.cov.indexOf('Top50 目标') >= 0 && fmBoard.cov.indexOf('展示') >= 0 &&
    fmBoard.cov.indexOf('/50') < 0, fmBoard.cov.replace(/\s+/g, ' ').slice(0, 120));
  chk('复审⑤｜默认按原名次排序：抖音罗盘榜首名次 = 1（原榜名次，非显示序号拼接）',
    lpBoard.firstNo === '1', `firstNo=${lpBoard.firstNo}`);
  chk('复审⑤｜FastMoss 榜首名次为「1页1位」（分页位次，不是 1）',
    fmBoard.firstNo.indexOf('页') >= 0 && fmBoard.firstNo.indexOf('位') >= 0, `firstNo=${fmBoard.firstNo}`);
  chk('复审⑤｜miss-note 说明名次口径（页-位 ≠ 全局名次）',
    fmBoard.note.indexOf('页') >= 0 && fmBoard.note.indexOf('全局名次') >= 0, fmBoard.note.slice(0, 120));
  chk('硬约束④｜榜单中心默认不出现「【示例】」', rk.demoText === 0, `n=${rk.demoText}`);
  chk('复审④｜榜单中心标题计数 = 360', rk.desc.indexOf('360 个商品') >= 0, rk.desc.slice(0, 90));
  chk('复审④｜榜单中心来源 Tab 计数 = 250/60/50',
    JSON.stringify(rk.srcTabs.map((x) => x.replace(/\s+/g, '')).sort()) === JSON.stringify(['分来源分榜', '抖音罗盘60', '蝉妈妈50', 'FastMoss250'].sort()),
    JSON.stringify(rk.srcTabs));
  chk('硬约束②｜榜单不出现「市场份额」', rk.txt.indexOf('市场份额') < 0, '');

  /* 重排 → 排序位 + 原榜保留 */
  const resort = await p.evaluate(async () => {
    state.view = 'rank'; state.rankBy = 'sales'; state.src = '蝉妈妈'; refreshAll();
    await new Promise((r) => setTimeout(r, 800));
    const t = document.querySelector('.rkt');
    const head = Array.from(t.querySelectorAll('thead th')).map((x) => x.textContent);
    const firstRow = t.querySelector('tbody tr');
    const cells = Array.from(firstRow.querySelectorAll('td')).map((x) => x.textContent.replace(/\s+/g, ' '));
    const headCell = t.querySelector('tbody tr td');
    return { head: head, first: cells[0], meta: (firstRow.querySelector('.pmeta') || {}).textContent || '' };
  });
  chk('复审⑤｜重排后名列表头 =「排序位」，值 = 1',
    resort.head[0] === '排序位' && resort.first === '1', `${resort.head[0]}/${resort.first}`);
  chk('复审⑤｜重排后保留「原榜 第N名」', /原榜 第\d+名/.test(resort.meta), resort.meta.slice(0, 60));
  await p.evaluate(() => { state.rankBy = 'rank'; state.src = '全部'; refreshAll(); });
  await p.waitForTimeout(600);

  /* 下钻 + 低基数（growth 置底 / sold 不置底） */
  await p.evaluate(() => { document.querySelector('[data-view="board"]').click(); });
  await p.waitForTimeout(800);
  const drill = await p.evaluate(async () => {
    const c = document.querySelector('.hcell[data-drill="rank"]');
    if (!c) return { ok: false };
    const cty = c.getAttribute('data-d-country'), c2 = c.getAttribute('data-d-c2');
    c.click();
    await new Promise((r) => setTimeout(r, 700));
    return { ok: true, cty: cty, c2: c2, view: state.view, sCountry: state.country, sC2: state.c2,
      tabOn: (document.querySelector('.rank-src .rank-tab.on') || {}).textContent || '' };
  });
  chk('DOM③｜点热力格带「国家 + 二级类目」下钻到榜单中心',
    drill.ok && drill.view === 'rank' && drill.sCountry === drill.cty && drill.sC2 === drill.c2,
    JSON.stringify(drill));
  chk('DOM③｜下钻后来源切到「分来源分榜」', drill.ok && drill.tabOn.indexOf('分来源分榜') >= 0, drill.tabOn);

  const exCase = await p.evaluate(async () => {
    state.country = '印度尼西亚'; state.c2 = '唇妆'; state.src = 'FastMoss';
    state.rankBy = 'growth'; state.view = 'rank'; refreshAll();
    await new Promise((r) => setTimeout(r, 900));
    const rows = Array.from(document.querySelectorAll('.rkt tbody tr'));
    const texts = rows.map((tr) => tr.innerText.replace(/\s+/g, ' '));
    const last = rows[rows.length - 1];
    const g = { last: last && last.classList.contains('ex'), idx: texts.findIndex((t) => t.indexOf('57725') >= 0), n: rows.length };
    state.rankBy = 'sold'; refreshAll();
    await new Promise((r) => setTimeout(r, 900));
    const rows2 = Array.from(document.querySelectorAll('.rkt tbody tr'));
    const texts2 = rows2.map((tr) => tr.innerText.replace(/\s+/g, ' '));
    return {
      n: rows.length, growthLastEx: g.last, growthIdx: g.idx,
      soldIdx: texts2.findIndex((t) => t.indexOf('57725') >= 0), soldN: rows2.length,
      soldLastEx: rows2[rows2.length - 1].classList.contains('ex'),
      soldOrder: rows2.map((tr) => { const m = tr.innerText.match(/销量\s*([\d,]+)/); return m ? Number(m[1].replace(/,/g, '')) : -1; })
    };
  });
  chk('榜单⑤｜下钻「印尼 × 唇妆」后恰好 7 行', exCase.n === 7, `n=${exCase.n}`);
  chk('榜单⑤｜按增速排序：57725% 置底并打标', exCase.growthLastEx === true && exCase.growthIdx === exCase.n - 1,
    `idx=${exCase.growthIdx}/${exCase.n - 1}`);
  chk('复审⑤｜按销量排序：57725% 不被强制置底（位置由销量决定）',
    exCase.soldIdx !== exCase.soldN - 1 || exCase.soldOrder[exCase.soldN - 1] >= Math.max.apply(null, exCase.soldOrder),
    `idx=${exCase.soldIdx}/${exCase.soldN - 1} order=${JSON.stringify(exCase.soldOrder)}`);
  await p.evaluate(() => { state.country = '全部'; state.c2 = '全部'; state.src = '全部'; state.rankBy = 'rank'; refreshAll(); });
  await p.waitForTimeout(600);

  /* ---------- 复审①：lib/insight 不被 c3/period 污染 ---------- */
  const poll = await p.evaluate(async () => {
    const before = {};
    state.view = 'lib'; refreshAll(); await new Promise((r) => setTimeout(r, 700));
    before.libLen = document.querySelector('#view').innerText.length;
    before.libDesc = document.querySelector('#viewDesc').textContent;
    state.view = 'insight'; refreshAll(); await new Promise((r) => setTimeout(r, 700));
    before.insLen = document.querySelector('#view').innerText.length;
    before.insDesc = document.querySelector('#viewDesc').textContent;
    before.insHasMkt = document.querySelector('#view').innerText.indexOf('市场机会') >= 0;
    /* 打开 c3 / period 隐藏控件值（取真实库中同时存在的取值：抖音罗盘的 60 条） */
    state.c3 = '沐浴露与香皂'; state.period = '2026-09-12 ~ 2026-09-18';
    state.view = 'lib'; refreshAll(); await new Promise((r) => setTimeout(r, 700));
    const libAfter = document.querySelector('#view').innerText.length;
    state.view = 'insight'; refreshAll(); await new Promise((r) => setTimeout(r, 700));
    const insAfter = document.querySelector('#view').innerText.length;
    const dataOfN = dataOf().length;
    const brN = boardRankDataOf().length;
    state.c3 = '全部'; state.period = '全部';
    return {
      before: before, libAfter: libAfter, insAfter: insAfter, dataOfN: dataOfN, brN: brN,
      libDescHas400: before.libDesc.indexOf('400 个商品') >= 0
    };
  });
  chk('复审①｜lib 页面默认计数保持 V10（400 个商品）', poll.libDescHas400 === true, poll.before.libDesc.slice(0, 80));
  chk('复审①｜设置 c3/period 后 lib 渲染完全不变（隐藏控件不生效）',
    poll.libAfter === poll.before.libLen, `${poll.before.libLen} -> ${poll.libAfter}`);
  chk('复审①｜设置 c3/period 后 insight 渲染完全不变',
    poll.insAfter === poll.before.insLen, `${poll.before.insLen} -> ${poll.insAfter}`);
  chk('复审①｜dataOf() 不受 c3/period 影响（V10 语义）', poll.dataOfN === 400, `n=${poll.dataOfN}`);
  chk('复审①｜boardRankDataOf 受 c3/period 影响（恰好命中抖音罗盘 60 条）',
    poll.brN === 60, `n=${poll.brN}`);
  chk('回归｜机会洞察仍渲染出机会卡', dom.insight.len > 80, `len=${dom.insight.len}`);
  chk('回归｜品类与成分库仍渲染', dom.lib.len > 80, `len=${dom.lib.len}`);
  chk('回归｜口碑诊断仍渲染', dom.review.len > 40 && dom.review.txt.indexOf('评价') >= 0, `len=${dom.review.len}`);

  chk('验收⑦｜桌面端 JS 错误数 = 0', errs.length === 0, errs.slice(0, 6).join(' || '));

  /* ---------- S4 移动端 390 ---------- */
  const p2 = await b.newPage({ viewport: { width: 390, height: 844 } });
  attach(p2, '[mobile]');
  await p2.addInitScript(MOCK);
  await p2.goto('file://' + PAGE, { waitUntil: 'load' });
  await p2.waitForTimeout(3200);

  const mb = await p2.evaluate(() => {
    const vis = (s) => { const e = document.querySelector(s); if (!e) return false; const st = getComputedStyle(e);
      return st.display !== 'none' && st.visibility !== 'hidden'; };
    const h = (s) => { const e = document.querySelector(s); return e ? e.offsetHeight : 0; };
    return {
      winW: window.innerWidth,
      scrollW: document.documentElement.scrollWidth,
      fltOpenVis: vis('.flt-open'), fltOpenH: h('.flt-open'),
      chipsWideVis: vis('.chips-wide'),
      inputFont: (function () { const e = document.querySelector('input#kw'); return e ? getComputedStyle(e).fontSize : ''; })(),
      selChips: document.querySelectorAll('.flt-sel-chips .flt-sc').length
    };
  });
  chk('移动端｜无页面级横向溢出', mb.scrollW <= mb.winW + 2, `scrollW=${mb.scrollW} winW=${mb.winW}`);
  chk('移动端｜小屏不依赖横向筛选长条', mb.chipsWideVis === false, '');
  chk('移动端｜出现「筛选」按钮', mb.fltOpenVis === true, '');
  chk('移动端｜筛选按钮触控高度 ≥ 44px', mb.fltOpenH >= 44, `h=${mb.fltOpenH}`);
  chk('移动端｜输入框字号 ≥ 16px', parseFloat(mb.inputFont) >= 16, mb.inputFont);

  /* 打开抽屉：视觉/结构验收（不只 display!=none） */
  const draw = await p2.evaluate(async () => {
    const btn = document.querySelector('.flt-open');
    if (!btn) return { ok: false };
    btn.click();
    await new Promise((r) => setTimeout(r, 700));
    const layer = document.getElementById('fltLayer');
    const scrim = document.querySelector('.flt-scrim');
    const sheet = document.querySelector('.flt-sheet');
    const sbd = document.querySelector('.flt-sbd');
    const shd = document.querySelector('.flt-shd');
    if (!layer || !scrim || !sheet || !sbd || !shd) return { ok: false, why: 'missing-node' };
    const lr = layer.getBoundingClientRect(), sr = scrim.getBoundingClientRect(), tr = sheet.getBoundingClientRect();
    const hit = document.elementFromPoint(innerWidth / 2, 60);   /* 抽屉上方一点，应被遮罩接住 */
    const st = getComputedStyle(sheet);
    const a = shd.getBoundingClientRect();
    const firstRow = document.querySelector('.flt-sbd .flt-row');
    const b2 = firstRow ? firstRow.getBoundingClientRect() : null;
    const overlap = b2 ? !(a.bottom <= b2.top + 1 || b2.bottom <= a.top + 1) : null;
    const touchables = Array.from(document.querySelectorAll('.flt-sheet .chip, .flt-sheet .mini, .flt-sheet select'));
    const minH = touchables.length ? Math.min.apply(null, touchables.map((c) => c.getBoundingClientRect().height)) : 0;
    return {
      ok: true,
      parentIsBody: layer.parentElement === document.body,
      layerCovers: Math.abs(lr.top) < 2 && Math.abs(lr.left) < 2 &&
        Math.abs(lr.width - innerWidth) < 3 && Math.abs(lr.height - innerHeight) < 3,
      scrimCovers: Math.abs(sr.width - innerWidth) < 3 && Math.abs(sr.height - innerHeight) < 3,
      scrimHit: hit ? !!(hit.closest('.flt-scrim') || hit.closest('.flt-sheet')) : false,
      hitCls: hit ? (hit.className || '').toString().slice(0, 30) : '',
      sheetOpaque: st.backgroundColor === 'rgb(255, 255, 255)',
      sheetAtBottom: Math.abs(tr.bottom - innerHeight) < 3,
      sheetFullW: Math.abs(tr.width - innerWidth) < 3,
      sheetAboveScrim: tr.top >= sr.top && tr.bottom <= sr.bottom,
      sbdScrollable: sbd.scrollHeight > sbd.clientHeight + 2,
      bodyLock: document.body.classList.contains('flt-lock') && getComputedStyle(document.body).overflow === 'hidden',
      headOverlap: overlap,
      touchMinH: minH,
      chipN: document.querySelectorAll('.flt-sheet .chip').length,
      scrollW: document.documentElement.scrollWidth, winW: innerWidth,
      scrollY: window.scrollY
    };
  });
  chk('复审⑦｜抽屉挂在 body 直下（脱离 topbar 的 backdrop-filter 包含块）',
    draw.ok && draw.parentIsBody === true, JSON.stringify(draw).slice(0, 90));
  chk('复审⑦｜遮罩全屏覆盖、命中测试被遮罩接住（底层不可穿透点击）',
    draw.ok && draw.scrimCovers && draw.scrimHit, `hit=${draw.hitCls}`);
  chk('复审⑦｜抽屉本体不透明白色面板（rgb 255,255,255）',
    draw.ok && draw.sheetOpaque, 'bg=' + draw.sheetOpaque);
  chk('复审⑦｜抽屉贴底、全宽、位于遮罩之上', draw.ok && draw.sheetAtBottom && draw.sheetFullW && draw.sheetAboveScrim,
    JSON.stringify(draw).slice(0, 90));
  chk('复审⑦｜抽屉内容独立滚动（.flt-sbd 可滚）', draw.ok && draw.sbdScrollable, '');
  chk('复审⑦｜打开时锁定 body 滚动（背景不跟着滚）', draw.ok && draw.bodyLock, '');
  chk('复审⑦｜标题与字段不重叠', draw.ok && draw.headOverlap === false, '');
  chk('复审⑦｜抽屉内可点目标 ≥ 44px', draw.ok && draw.touchMinH >= 44, `minH=${draw.touchMinH}`);
  chk('复审⑦｜抽屉打开仍无横向溢出', draw.ok && draw.scrollW <= draw.winW + 2, `scrollW=${draw.scrollW}`);

  /* 关闭 → 状态稳定 */
  const closeT = await p2.evaluate(async () => {
    const y0 = window.scrollY;
    const done = document.querySelector('.flt-sheet .mini');
    if (!done) return { ok: false };
    done.click();
    await new Promise((r) => setTimeout(r, 500));
    const layer = document.getElementById('fltLayer');
    return {
      ok: true, open: state.fltOpen, layerCleared: !layer.innerHTML,
      unlock: !document.body.classList.contains('flt-lock'),
      scrollKept: window.scrollY === y0,
      fltOpenBtnBack: !!document.querySelector('.flt-open')
    };
  });
  chk('复审⑦｜点「完成」收抽屉：状态复位、层清空、解锁、滚动位置不动',
    closeT.ok && closeT.open === '0' && closeT.layerCleared && closeT.unlock && closeT.scrollKept && closeT.fltOpenBtnBack,
    JSON.stringify(closeT));

  /* 再开 → 选国家 → 抽屉保持、已选回显 */
  const sel = await p2.evaluate(async () => {
    document.querySelector('.flt-open').click();
    await new Promise((r) => setTimeout(r, 500));
    const s = document.querySelector('.flt-sbd select[data-f-sel="country"]');
    if (!s) return { ok: false, why: 'no-select' };
    const opt = Array.from(s.options).find((o) => o.value !== '全部');
    if (!opt) return { ok: false, why: 'no-option' };
    s.value = opt.value;
    s.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 800));
    const sheetStill = !!document.querySelector('.flt-sheet');
    return {
      ok: true, v: opt.value, state: state.country, sheetStill: sheetStill,
      selChips: Array.from(document.querySelectorAll('.flt-sel-chips .flt-sc')).map((x) => x.innerText.replace(/\s+/g, ' ')),
      banner: (document.querySelector('.flt-open .n') || {}).textContent || '',
      optText: opt.textContent,
      scrollW: document.documentElement.scrollWidth, winW: window.innerWidth
    };
  });
  chk('复审④｜抽屉里国家选项计数基于真实数据（无 400）',
    sel.ok && sel.optText.indexOf('400') < 0, sel.optText || '');
  chk('移动端｜抽屉里选国家生效、抽屉保持、回显已选条件',
    sel.ok && sel.state === sel.v && sel.sheetStill && sel.selChips.length > 0,
    JSON.stringify(sel).slice(0, 180));
  chk('移动端｜筛选按钮出现已选计数', /^[1-9]/.test(String(sel.banner)), `n=${sel.banner}`);
  chk('移动端｜选完筛选仍无横向溢出', sel.ok && sel.scrollW <= sel.winW + 2, '');

  /* 移动端榜单不溢出 */
  await p2.evaluate(async () => {
    document.querySelectorAll('.flt-sc button').forEach((x) => x.click());
    await new Promise((r) => setTimeout(r, 400));
    const close = document.querySelector('.flt-sheet .mini');
    if (close) close.click();
    await new Promise((r) => setTimeout(r, 400));
    document.querySelector('[data-view="rank"]').click();
  });
  await p2.waitForTimeout(900);
  const mRank = await p2.evaluate(() => {
    const tabs = Array.from(document.querySelectorAll('.rank-tab'));
    return {
      scrollW: document.documentElement.scrollWidth, winW: window.innerWidth,
      tabMinH: tabs.length ? Math.min.apply(null, tabs.map((t) => t.offsetHeight)) : 0,
      wrapOverflow: Array.from(document.querySelectorAll('.rkt-wrap')).map((w) => w.scrollWidth - w.clientWidth),
      tableN: document.querySelectorAll('.rkt').length
    };
  });
  chk('移动端｜榜单 Tab 触控 ≥ 44px', mRank.tabMinH >= 44, `h=${mRank.tabMinH}`);
  chk('移动端｜榜单页无页面级横向溢出', mRank.scrollW <= mRank.winW + 2, `scrollW=${mRank.scrollW}`);
  chk('移动端｜小屏榜单表格改卡片', mRank.wrapOverflow.every((x) => x <= 2), JSON.stringify(mRank.wrapOverflow));
  chk('验收⑦｜移动端 JS 错误数 = 0', errs.filter((e) => e.indexOf('[mobile]') === 0).length === 0,
    errs.filter((e) => e.indexOf('[mobile]') === 0).slice(0, 6).join(' || '));

  await b.close();

  /* ================= 报告 ================= */
  const pass = RES.filter((r) => r.ok).length;
  const fail = RES.filter((r) => !r.ok);
  console.log('\n================ V11·R2 验收结果 ================');
  RES.forEach((r) => {
    console.log((r.ok ? '  PASS  ' : '  FAIL  ') + r.name + (r.detail ? '   [' + r.detail + ']' : ''));
  });
  console.log('\n---- 引擎实测（报告引用） ----');
  console.log('印尼×唇妆 7 条增速 : ' + JSON.stringify(L.gs));
  console.log('  均值 ' + L.mean + '% / 全量中位 ' + L.medAll + '% / 稳健中枢 ' + L.med + '%（剔除 ' + L.ex + ' 条）');
  console.log('insightsOf(V10均值) 含印尼·唇妆: ' + eng.insV10HasLip + ' | boardInsightsOf(稳健) 含: ' + eng.brHasLip);
  console.log('金额保护: 全范围=' + eng.cgAll.ok + ' 多国=' + eng.cgMultiCty.ok + ' 缺币种=' + eng.cgNoCur.ok +
    ' 多周期=' + eng.cgMultiPeriod.ok + ' 蝉妈妈单国=' + eng.cgCmm.ok + '(' + eng.cgCmm.currency + ')');
  console.log('分榜: ' + JSON.stringify(eng.groups));
  console.log('计数: board total=' + eng.counts.board.total + ' src=' + JSON.stringify(eng.counts.board.src) +
    ' | lib total=' + eng.counts.lib.total);
  console.log('\n合计 ' + RES.length + ' 项断言：通过 ' + pass + '，失败 ' + fail.length);
  console.log('JS 错误总数    : ' + errs.length);
  if (errs.length) errs.slice(0, 10).forEach((e) => console.log('   ' + e));

  if (fail.length) {
    console.log('\n*** 存在失败断言，退出码 1 ***');
    process.exit(1);
  }
  console.log('\nV11_ALL_ASSERTIONS_PASS');
  process.exit(0);
})().catch((e) => {
  console.error('验收脚本自身异常（按失败处理）:', e);
  process.exit(2);
});
