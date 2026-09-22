(() => {
  const t = document.querySelector('#syncText');
  const txt = (document.body.innerText || '');
  const cards = document.querySelectorAll('[class*=card],[class*=pcard],[data-rid]').length;
  const kpis = [...document.querySelectorAll('[class*=kpi] [class*=v],[class*=kpi-v]')].map(e => (e.innerText || '').trim()).slice(0, 8);
  return JSON.stringify({
    url: location.href.slice(0, 90),
    title: document.title,
    sync: t ? t.textContent.trim() : null,
    hasDb: !!(window.__SMART_PAGE__ && window.__SMART_PAGE__.database),
    bodyLen: txt.length,
    cards: cards,
    kpis: kpis,
    head: txt.replace(/\s+/g, ' ').slice(0, 240)
  });
})()
