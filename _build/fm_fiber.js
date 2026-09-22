const { chromium } = require('playwright');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const b=await chromium.connectOverCDP('http://127.0.0.1:53126');
  const ps=[];for(const c of b.contexts())for(const p of c.pages())ps.push(p);
  const p=ps.find(x=>x.url().includes('fastmoss.com'));
  const r=await p.evaluate(()=>{
    const row=document.querySelector('.ant-table-row');
    if(!row) return {err:'no row'};
    const k=Object.keys(row).find(x=>x.startsWith('__reactProps'));
    const props=row[k];
    const out={};
    if(props){ out.propKeys=Object.keys(props);
      for(const kk of Object.keys(props)){ const v=props[kk];
        if(v&&typeof v==='object'&&!Array.isArray(v)){ out[kk+'_keys']=Object.keys(v).slice(0,45); }
      }
    }
    // 往上走 fiber，找带 dataSource / list 的组件
    const fk=Object.keys(row).find(x=>x.startsWith('__reactFiber'));
    let f=row[fk], hits=[], d=0;
    while(f&&d<60){
      const mp=f.memoizedProps;
      if(mp&&typeof mp==='object'){
        for(const kk of Object.keys(mp)){
          const v=mp[kk];
          if(Array.isArray(v)&&v.length>3&&v[0]&&typeof v[0]==='object'){
            hits.push({d:d,key:kk,len:v.length,fields:Object.keys(v[0]).slice(0,50)});
          }
        }
      }
      f=f.return; d++;
    }
    out.hits=hits.slice(0,6);
    return out;
  });
  console.log(JSON.stringify(r,null,1).slice(0,3000));
  await b.close();
})();
