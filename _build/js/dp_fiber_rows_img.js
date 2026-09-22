(function () {
  function midOf(vr, isRatio) {
    if (!vr || !vr.value_range || !vr.value_range.length) return null;
    var a = vr.value_range;
    var v = a.length === 1 ? a[0].value : (a[0].value + a[a.length - 1].value) / 2;
    if (isRatio) return Math.round(v * 10000) / 100;
    return Math.round(v);
  }
  function mid(vr) { return midOf(vr, false); }
  function raw(vr) {
    if (!vr || !vr.value_range) return '';
    return vr.value_range.map(function (x) { return x.value; }).join(' ~ ');
  }
  var rowOne = document.querySelector('tr.aurora-table-row');
  if (!rowOne) return JSON.stringify({ ok: false, err: 'no row' });
  var fk = Object.keys(rowOne).find(function (x) { return x.indexOf('__reactFiber') === 0; });
  var f = rowOne[fk], ds = null, d = 0;
  while (f && d < 60 && !ds) {
    var mp = f.memoizedProps;
    if (mp && typeof mp === 'object') {
      for (var k in mp) {
        var v = mp[k];
        if (Object.prototype.toString.call(v) === '[object Array]' && v.length > 2 && v[0] && typeof v[0] === 'object' && v[0].product_info) { ds = v; break; }
      }
    }
    f = f.return; d++;
  }
  if (!ds) return JSON.stringify({ ok: false, err: 'no dataSource' });
  var data = ds.map(function (o) {
    var info = o.product_info || {};
    var sh = (info.shop_list || [])[0] || {};
    return {
      rank: info.rank,
      product_id: info.id,
      name: info.name,
      image_url: info.image_url || '',
      price_bin: info.price_bin,
      rank_change: info.rank_change,
      newly_on_ranking: info.newly_on_ranking,
      shop_name: sh.shop_name || '',
      detail_url: info.product_detail_h5_url || '',
      gmv_mid: mid(o.new_pay_amt), gmv_raw: raw(o.new_pay_amt),
      orders_mid: mid(o.pay_combo_cnt), orders_raw: raw(o.pay_combo_cnt),
      clicks_mid: mid(o.product_click_cnt), clicks_raw: raw(o.product_click_cnt),
      conv_mid: midOf(o.product_click_pay_cnt_ratio, true), conv_raw: raw(o.product_click_pay_cnt_ratio)
    };
  });
  var ctx = (document.body.innerText || '').replace(/\s+/g, ' ');
  var mTime = ctx.match(/(\d{4}\/\d{1,2}\/\d{1,2})\s*-\s*(\d{4}\/\d{1,2}\/\d{1,2})/);
  var mCat = ctx.match(/行业类目[^不]{0,40}/);
  return JSON.stringify({
    ok: true, count: data.length,
    range: mTime ? mTime[1] + ' ~ ' + mTime[2] : '',
    catText: mCat ? mCat[0].slice(0, 60) : '',
    rows: data
  });
})()
