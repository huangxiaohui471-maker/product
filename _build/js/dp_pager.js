(function () {
  var out = { url: location.href };
  // 找分页控件
  var pg = document.querySelector('.aurora-pagination, [class*="pagination"]');
  out.pagerText = pg ? (pg.innerText || '').replace(/\s+/g, ' ').slice(0, 200) : '(none)';
  out.pagerCls = pg ? String(pg.className).slice(0, 100) : '';
  // 找下一页按钮
  var btns = [].slice.call(document.querySelectorAll('button, li, a')).filter(function (b) {
    var t = (b.innerText || '').trim();
    return /下一页|下页|Next/.test(t) || /下一页|next/i.test(String(b.className) + ' ' + String(b.getAttribute && b.getAttribute('aria-label') || ''));
  });
  out.nextBtns = btns.slice(0, 5).map(function (b) { return { tag: b.tagName, cls: String(b.className).slice(0, 70), txt: (b.innerText || '').trim().slice(0, 20), disabled: !!b.disabled, aria: b.getAttribute && b.getAttribute('aria-label') }; });
  // 找总条数
  var m = (document.body.innerText || '').replace(/\s+/g, ' ').match(/共\s*(\d+)\s*条/);
  out.total = m ? m[1] : '';
  return JSON.stringify(out);
})()
