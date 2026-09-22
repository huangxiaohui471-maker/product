const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const D = path.join(__dirname, 'data');
const NUM = new Set(['价格','销量','销售额','环比增速','关联达人数','退货率','评分','评价数','预估成本','SKU 数']);
const SEL = new Set(['品类','数据来源','所属市场','国家/地区','剂型','技术壁垒','评价来源','备案路径','宣称支撑难度','与我方价格带匹配','与我方客群匹配','与我方 SKU 重合度','决策状态','数据标记','二级类目','三级类目']);
function wrap(rec,i){const o={};for(const[k,v]of Object.entries(rec)){if(v===null||v===''||v===undefined||k.startsWith('_'))continue;if(NUM.has(k))o[k]={number:Number(v)};else if(SEL.has(k))o[k]={select:String(v)};else if(k==='上市日期')o[k]={date:String(v).slice(0,19)};else o[k]={text:String(v)};}o._id='p'+i;return o;}
const ai=JSON.parse(fs.readFileSync(path.join(D,'records_cat_400.json'),'utf8'));const recs=(ai.records||ai);
const cs=JSON.parse(fs.readFileSync(path.join(__dirname,'cloud_platform.json'),'utf8'));
const by={};for(const c of (cs.results||cs))if(c['商品ID'])by[String(c['商品ID'])]=c;
for(const r of recs){const c=by[String(r['商品ID']||'')];if(c)for(const k of ['SKU 数','备案/许可号','法规合规声明','数据标记','二级类目','三级类目','榜单排名'])if(c[k]!==undefined&&c[k]!==null&&c[k]!=='')r[k]=c[k];}
(async()=>{
const b=await chromium.launch();const p=await b.newPage({viewport:{width:1440,height:980}});
await p.addInitScript('window.__SMART_PAGE__={database:{query:function(){return Promise.resolve({results:' + JSON.stringify(recs.map(wrap)) + ',nextCursor:null,hasMore:false});},getSchema:function(){return Promise.resolve({properties:[]});},addRecord:function(){return Promise.resolve({recordId:"x"});},deleteRecord:function(){return Promise.resolve({ok:true});},onUpdated:function(){return function(){};}}};');
await p.goto('file://' + path.join(__dirname, '..', '全球选品平台.html'), {waitUntil:'load'});
await p.waitForTimeout(3000);
await p.evaluate(()=>document.querySelector('[data-view="board"]').click());
await p.waitForTimeout(1200);
const out=await p.evaluate(()=>{
  const cells=Array.from(document.querySelectorAll('.hcell')).map(x=>({
    cls:x.className.replace('hcell','').trim(),
    v:(x.querySelector('b')||{}).textContent||'',
    n:parseInt((((x.querySelector('i')||{}).textContent)||'0').replace(/[^0-9]/g,''),10)||0
  }));
  return {
    l3:cells.filter(c=>c.cls.indexOf('l3')>=0),
    l1:cells.filter(c=>c.cls.indexOf('l1')>=0),
    bad:cells.filter(c=>c.cls.indexOf('l3')>=0&&c.n<3),
    hi:cells.filter(c=>parseFloat(c.v.replace('+','').replace('%',''))>=60).sort((a,b)=>b.n-a.n).slice(0,16)
  };
});
console.log('l3 数:', out.l3.length, ' 样本<3 的 l3（违规）:', JSON.stringify(out.bad));
console.log('l1（降级）数:', out.l1.length, JSON.stringify(out.l1.map(c=>c.v+'/'+c.n+'样本')));
console.log('med>=60 的格子（值 / 样本数 / 配色）:');
out.hi.forEach(c=>console.log('   ', c.v, c.n+'样本', c.cls||'l0'));
await b.close();
})();
