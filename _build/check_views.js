const { chromium } = require('playwright');
const fs = require('fs');
const DIR='/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47';
const F='file://'+encodeURIComponent(DIR+'/全球选品平台.html').replace(/%2F/g,'/');
const schema=JSON.parse(fs.readFileSync(DIR+'/_build/schema_platform.json','utf8'));
const rows=JSON.parse(fs.readFileSync(DIR+'/_build/data/cloud_after.json','utf8')).results;
(async()=>{
  const errs=[];
  const b=await chromium.launch({channel:'chrome',args:['--no-sandbox']});
  const ctx=await b.newContext({viewport:{width:1440,height:1100}});
  await ctx.addInitScript(({schema,rows})=>{window.__SMART_PAGE__={database:{getSchema:()=>Promise.resolve(schema),query:()=>Promise.resolve({results:rows,nextCursor:null,hasMore:false}),addRecord:()=>Promise.resolve({id:'n'}),updateRecord:()=>Promise.resolve({}),deleteRecord:()=>Promise.resolve({}),onUpdated:()=>{}}};},{schema,rows});
  const p=await ctx.newPage();
  p.on('pageerror',e=>errs.push('PE '+e.message));
  p.on('console',m=>{if(m.type()==='error')errs.push('C:'+m.text());});
  await p.goto(F); await p.waitForTimeout(2500);
  for (const [name,label] of [['机会洞察','insight'],['品类与成分库','lib']]) {
    await p.evaluate((n)=>{const els=[...document.querySelectorAll('#nav *')];const t=els.find(e=>(e.innerText||'').trim()===n&&e.getBoundingClientRect().width>0);if(t)t.click();},name);
    await p.waitForTimeout(1200);
    const r=await p.evaluate(()=>{
      const txt=(document.body.innerText||'');
      const rules=[...document.querySelectorAll('#view [class*=rule],#view .r-item,#view .engine-r')].map(e=>(e.innerText||'').replace(/\s+/g,' ').trim().slice(0,60));
      return {head:txt.replace(/\s+/g,' ').slice(0,300), rules:rules.slice(0,8), txtLen:txt.length};
    });
    console.log('=== '+label+' ===');
    console.log(r.head);
    if(r.rules.length) console.log('RULES '+JSON.stringify(r.rules,null,1));
    await p.screenshot({path:DIR+'/_build/shot_real_'+label+'.png'});
  }
  console.log('ERRORS '+JSON.stringify(errs.slice(0,5)));
  await b.close();
})();
