(function () {
  function get(url) {
    var x = new XMLHttpRequest();
    x.open('GET', url, false);   // 同步，便于 webbridge 直接取值
    x.send(null);
    return { status: x.status, text: x.responseText };
  }
  var t = Math.floor(Date.now() / 1000);
  var url = '/api/goods/saleRank?page=1&pagesize=100&order=1,2&l1_cid=14&_time=' + t + '&cnonce=' + Math.floor(Math.random() * 99999999);
  var r = get(url);
  var out = { url: url, status: r.status, len: r.text.length };
  try {
    var j = JSON.parse(r.text);
    out.topKeys = Object.keys(j);
    var data = j.data || j.result || j;
    out.dataKeys = data && typeof data === 'object' ? Object.keys(data).slice(0, 12) : typeof data;
    var list = data && (data.list || data.records || data.data);
    if (Array.isArray(list)) {
      out.count = list.length;
      out.itemKeys = Object.keys(list[0]).slice(0, 40);
      out.first = { title: (list[0].title || '').slice(0, 50), author_count: list[0].author_count, sold_count: list[0].sold_count, region: list[0].region };
    } else {
      out.snippet = r.text.slice(0, 400);
    }
  } catch (e) { out.err = String(e); out.snippet = r.text.slice(0, 400); }
  return JSON.stringify(out);
})()
