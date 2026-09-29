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
    '@media (max-width:600px){.demo-decision-layout{padding:13px}.demo-decision-stats-expanded{grid-template-columns:repeat(2,minmax(0,1fr))}.demo-analysis-compact .demo-evidence-strip{grid-template-columns:1fr}.demo-report-list>div{grid-template-columns:72px minmax(0,1fr);gap:9px;padding:9px 0}}'
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
    var headings = root.querySelectorAll('.stage-heading')
    Array.prototype.forEach.call(headings, function (heading) {
      var title = heading.querySelector('h1')
      if (cleanText(title) === '产品 Demo') heading.classList.add('demo-stage-heading-merged')
    })
    var panel = root.querySelector('.demo-decision-panel')
    if (panel) {
      var title = panel.querySelector('.panel-heading h2')
      if (title) title.textContent = '产品 Demo · 核心判断'
      ensurePlanningStats(root, panel)
    }
    var analysis = root.querySelector('.demo-analysis-panel')
    if (analysis) analysis.classList.add('demo-analysis-compact')
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
