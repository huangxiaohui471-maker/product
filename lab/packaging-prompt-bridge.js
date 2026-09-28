(function () {
  var KEY = '__packaging_prompt_bridge_v1__';
  var library = window.__PACKAGING_PROMPT_LANGUAGE_LIBRARY__ || {};

  function text(value, max) {
    var out = String(value || '').trim();
    return max ? out.slice(0, max) : out;
  }

  function chooseLanguage(input) {
    var hay = [input.productNeed, input.opportunity, input.signal, input.direction, input.style].join(' ');
    var rules = Array.isArray(library.translationRules) ? library.translationRules : [];
    var matched = rules.filter(function (rule) {
      return (rule.signals || []).some(function (signal) { return hay.indexOf(signal) >= 0; });
    }).slice(0, 3);
    if (!matched.length) matched = rules.slice(0, 2);
    var archetypes = Array.isArray(library.visualArchetypes) ? library.visualArchetypes : [];
    var archetype = archetypes.find(function (item) {
      return hay.indexOf('科学') >= 0 || hay.indexOf('功效') >= 0 ? item.id === 'clinical-minimal' : item.id === 'soft-mineral';
    }) || archetypes[0] || { name: '安静极简感', language: '有限色彩、清晰轮廓、充足留白和低反射材质。' };
    var quality = (library.qualityBar || []).slice(0, 4).join('；');
    var production = (library.productionRules || []).slice(0, 3).join('；');
    var negative = (library.negativeRules || []).join('；');
    var translations = matched.map(function (item) { return item.language; }).join('；');
    return {
      archetype: archetype,
      translations: translations,
      quality: quality,
      production: production,
      negative: negative,
      palette: hay.indexOf('夜间') >= 0 || hay.indexOf('修护') >= 0
        ? ['#1e293b', '#e7e2d8', '#b48b5a']
        : ['#e8eee8', '#f4f1e9', '#26332f'],
      finishes: hay.indexOf('专业') >= 0 || hay.indexOf('科学') >= 0
        ? ['细腻哑光', '局部丝印']
        : ['磨砂触感', '低光泽哑光']
    };
  }

  function enrichPromptRequest(body) {
    var selected = chooseLanguage(body);
    var enriched = Object.assign({}, body, {
      visualLanguageBrief: {
        visualArchetype: selected.archetype.name,
        translation: selected.translations,
        qualityBar: selected.quality,
        productionConstraints: selected.production,
        negativeRules: selected.negative
      },
      promptInstruction: '不要只复述需求；请把需求拆成轮廓、材质、比例、色彩占比、字体留白、工艺、摄影和负面约束。'
    });
    return enriched;
  }

  function enrichImageRequest(body) {
    var selected = chooseLanguage(body);
    var promptOverride = text(window.__PACKAGING_LAST_PROMPT__ || body.promptOverride, 2200);
    var original = text(body.description, 180);
    var languageDescription = [
      '视觉原型：' + selected.archetype.name + '。',
      selected.archetype.language,
      '需求转译：' + selected.translations + '。',
      '生产约束：' + selected.production + '。',
      '负面约束：' + selected.negative + '。'
    ].join(' ');
    return Object.assign({}, body, {
      structure: text([body.structure, '轮廓清晰、比例克制、容器与纸盒形成系列关系'].filter(Boolean).join('；'), 80),
      style: text([body.style, selected.archetype.name, selected.archetype.language].filter(Boolean).join('；'), 80),
      description: text([promptOverride || original, languageDescription].filter(Boolean).join(' '), 240),
      palette: selected.palette,
      finishes: selected.finishes
    });
  }

  function install() {
    if (!window.fetch || window.fetch[KEY]) return;
    var originalFetch = window.fetch;
    var wrapped = function (input, init) {
      var url = typeof input === 'string' ? input : (input && input.url) || '';
      if (!init || typeof init.body !== 'string' || !/\/api\/ai\/(image-prompt|packaging)(?:$|\?)/.test(url)) return originalFetch.apply(this, arguments);
      var body;
      try { body = JSON.parse(init.body); } catch (error) { return originalFetch.apply(this, arguments); }
      var isPrompt = /\/image-prompt(?:$|\?)/.test(url);
      var nextInit = Object.assign({}, init, { body: JSON.stringify(isPrompt ? enrichPromptRequest(body) : enrichImageRequest(body)) });
      return originalFetch.call(this, input, nextInit).then(function (response) {
        if (isPrompt && response && response.clone) {
          response.clone().json().then(function (result) {
            if (result && result.prompt) window.__PACKAGING_LAST_PROMPT__ = result.prompt;
          }).catch(function () {});
        }
        return response;
      });
    };
    wrapped[KEY] = true;
    window.fetch = wrapped;
  }

  install();
  var sawBundleShim = false;
  var attempts = 0;
  var timer = window.setInterval(function () {
    if (window.__eyeOilShimInstalled) sawBundleShim = true;
    install();
    attempts += 1;
    if (attempts > 240 || (sawBundleShim && window.fetch[KEY])) window.clearInterval(timer);
  }, 50);
}());
