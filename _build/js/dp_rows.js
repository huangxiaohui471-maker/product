(() => {
  const rows = [...document.querySelectorAll('tr')].filter(r => !String(r.className).includes('measure'));
  const out = rows.slice(0, 12).map(r => ({
    cls: String(r.className).slice(0, 70),
    cells: [...r.querySelectorAll('td,th')].map(c => (c.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70))
  }));
  return JSON.stringify({ count: rows.length, out: out });
})()
