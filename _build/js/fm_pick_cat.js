(function () {
  // 找筛选栏里文本恰为「美妆个护」的可点击元素
  var cands = [].slice.call(document.querySelectorAll('span,div,li,a'))
    .filter(function (e) {
      var t = (e.innerText || '').trim();
      return t === '美妆个护' && e.children.length === 0;
    });
  if (!cands.length) return JSON.stringify({ ok: false, why: 'no chip' });
  // 选最靠近「商品分类」区域的那个（y 坐标较大且靠上）
  var target = cands[0];
  var rect = target.getBoundingClientRect();
  target.click();
  return JSON.stringify({ ok: true, clicked: true, cands: cands.length,
    rect: { x: Math.round(rect.x), y: Math.round(rect.y) } });
})()
