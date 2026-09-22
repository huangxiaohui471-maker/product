(function () {
  var out = { url: location.href };
  // 找「商品分类」附近被选中的项
  var t = document.body.innerText.replace(/\s+/g, ' ');
  var i = t.indexOf('商品分类');
  out.nearCat = i >= 0 ? t.slice(i, i + 160) : '(no 商品分类)';
  // 常见选中态类名
  var sel = [].slice.call(document.querySelectorAll('[class*="active"],[class*="selected"],[class*="checked"]'))
    .map(function (e) { return (e.innerText || '').trim().slice(0, 18); })
    .filter(function (x) { return x && x.length < 18; }).slice(0, 12);
  out.selected = sel;
  // 表格第一行的分类列（若有）
  var ths = [].slice.call(document.querySelectorAll('thead th')).map(function (x) { return (x.innerText || '').trim(); });
  out.heads = ths;
  return JSON.stringify(out);
})()
