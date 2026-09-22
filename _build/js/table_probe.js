(() => {
  const info = {
    url: location.href,
    title: document.title,
    bodyLen: (document.body.innerText || '').length,
    heads: [...document.querySelectorAll('thead th')].map(e => (e.innerText || '').trim()).filter(Boolean).slice(0, 30),
    rowCount: document.querySelectorAll('tbody tr').length,
    firstRow: null,
    rowHtml: null
  };
  const r = document.querySelector('tbody tr');
  if (r) {
    info.firstRow = (r.innerText || '').replace(/\s+/g, ' ').slice(0, 320);
    info.rowHtml = (r.outerHTML || '').replace(/\s+/g, ' ').slice(0, 700);
  }
  return JSON.stringify(info);
})()
