// Find and actually launch an existing browser. No installs, user profiles, or network.
const fs=require('fs'),path=require('path'),os=require('os');
const roots=[process.cwd(),path.join(os.homedir(),'.workbuddy/binaries/node/workspace'),path.join(os.homedir(),'.workbuddy'),__dirname];
const chrome=[process.env.CHROME_PATH,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge','/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser',process.env.LOCALAPPDATA&&path.join(process.env.LOCALAPPDATA,'Google/Chrome/Application/chrome.exe'),process.env.PROGRAMFILES&&path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe')].filter(x=>x&&fs.existsSync(x));
(async()=>{
 const attempts=[];
 for(const name of ['playwright','playwright-core','puppeteer','puppeteer-core']){
  let modulePath;
  try{modulePath=require.resolve(name,{paths:roots});}catch(e){attempts.push({name,status:'module_not_found'});continue;}
  const pkg=require(modulePath);
  for(const executablePath of [undefined,...chrome]){
   let browser;
   try{
    const options={headless:true,...(executablePath?{executablePath}:{})};
    browser=name.startsWith('playwright')?await pkg.chromium.launch(options):await pkg.launch(options);
    const page=await browser.newPage();await page.setContent('<title>browser probe</title><p>Local check</p>');
    const title=await page.title();await browser.close();
    console.log(JSON.stringify({ok:title==='browser probe',engine:name,modulePath,executablePath:executablePath||'engine_default',message:'Browser launched; use this engine for page screenshots AND a real save/reload interaction. This probe alone does not validate the app.'},null,2));return;
   }catch(e){attempts.push({name,executablePath:executablePath||'engine_default',error:String(e.message).split('\n').slice(0,2).join(' ')});if(browser)await browser.close().catch(()=>{});}
  }
 }
 console.log(JSON.stringify({ok:false,attempts,installedBrowsers:chrome,message:'These local paths failed. Try an exposed browser/preview tool if available; otherwise report the specific unverified operation.'},null,2));process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exitCode=1;});
