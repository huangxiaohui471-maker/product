(() => {
  const all = [...document.querySelectorAll('*')];
  const cand = all.filter(e => (e.innerText || '').trim() === '市场' && e.children.length <= 1);
  const report = [];
  cand.forEach((el, i) => {
    let p = el, hops = 0, clickable = null;
    while (p && hops < 5) {
      if (getComputedStyle(p).cursor === 'pointer') { clickable = p; break; }
      p = p.parentElement; hops++;
    }
    const target = clickable || el;
    target.setAttribute('data-wbtmp', 'mkt' + i);
    const r = target.getBoundingClientRect();
    report.push({
      i: i, tag: target.tagName, cls: String(target.className || '').slice(0, 60),
      x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
      visible: r.width > 0 && r.height > 0
    });
  });
  return JSON.stringify({ count: cand.length, report: report });
})()
