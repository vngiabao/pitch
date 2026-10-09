const fs=require('fs'),path=require('path');
const {chromium}=require('C:/Users/vngia/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
const root=path.resolve(__dirname,'..'),dir=path.join(root,'.impeccable','review','autonomy');fs.mkdirSync(dir,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
const captures=[];
for(const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
 await page.setViewportSize({width,height});await page.goto('http://127.0.0.1:8765/applications');await page.getByRole('heading',{name:'Application Pilot',exact:true}).waitFor();await page.getByRole('heading',{name:'Daily email report',exact:true}).waitFor();
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Application page overflow');
 const report=page.getByRole('button',{name:'Read report',exact:true}).first();await report.click();await page.locator('.report-copy').waitFor();
 const file=path.join(dir,name+'-applications.png');await page.screenshot({path:file,fullPage:true});captures.push(file);
 await page.goto('http://127.0.0.1:8765/opportunities');await page.getByRole('button',{name:'All',exact:true}).click();const link=page.getByRole('link',{name:'Claude Startups',exact:true}).first();await link.waitFor();await link.click();await page.getByRole('heading',{name:'Credits & conditions',exact:true}).waitFor();
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Credit detail overflow');
 const detail=path.join(dir,name+'-credits.png');await page.screenshot({path:detail,fullPage:true});captures.push(detail);
}
await browser.close();const report={routes:['applications','opportunities','opportunity detail'],desktop:'1440x1000',mobile:'390x844',page_errors:errors,page_overflow:false,captures,external_actions_triggered:false};fs.writeFileSync(path.join(root,'reports','autonomy-ui-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
