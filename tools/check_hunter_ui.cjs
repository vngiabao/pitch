const fs=require('fs'),path=require('path');
const {chromium}=require('C:/Users/vngia/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
const root=path.resolve(__dirname,'..'),dir=path.join(root,'.impeccable','review');fs.mkdirSync(dir,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8765/');await page.getByRole('heading',{name:'Command center',exact:true}).waitFor();
await page.screenshot({path:path.join(dir,'desktop.png'),fullPage:true});
const link=page.locator('a.program-name').first();const href=await link.getAttribute('href');await page.goto('http://127.0.0.1:8765'+href);await page.getByRole('heading',{name:'Application readiness'}).waitFor();
await page.screenshot({path:path.join(dir,'desktop-detail.png'),fullPage:true});
for(const route of ['opportunities','applications','materials','memory','decisions','activity']){
 await page.goto('http://127.0.0.1:8765/'+route);await page.waitForFunction(()=>!document.querySelector('#app .loading')&&document.querySelector('#app h1'));
 if(route==='opportunities'){await page.getByRole('button',{name:'All',exact:true}).click();await page.waitForTimeout(100);if(await page.locator('tbody tr').count()<3)throw Error('Pipeline lost existing records');}
}
await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:8765/');await page.getByRole('heading',{name:'Command center',exact:true}).waitFor();
const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);if(overflow)throw Error('Mobile page overflows viewport');
await page.screenshot({path:path.join(dir,'mobile.png'),fullPage:true});
await page.goto('http://127.0.0.1:8765'+href);await page.getByRole('heading',{name:'Application readiness'}).waitFor();await page.screenshot({path:path.join(dir,'mobile-detail.png'),fullPage:true});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile detail overflows viewport');
await browser.close();const report={routes_checked:7,desktop:'1440x1000',mobile:'390x844',page_errors:errors,mobile_overflow:false,mutating_actions_triggered:false};fs.writeFileSync(path.join(root,'reports','ui-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
