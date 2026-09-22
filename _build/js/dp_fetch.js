/* 抖音罗盘 商品榜单抽取（webbridge 模式下由 wbeval 调用） */
(() => {
  const rows = [...document.querySelectorAll('tr')].filter(r => String(r.className).includes('aurora-table-row'));
  const data = rows.map((r, idx) => {
    const cells = [...r.querySelectorAll('td')].map(c => (c.innerText || '').replace(/\s+/g, ' ').trim());
    const a = r.querySelector('a[href]');
    const rawName = cells[1] || '';
    const mPrice = rawName.match(/价格带\s*(.+)$/);
    const name = rawName.replace(/价格带\s*.+$/, '').trim();
    return {
      idx: idx + 1,
      rank_text: cells[0] || '',
      name: name,
      price_band: mPrice ? mPrice[1].trim() : '',
      shop: cells[2] || '',
      gmv: cells[3] || '',
      clicks: cells[4] || '',
      orders: cells[5] || '',
      conv: cells[6] || '',
      href: a ? a.getAttribute('href') : ''
    };
  });
  const ctx = (document.body.innerText || '').replace(/\s+/g, ' ');
  const mTime = ctx.match(/(\d{4}\/\d{1,2}\/\d{1,2})\s*-\s*(\d{4}\/\d{1,2}\/\d{1,2})/);
  const mCat = ctx.match(/行业类目[^不]{0,40}/);
  return JSON.stringify({
    url: location.href,
    count: data.length,
    range: mTime ? mTime[1] + ' ~ ' + mTime[2] : '',
    catText: mCat ? mCat[0].slice(0, 60) : '',
    rows: data
  });
})()
