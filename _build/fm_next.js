const { chromium } = require('playwright');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const b=await chromium.connectOverCDP('http://127.0.0.1:53126');
  const ps=[];for(const c of b.contexts())for(const p of c.pages())ps.push(p);
  const p=ps.find(x=>x.url().includes('fastmoss.com'));
  await p.goto('https://www.fastmoss.com/zh/e-commerce/saleslist?page=1&l1_cid=14',{waitUntil:'domcontentloaded',timeout:60000});
  await sleep(6000);
  const r=await p.evaluate(()=>{
    const nd=window.__NEXT_DATA__;
    const out={hasNext:!!nd};
    if(nd){ out.size=JSON.stringify(nd).length; }
    // 找页面里所有 script 里的 JSON 大写数据
    const cands=[];
    document.querySelectorAll('script').forEach(s=>{const t=s.textContent||'';if(t.length>2000&&(t.includes('product_id')||t.includes('productId')))cands.push(t.length);});
    out.scripts=cands.slice(0,6);
    // 探查行内是否 react fiber 里有更多字段
    const row=document.querySelector('.ant-table-row');
    let keys=[];
    if(row){ for(const k in row){ if(k.startsWith('__react')) { try{ keys.push('fiber:'+k); }catch(e){} } } }
    out.rowKeys=keys;
    return out;
  });
  console.log(JSON.stringify(r,null,1));
  await b.close();
})();
