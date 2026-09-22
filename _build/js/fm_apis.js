(function () {
  var rs = performance.getEntriesByType('resource').map(function (e) { return e.name; })
    .filter(function (u) { return /api|list|rank|product/i.test(u) && !/\.(js|css|png|jpg|webp|svg|woff)/i.test(u); });
  var uniq = [];
  rs.forEach(function (u) { if (uniq.indexOf(u) < 0) uniq.push(u); });
  return JSON.stringify({ count: uniq.length, urls: uniq.slice(-40) });
})()
