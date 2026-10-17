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
// What A Story pays for, and which credit covers it. Uncovered items steer the Credits and Perks scouts.
function stackRow(r,providers){
 const opts=['',...providers.filter(p=>p&&p!==r.covered_by),...(r.covered_by?[r.covered_by]:[])];
 return `<form class="stack-form stack-row" data-id="${E(r.id)}"><input name="item" value="${E(r.item)}" maxlength="120" aria-label="What you pay for" required><input name="provider" value="${E(r.provider||'')}" maxlength="80" placeholder="Provider" aria-label="Provider"><input name="monthly_usd" type="number" min="0" step="0.01" value="${r.monthly_usd??''}" placeholder="$/month" aria-label="Monthly cost"><select name="covered_by" aria-label="Covered by">${opts.map(p=>`<option value="${E(p)}"${p===(r.covered_by||'')?' selected':''}>${p?E(p)+' credits':'Not covered'}</option>`).join('')}</select><button type="submit">Save</button><button type="button" class="link-button" data-stack-delete="${E(r.id)}">Remove</button></form>`;
}
function stackSection(st){
 const u=st.monthly_uncovered,c=st.monthly_covered;
 return `<section class="section" id="stack"><div class="section-title"><h2>What A Story pays for</h2><span class="small">${u||c?`${E(money(u))} a month not covered · ${E(money(c))} covered by credits`:'Add monthly costs to see what credits still need to cover'}</span></div>`+
 `<p class="small">Fill in the monthly cost and which credit covers it. The Credits and Perks scouts hunt cover for the uncovered items first.</p>`+
 `<div class="stack-list">${st.items.map(r=>stackRow(r,st.credit_providers)).join('')}</div>`+
 `<form class="stack-form stack-row stack-add"><input name="item" maxlength="120" placeholder="Add something you pay for" aria-label="New item" required><input name="provider" maxlength="80" placeholder="Provider" aria-label="Provider"><input name="monthly_usd" type="number" min="0" step="0.01" placeholder="$/month" aria-label="Monthly cost"><select name="covered_by" aria-label="Covered by"><option value="">Not covered</option>${st.credit_providers.filter(Boolean).map(p=>`<option value="${E(p)}">${E(p)} credits</option>`).join('')}</select><button type="submit" class="primary">Add</button></form></section>`;
}
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.classList.contains('stack-form'))return;e.preventDefault();
 const body=Object.fromEntries(new FormData(f)),btn=f.querySelector('button[type=submit]');btn.disabled=true;
 try{await api('/api/stack-cost',{...(f.dataset.id?{id:f.dataset.id}:{}),...body});await boot();toast('Saved.');}catch(err){toast(err.message,true);}finally{btn.disabled=false;}
});
document.addEventListener('click',async e=>{
 const d=e.target.closest('[data-stack-delete]');if(!d)return;e.preventDefault();
 if(!confirm('Remove this item?'))return;d.disabled=true;
 try{await api('/api/stack-delete',{id:d.dataset.stackDelete});await boot();toast('Removed.');}catch(err){toast(err.message,true);d.disabled=false;}
});
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-scout-run]');if(!b)return;e.preventDefault();b.disabled=true;
 try{await api('/api/scout-run',{key:b.dataset.scoutRun});await boot();toast('Scout started. Results appear on its page in about 15 minutes.');}
 catch(err){toast(err.message,true);b.disabled=false;}
});
