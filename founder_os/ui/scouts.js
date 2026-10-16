// Scouts page: one specialized agent per kind of money or person, each with its schedule, last run and landing page.
const DAY_WORDS={MO:'Mon',TU:'Tue',WE:'Wed',TH:'Thu',FR:'Fri',SA:'Sat',SU:'Sun'};
function scheduleWords(s){
 if(!s||!s.days)return 'No schedule';
 const days=s.days.length===7?'Every day':s.days.map(d=>DAY_WORDS[d]||d).join(' and ');
 const h=((s.hour+11)%12)+1,m=String(s.minute||0).padStart(2,'0'),ap=s.hour<12?'AM':'PM';
 return `${days} at ${h}:${m} ${ap} Eastern`;
}
function lastRunWords(l){
 if(!l)return 'Has not run yet';
 const when=readableDate(l.at);
 if(l.found===null||l.found===undefined)return `Last ran ${when}`;
 return `Last ran ${when}: ${l.found} new${l.checked?` of ${l.checked} checked`:''}`;
}
function scoutCard(s){
 return `<article class="section scout-card${s.running?' running':''}"><div class="section-title"><div><h3>${E(s.name)}</h3><p class="small">${E(s.hunts)}</p></div><span class="credit-status${s.running?' due':''}">${s.running?'Running now':E(scheduleWords(s.schedule))}</span></div>`+
 `<dl class="fact-list scout-facts"><div><dt>Results land in</dt><dd><a href="${E(s.lands_url)}">${E(s.lands_label)}</a></dd></div><div><dt>Last run</dt><dd>${E(lastRunWords(s.last_run))}</dd></div><div><dt>Next run</dt><dd>${s.next_run?E(readableDate(s.next_run)):'On request'}</dd></div>${s.families.length?`<div><dt>Searches</dt><dd>${E(s.families.map(f=>prettyKey(f)).join(', '))}</dd></div>`:''}</dl>`+
 `<div class="actions"><button type="button" data-scout-run="${E(s.key)}"${s.running?' disabled':''}>${s.running?'Running…':'Run now'}</button></div></article>`;
}
async function scouts(){
 const r=await api('/api/scouts'),groups=[...new Set(r.scouts.map(s=>s.group))],b=r.broad_sweep;
 app.innerHTML=heading('Scouts','One agent per kind of money or person. Each one searches its own corner on its own day, and everything it finds waits for you.')+
 `<p class="state-line"><span><strong>${r.scouts.length}</strong> scouts</span><span><strong>${r.scouts.filter(s=>s.running).length}</strong> running now</span><span>Read-only. Nothing is applied to, sent or spent.</span></p>`+
 groups.map(g=>`<section aria-labelledby="g-${E(g.replace(/\W+/g,'-'))}"><div class="block-title"><h2 id="g-${E(g.replace(/\W+/g,'-'))}">${E(g)}</h2></div><div class="scout-grid">${r.scouts.filter(s=>s.group===g).map(scoutCard).join('')}</div></section>`).join('')+
 `<section class="section quiet"><div class="section-title"><div><h3>${E(b.name)}</h3><p class="small">${E(b.hunts)}</p></div><span class="credit-status">${b.running?'Running now':E(scheduleWords(b.schedule))}</span></div><p class="small">${E(lastRunWords(b.last_run))}. <a href="/activity">All research runs</a>.</p></section>`;
}
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-scout-run]');if(!b)return;e.preventDefault();b.disabled=true;
 try{await api('/api/scout-run',{key:b.dataset.scoutRun});await boot();toast('Scout started. Results appear on its page in about 15 minutes.');}
 catch(err){toast(err.message,true);b.disabled=false;}
});
