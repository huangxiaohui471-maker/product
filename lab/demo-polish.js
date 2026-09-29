(function () {
  'use strict'

  // Product Demo is shipped as a compiled lab bundle. This small presentation
  // layer keeps the bundle/data contract intact while fixing the visual hierarchy
  // in both the standalone lab page and the embedded Shadow DOM workbench.
  var STYLE = [
    '.demo-stage-heading-merged{display:none!important}',
    '.demo-decision-panel,.demo-analysis-compact,.demo-report-grid,.demo-validation-panel{max-width:1280px;margin-left:auto;margin-right:auto}',
    '.demo-decision-panel .panel-heading{min-height:46px;padding:10px 16px}',
    '.demo-decision-panel .panel-heading h2{font-size:17px;letter-spacing:-.01em}',
    '.demo-decision-panel .panel-heading p{display:none}',
    '.demo-decision-layout{grid-template-columns:minmax(0,1.12fr) minmax(460px,.88fr);gap:16px;padding:16px 18px}',
    '.demo-decision-copy h2{margin:8px 0 5px;font-size:21px;line-height:1.25}',
    '.demo-decision-copy p{margin-bottom:6px;font-size:13px;line-height:1.55}',
    '.demo-decision-copy small{font-size:10.5px}',
    '.demo-decision-stats-expanded{grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}',
    '.demo-decision-stats>div{min-height:78px;padding:11px 12px;border-radius:11px}',
    '.demo-decision-stats span{font-size:10.5px}',
    '.demo-decision-stats strong{font-size:13px;line-height:1.35}',
    '.demo-analysis-compact{margin-bottom:12px}',
    '.demo-analysis-compact .panel-heading{min-height:44px;padding:9px 16px}',
    '.demo-analysis-compact .panel-heading p{display:none}',
    '.demo-analysis-compact .demo-analysis-summary{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;margin:0;padding:9px 16px 5px;font-size:12px;line-height:1.45}',
    '.demo-analysis-compact .demo-evidence-strip{grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;padding:4px 16px 13px}',
    '.demo-analysis-compact .demo-evidence-strip>div{min-height:68px;padding:9px 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel,#f8fafc)}',
    '.demo-analysis-compact .demo-evidence-strip span{font-size:10px}',
    '.demo-analysis-compact .demo-evidence-strip strong{font-size:12px;line-height:1.35}',
    '.demo-analysis-compact .demo-evidence-strip small{font-size:10px;line-height:1.35}',
    '.demo-report-grid{grid-template-columns:minmax(0,1.42fr) minmax(300px,.78fr);gap:14px;align-items:start;align-content:start}',
    '.demo-report-grid>.panel,.demo-report-grid>aside{min-width:0;align-self:start}',
    '.demo-report-grid .panel-heading{min-height:46px;padding:10px 16px}',
    '.demo-report-grid .panel-heading p{display:none}',
    '.demo-report-list{padding:0 16px 8px}',
    '.demo-report-list>div{grid-template-columns:82px minmax(0,1fr);gap:12px;padding:11px 0}',
    '.demo-report-list span{font-size:10.5px}',
    '.demo-report-list strong{font-size:12px;line-height:1.45}',
    '.demo-report-grid .demo-market-price{margin:0 16px;padding:12px}',
    '.demo-report-grid .demo-benchmark-list{margin:12px 16px;padding-top:10px}',
    '.demo-report-grid .demo-competitor-note{margin:10px 16px;padding-top:10px}',
    '.demo-validation-panel .panel-heading{min-height:44px;padding:9px 16px}',
    '.demo-validation-panel .panel-heading p{display:none}',
    '@media (max-width:1180px){.demo-decision-layout{grid-template-columns:1fr}.demo-decision-stats-expanded{grid-template-columns:repeat(5,minmax(0,1fr))}.demo-report-grid{grid-template-columns:minmax(0,1fr) minmax(280px,.8fr)}}',
    '@media (max-width:900px){.demo-decision-stats-expanded{grid-template-columns:repeat(3,minmax(0,1fr))}.demo-report-grid{grid-template-columns:1fr}.demo-analysis-compact .demo-evidence-strip{grid-template-columns:repeat(2,minmax(0,1fr))}}',
    '@media (max-width:600px){.demo-decision-layout{padding:13px}.demo-decision-stats-expanded{grid-template-columns:repeat(2,minmax(0,1fr))}.demo-analysis-compact .demo-evidence-strip{grid-template-columns:1fr}.demo-report-list>div{grid-template-columns:72px minmax(0,1fr);gap:9px;padding:9px 0}}',
    '.lab-delivery-sheet{max-width:1280px;margin:14px auto 0;border:1px solid #dfe4ec;border-radius:16px;background:#fff;box-shadow:0 12px 30px rgba(15,23,42,.06);overflow:hidden}',
    '.lab-delivery-sheet-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:20px 22px;border-bottom:1px solid #e5e9ef;background:linear-gradient(135deg,#fbfdfd,#f5f8fb)}',
    '.lab-delivery-sheet-head h2{margin:0;color:#1e293b;font-size:18px;letter-spacing:-.02em}',
    '.lab-delivery-sheet-head p{margin:6px 0 0;color:#64748b;font-size:12px;line-height:1.5}',
    '.lab-delivery-status{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}',
    '.lab-delivery-status span,.lab-delivery-section summary em{display:inline-flex;align-items:center;padding:5px 8px;border-radius:999px;background:#edf6f5;color:#18766f;font-size:10px;font-style:normal;white-space:nowrap}',
    '.lab-delivery-status span.pending,.lab-delivery-section summary em.pending{background:#fff6e8;color:#9a650f}',
    '.lab-delivery-overview{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;padding:14px 22px;background:#fff}',
    '.lab-delivery-overview div{min-width:0;padding:10px 11px;border:1px solid #e6eaf0;border-radius:10px;background:#fafbfc}',
    '.lab-delivery-overview small,.lab-delivery-overview b{display:block}',
    '.lab-delivery-overview small{color:#8792a2;font-size:10px}',
    '.lab-delivery-overview b{margin-top:5px;color:#263548;font-size:11px;line-height:1.4;word-break:break-word}',
    '.lab-delivery-sections{display:grid;gap:8px;padding:0 22px 18px}',
    '.lab-delivery-section{border:1px solid #e1e6ee;border-radius:11px;background:#fff;overflow:hidden}',
    '.lab-delivery-section summary{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 15px;cursor:pointer;list-style:none}',
    '.lab-delivery-section summary::-webkit-details-marker{display:none}',
    '.lab-delivery-section summary:hover{background:#f8fafc}',
    '.lab-delivery-section summary strong{color:#263548;font-size:12px}',
    '.lab-delivery-section summary small{display:block;margin-top:3px;color:#8792a2;font-size:10px;font-weight:400}',
    '.lab-delivery-section summary i{margin-left:auto;color:#8792a2;font-size:15px;font-style:normal;transition:transform .16s ease}',
    '.lab-delivery-section[open] summary i{transform:rotate(180deg)}',
    '.lab-delivery-section-body{padding:0 15px 15px;border-top:1px solid #edf0f4}',
    '.lab-delivery-table-wrap{overflow-x:auto}',
    '.lab-delivery-table{width:100%;min-width:720px;border-collapse:collapse}',
    '.lab-delivery-table th,.lab-delivery-table td{padding:10px 9px;border-bottom:1px solid #edf0f4;text-align:left;vertical-align:top;font-size:11px;line-height:1.5}',
    '.lab-delivery-table th{width:22%;color:#536174;background:#fbfcfd;font-weight:600}',
    '.lab-delivery-table td{color:#344256}',
    '.lab-delivery-table td:last-child{color:#66758a}',
    '.lab-delivery-table tr:last-child th,.lab-delivery-table tr:last-child td{border-bottom:0}',
    '.lab-delivery-inline-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px}',
    '.lab-delivery-inline-grid div{padding:10px 11px;border-radius:9px;background:#f7f9fb}',
    '.lab-delivery-inline-grid small,.lab-delivery-inline-grid b{display:block}',
    '.lab-delivery-inline-grid small{color:#8792a2;font-size:9.5px}',
    '.lab-delivery-inline-grid b{margin-top:4px;color:#334155;font-size:11px;line-height:1.45}',
    '.lab-delivery-note{padding:11px 12px;border-left:3px solid #e0a33e;border-radius:4px 9px 9px 4px;background:#fff9ee;color:#795a2e;font-size:10px;line-height:1.6}',
    '@media (max-width:1000px){.lab-delivery-overview{grid-template-columns:repeat(3,minmax(0,1fr))}.lab-delivery-inline-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}',
    '@media (max-width:600px){.lab-delivery-sheet{margin:10px 12px 0}.lab-delivery-sheet-head{display:block;padding:16px}.lab-delivery-status{justify-content:flex-start;margin-top:10px}.lab-delivery-overview,.lab-delivery-sections{padding-left:16px;padding-right:16px}.lab-delivery-overview{grid-template-columns:repeat(2,minmax(0,1fr))}.lab-delivery-inline-grid{grid-template-columns:1fr}}'
  ].join('')

  function addStyle(root) {
    if (!root || !root.appendChild) return
    if (root.querySelector && root.querySelector('style[data-product-demo-polish]')) return
    var style = document.createElement('style')
    style.setAttribute('data-product-demo-polish', 'true')
    style.textContent = STYLE
    var target = root.nodeType === 9 ? (root.head || root.documentElement) : root
    if (target) target.appendChild(style)
  }

  function cleanText(node) {
    return node && (node.textContent || '').replace(/\s+/g, ' ').trim()
  }

  function htmlText(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  function readLocalLabState() {
    try {
      return JSON.parse(window.localStorage.getItem('eye-oil-experiment-lab-v2') || '{}') || {}
    } catch (_) {
      return {}
    }
  }

  function readHandoffValue(grid, label, fallback) {
    if (!grid) return fallback
    var rows = grid.querySelectorAll('.definition-list > div')
    for (var i = 0; i < rows.length; i++) {
      if (cleanText(rows[i].querySelector('dt')) === label) return cleanText(rows[i].querySelector('dd')) || fallback
    }
    return fallback
  }

  function firstValue(values, fallback) {
    for (var i = 0; i < values.length; i++) {
      var value = values[i]
      if (value !== undefined && value !== null && String(value).trim()) return String(value)
    }
    return fallback
  }

  function deliveryData(grid) {
    var state = readLocalLabState()
    var project = state.project || {}
    var packaging = state.packagingDesign || {}
    var analysis = project.analysis || {}
    var product = firstValue([project.name, packaging.productName, readHandoffValue(grid, '产品方向', '')], '待命名产品')
    var source = readHandoffValue(grid, '来源机会', '待关联机会')
    var userTask = readHandoffValue(grid, '用户任务', '待补充用户任务')
    var design = readHandoffValue(grid, '设计约束', firstValue([project.structure, packaging.description], '待补充设计约束'))
    var pending = readHandoffValue(grid, '待验证事项', '待补充验证事项')
    var eye = /眼|睫毛/.test(product + source + userTask)
    var formula = firstValue([project.formula, project.ingredients, analysis.formula], eye ? '角鲨烷、霍霍巴籽油、咖啡因、红景天提取物、维生素E' : '待接入配方数据')
    var functionText = firstValue([analysis.coreFunction, project.sellingPoint, packaging.description], '待补充核心功能')
    var audience = firstValue([analysis.audience, state.targetUser], '待补充目标人群')
    var price = firstValue([project.priceBand, analysis.priceBand], '待确认价格带')
    var texture = eye ? '轻润油相 · 滚珠触感' : '待补充质地与肤感'
    return {
      product: product,
      source: source,
      userTask: userTask,
      design: design,
      pending: pending,
      formula: formula,
      functionText: functionText,
      audience: audience,
      price: price,
      texture: texture,
      specification: firstValue([project.specification, project.volume], eye ? '20ml' : '待补充'),
      cooperation: firstValue([state.cooperation, project.cooperation], 'ODM / OEM · 待确认'),
      quantity: firstValue([project.firstOrderQuantity, project.moq], '首批数量待确认'),
      launch: firstValue([project.launchDate, project.launchTime], '上市时间待确认'),
      benchmark: firstValue([project.benchmark, project.competitor], '待补充对标竞品')
    }
  }

  function deliveryTable(rows) {
    var h = '<div class="lab-delivery-table-wrap"><table class="lab-delivery-table"><thead><tr><th>项目结构</th><th>卖点 / 要求</th><th>功效效果 / 验证目标</th><th>添加成分 / 执行资料</th></tr></thead><tbody>'
    rows.forEach(function (row) {
      h += '<tr><th>' + htmlText(row[0]) + '</th><td>' + htmlText(row[1]) + '</td><td>' + htmlText(row[2]) + '</td><td>' + htmlText(row[3]) + '</td></tr>'
    })
    return h + '</tbody></table></div>'
  }

  function simpleTable(headers, rows) {
    var h = '<div class="lab-delivery-table-wrap"><table class="lab-delivery-table"><thead><tr>'
    headers.forEach(function (header) { h += '<th>' + htmlText(header) + '</th>' })
    h += '</tr></thead><tbody>'
    rows.forEach(function (row) {
      h += '<tr>'
      row.forEach(function (cell) { h += '<td>' + htmlText(cell) + '</td>' })
      h += '</tr>'
    })
    return h + '</tbody></table></div>'
  }

  function makeDeliverySheet(root, grid) {
    if (!grid || !grid.parentNode || grid.parentNode.querySelector('.lab-delivery-sheet')) return
    var data = deliveryData(grid)
    var h = '<section class="lab-delivery-sheet" aria-label="产品开发交付表">'
    h += '<div class="lab-delivery-sheet-head"><div><h2>产品开发交付表</h2><p>把已确认的产品方向整理成研发、供应商和测试团队可以继续填写的执行资料。</p></div><div class="lab-delivery-status"><span>已关联产品方向</span><span class="pending">未确认字段保留为待补充</span></div></div>'
    h += '<div class="lab-delivery-overview">'
    ;[['产品名称', data.product], ['来源机会', data.source], ['用户任务', data.userTask], ['产品形态', data.design], ['目标价格', data.price], ['当前风险', data.pending]].forEach(function (item) {
      h += '<div><small>' + htmlText(item[0]) + '</small><b>' + htmlText(item[1]) + '</b></div>'
    })
    h += '</div><div class="lab-delivery-sections">'
    h += '<details class="lab-delivery-section" open><summary><span><strong>01 · 产品功能</strong><small>每一个卖点都对应功效目标和添加成分</small></span><em>一览表</em><i>⌄</i></summary><div class="lab-delivery-section-body">'
    h += deliveryTable([
      ['核心功能', data.functionText, '让用户在核心场景下获得可感知的体验改善。', data.formula],
      ['用户与场景', data.audience, data.userTask, '目标人群与使用场景待业务确认'],
      ['轻润 / 使用体验', '轻润、便携、易于完成日常护理', '降低油腻、刺激、使用复杂等阻力。', '质地与肤感需要样品验证'],
      ['产品结构', data.design, '结构要支持稳定出液、使用顺手和运输安全。', '瓶器、滚珠/泵头、密封件待包材资料确认'],
      ['安全与边界', '不把概念直接写成确定功效', '功效、刺激性和宣称必须有对应测试证据。', '法规与安全资料待接入'],
      ['商业目标', data.price, '先验证首购体验，再判断是否扩大投入。', '成本、MOQ、毛利待供应商正式报价'],
      ['竞品对标', data.benchmark, '借鉴体验表达，不直接复制竞品结论。', '竞品样品和对标依据待补充']
    ])
    h += '</div></details>'
    h += '<details class="lab-delivery-section"><summary><span><strong>02 · 配方要求</strong><small>配方方向、禁限用和感官要求</small></span><em class="pending">待补资料</em><i>⌄</i></summary><div class="lab-delivery-section-body">'
    h += simpleTable(['要求项', '当前内容', '状态'], [
      ['配方方向', data.formula, '方案草案'],
      ['基础要求', '优先使用成熟原料体系，避免未经验证的功能承诺。', '待研发确认'],
      ['禁限用要求', '按目标市场法规、敏感人群和产品品类要求复核。', '待法规复核'],
      ['感官要求', data.texture + '；不黏腻、不厚重、不影响后续使用。', '待样品确认'],
      ['稳定性要求', '颜色、气味、分层、析出、冷热循环和包材相容性。', '待测试']
    ])
    h += '</div></details>'
    h += '<details class="lab-delivery-section"><summary><span><strong>03 · 背书与证据</strong><small>说明方案依据什么，哪些还不能直接宣称</small></span><em class="pending">待补资料</em><i>⌄</i></summary><div class="lab-delivery-section-body">'
    h += simpleTable(['证据类型', '已接入内容', '交付用途'], [
      ['来源机会', data.source, '说明为什么进入这个产品方向'],
      ['用户任务', data.userTask, '定义产品要完成的核心任务'],
      ['设计依据', data.design, '约束瓶器、包材和视觉预览'],
      ['功效背书', '当前未接入真实功效测试报告', '不得直接转成确定功效宣称'],
      ['供应商背书', '当前未接入正式报价和资质文件', '不得直接视为可生产供应商']
    ])
    h += '</div></details>'
    h += '<details class="lab-delivery-section"><summary><span><strong>04 · 测试维度</strong><small>把卖点转换成可以打样和验收的测试项目</small></span><em class="pending">待执行</em><i>⌄</i></summary><div class="lab-delivery-section-body">'
    h += simpleTable(['测试维度', '测试内容', '通过标准', '状态'], [
      ['功效效果', '验证核心卖点是否能被用户感知。', '待研发填写具体阈值', '待确认'],
      ['感官肤感', '延展、吸收、残留、黏腻和气味。', '待样品评测', '待打样'],
      ['结构体验', '出液均匀、操作顺手、使用量稳定。', '待样品评测', '待打样'],
      ['安全性', '刺激、斑贴、眼周/敏感部位耐受等。', '按目标市场要求确认', '待测试'],
      ['稳定性与兼容', '冷热循环、分层、变色、包材密封和迁移。', '不得出现不可接受变化', '待测试'],
      ['商业验证', '价格接受、内容理解、首批转化和复购信号。', '待确定指标和周期', '待执行']
    ])
    h += '</div></details>'
    h += '<details class="lab-delivery-section"><summary><span><strong>05 · 质地与 SKU</strong><small>明确产品形态、规格和首轮样品边界</small></span><em class="pending">待确认</em><i>⌄</i></summary><div class="lab-delivery-section-body">'
    h += '<div class="lab-delivery-inline-grid">'
    ;[['质地方向', data.texture], ['规格', data.specification], ['SKU 数量', '首轮建议 1 个 SKU'], ['包装形式', data.design], ['首批数量', data.quantity], ['视觉预览', '已从产品设计舱回流']].forEach(function (item) {
      h += '<div><small>' + htmlText(item[0]) + '</small><b>' + htmlText(item[1]) + '</b></div>'
    })
    h += '</div></div></details>'
    h += '<details class="lab-delivery-section"><summary><span><strong>06 · 合作方式与开发周期</strong><small>给供应商和内部执行团队的合作边界</small></span><em class="pending">待确认</em><i>⌄</i></summary><div class="lab-delivery-section-body">'
    h += simpleTable(['项目', '当前内容', '状态'], [
      ['合作方式', data.cooperation, '待确认'],
      ['供应商', '待接入候选供应商、联系人和资质资料', '待接入'],
      ['MOQ / 首批', data.quantity, '待报价确认'],
      ['打样周期', '待供应商确认配方、包材和测试排期', '待确认'],
      ['大货周期', '待供应商确认生产和包材交期', '待确认'],
      ['上市时间', data.launch, '待项目确认'],
      ['对标竞品', data.benchmark, '待补充']
    ])
    h += '</div></details>'
    h += '<div class="lab-delivery-note">当前交付表已经把研发、测试、包材和供应商需要的信息位置固定下来；空缺项显示为“待补充/待确认”，接入真实资料后直接替换对应字段，不改变页面结构。</div>'
    h += '</div></section>'
    grid.insertAdjacentHTML('afterend', h)
  }

  function planningValues() {
    var state = {}
    try {
      state = JSON.parse(window.localStorage.getItem('eye-oil-experiment-lab-v2') || '{}') || {}
    } catch (_) {}
    var assumptions = state.assumptions || {}
    var cost = assumptions.targetCost || state.project && state.project.targetCost
    var cycle = assumptions.developmentCycle || assumptions.leadTime || state.project && state.project.developmentCycle
    return {
      cost: cost ? '≤ ¥' + cost + '/件' : '待成本核算',
      cycle: cycle || '4–6 周'
    }
  }

  function ensurePlanningStats(root, panel) {
    var stats = panel && panel.querySelector('.demo-decision-stats')
    if (!stats || stats.getAttribute('data-planning-stats') === 'ready') return
    var values = planningValues()
    var fields = [
      ['目标成本', values.cost],
      ['开发周期', values.cycle]
    ]
    fields.forEach(function (field) {
      var exists = Array.prototype.some.call(stats.children, function (item) {
        return cleanText(item.querySelector('span')) === field[0]
      })
      if (exists) return
      var cell = document.createElement('div')
      var label = document.createElement('span')
      var value = document.createElement('strong')
      label.textContent = field[0]
      value.textContent = field[1]
      cell.appendChild(label)
      cell.appendChild(value)
      stats.appendChild(cell)
    })
    stats.setAttribute('data-planning-stats', 'ready')
    stats.classList.add('demo-decision-stats-expanded')
  }

  function polish(root) {
    if (!root || !root.querySelectorAll) return
    addStyle(root)
    Array.prototype.forEach.call(root.querySelectorAll('button, h1, h2, h3, p, span, small, strong'), function (node) {
      if (node.children.length) return
      var value = cleanText(node)
      if (!value) return
      var next = value.replace(/生成产品 Demo/g, '生成产品方案').replace(/确认 Demo/g, '确认方案')
      if (next !== value) node.textContent = next
    })
    Array.prototype.forEach.call(root.querySelectorAll('.stage-rail .stage-label'), function (label) {
      if (cleanText(label) === '产品 Demo') label.textContent = '产品方案'
    })
    var headings = root.querySelectorAll('.stage-heading')
    Array.prototype.forEach.call(headings, function (heading) {
      var title = heading.querySelector('h1')
      if (cleanText(title) === '产品 Demo') heading.classList.add('demo-stage-heading-merged')
    })
    var panel = root.querySelector('.demo-decision-panel')
    if (panel) {
      var title = panel.querySelector('.panel-heading h2')
      if (title) title.textContent = '产品方案 · 核心判断'
      ensurePlanningStats(root, panel)
    }
    var analysis = root.querySelector('.demo-analysis-panel')
    if (analysis) analysis.classList.add('demo-analysis-compact')
    var handoff = root.querySelector('.handoff-report-grid')
    if (handoff) makeDeliverySheet(root, handoff)
  }

  function roots() {
    var list = [document]
    var host = window.__labHost
    if (host && host.shadowRoot) list.push(host.shadowRoot)
    return list
  }

  function boot() {
    var run = function () { roots().forEach(polish) }
    run()
    var observer = new MutationObserver(function () { run() })
    observer.observe(document.body, { childList: true, subtree: true })
    window.setInterval(run, 800)
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot)
  else boot()
}())
