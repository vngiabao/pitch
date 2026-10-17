// Scouts page: one specialized agent per kind of money or person, each with its schedule, last run and landing page.
const DAY_WORDS={MO:'Mon',TU:'Tue',WE:'Wed',TH:'Thu',FR:'Fri',SA:'Sat',SU:'Sun'};
function scheduleWords(s){
 if(!s||!s.days)return 'No schedule';
 if(s.days.length===7&&s.hour===8&&s.minute===30)return 'Weekly, for programs you are in';
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
 `<div class="actions">${s.key==='win'?`<a class="button" href="/opportunities">Open a program and press Research how to win</a>`:`<button type="button" data-scout-run="${E(s.key)}"${s.running?' disabled':''}>${s.running?'Running…':'Run now'}</button>`}</div></article>`;
}
async function scouts(){
 const r=await api('/api/scouts'),groups=[...new Set(r.scouts.map(s=>s.group))],b=r.broad_sweep;
 app.innerHTML=heading('Scouts','One agent per kind of money or person. Each one searches its own corner on its own day, and everything it finds waits for you.')+
 `<p class="state-line"><span><strong>${r.scouts.length}</strong> scouts</span><span><strong>${r.scouts.filter(s=>s.running).length}</strong> running now</span><span>Read-only. Nothing is applied to, sent or spent.</span></p>`+
 groups.map(g=>`<section aria-labelledby="g-${E(g.replace(/\W+/g,'-'))}"><div class="block-title"><h2 id="g-${E(g.replace(/\W+/g,'-'))}">${E(g)}</h2></div><div class="scout-grid">${r.scouts.filter(s=>s.group===g).map(scoutCard).join('')}</div></section>`).join('')+
 `<section class="section quiet"><div class="section-title"><div><h3>${E(b.name)}</h3><p class="small">${E(b.hunts)}</p></div><span class="credit-status">${b.running?'Running now':E(scheduleWords(b.schedule))}</span></div><p class="small">${E(lastRunWords(b.last_run))}. <a href="/activity">All research runs</a>.</p></section>`;
}
// Win Scout: how to win one program. Shown on the opportunity page; feeds Pitch Tailor, the Drafter and the Coach.
const APPLIES_WORDS={pitch:'In the pitch',application:'In the application',qa:'In Q&A',demo:'In the demo',materials:'In the materials'};
function winSection(w,id){
 if(!w)return '';
 const b=w.brief,btn=(label,primary)=>`<button type="button" class="${primary?'primary':''}" data-win-research="${E(id)}"${w.researching?' disabled':''}>${w.researching?'Researching…':label}</button>`;
 if(!b)return `<section class="section win-box"><div class="section-title"><h2>How we win here</h2><span class="small">Win Scout</span></div><p class="small">Win Scout reads the rules, the judges, past winners and this cycle’s other companies, then says what wins here. Pitch Tailor, the Drafter and the Coach use it for this program.</p><div class="actions">${btn('Research how to win',true)}</div>${w.researching?'<p class="small">Results land here in about 15 minutes.</p>':''}</section>`;
 const r=b.rules,rules=[['Format',r.format],['Time',r.time_limit],['Slides',r.slide_limit],['Q&A',r.qa],['Audience',r.audience],['Where',r.where],['Event',r.event_date]].filter(x=>x[1]&&!/not published/i.test(x[1]));
 const byApply=APPLIES_WORDS;const groups=Object.keys(byApply).map(k=>[k,b.how_we_win.filter(m=>m.applies_to===k)]).filter(x=>x[1].length);
 return `<section class="section win-box"><div class="section-title"><h2>How we win here</h2><span class="small">Win Scout · checked ${E(readableDate(w.checked_at))}${w.runs>1?` · ${w.runs} checks`:''}</span></div>`+
 (w.changes.length&&!w.seen?`<div class="notice win-changes"><strong>Changed since last time</strong><ul>${w.changes.map(c=>`<li>${E(c)}</li>`).join('')}</ul><button type="button" class="link-button" data-win-seen="${E(id)}">Got it</button></div>`:'')+
 (groups.length?`<div class="win-moves">${groups.map(([k,ms])=>`<h3 class="list-head">${E(byApply[k])}</h3><ol>${ms.map(m=>`<li><strong>${E(m.move)}</strong><p class="small">${E(m.why)}</p></li>`).join('')}</ol>`).join('')}</div>`:'<p class="small">No specific moves found; the program publishes little.</p>')+
 (b.unstated.length?`<h3 class="list-head">What nobody writes down</h3><ul>${b.unstated.map(u=>`<li>${E(u.insight)}${u.evidence?` <span class="small muted">(${E(u.evidence)})</span>`:''}</li>`).join('')}</ul>`:'')+
 (b.criteria.length?`<h3 class="list-head">What judges score</h3><div class="win-criteria">${b.criteria.map(c=>`<span class="count-chip" title="${E(c.evidence)}">${E(c.name)}${c.weight&&!/not published/i.test(c.weight)?' · '+E(c.weight):''}</span>`).join('')}</div>`:'')+
 (rules.length?`<dl class="fact-list">${rules.map(([k,v])=>`<div><dt>${E(k)}</dt><dd>${E(v)}</dd></div>`).join('')}</dl>`:'')+
 (b.judges.length?`<details class="more"><summary>Judges (${b.judges.length})</summary><ul>${b.judges.map(j=>`<li><strong>${E(j.name)}</strong>${j.role?', '+E(j.role):''}${j.cares_about?`<p class="small">${E(j.cares_about)}</p>`:''}${j.source_url?` <a class="small" href="${E(j.source_url)}" target="_blank" rel="noopener noreferrer">Source ↗</a>`:''}</li>`).join('')}</ul></details>`:'')+
 (b.competitors.length?`<details class="more"><summary>Other companies this cycle (${b.competitors.length})</summary><ul>${b.competitors.map(c=>`<li><strong>${E(c.name)}</strong>${c.stage?' · '+E(c.stage):''}<p class="small">${E(c.what_they_do)}${c.strength?' Strength: '+E(c.strength):''}</p>${c.source_url?`<a class="small" href="${E(c.source_url)}" target="_blank" rel="noopener noreferrer">Source ↗</a>`:''}</li>`).join('')}</ul></details>`:'')+
 (b.past_winners.length?`<details class="more"><summary>Past winners (${b.past_winners.length})</summary><ul>${b.past_winners.map(x=>`<li><strong>${E(x.year)} ${E(x.company)}</strong><p class="small">${E(x.what_they_did)} ${E(x.why_it_won)}</p>${x.source_url?`<a class="small" href="${E(x.source_url)}" target="_blank" rel="noopener noreferrer">Source ↗</a>`:''}</li>`).join('')}</ul></details>`:'')+
 (b.risks.length||b.open_questions.length?`<details class="more"><summary>Risks and open questions</summary>${b.risks.length?`<ul>${b.risks.map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:''}${b.open_questions.length?`<p class="small">Only you can answer:</p><ul>${b.open_questions.map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:''}</details>`:'')+
 `<div class="actions">${btn('Research again',false)}</div>${b.sources.length?`<p class="small">${b.sources.slice(0,6).map(u=>`<a href="${E(u)}" target="_blank" rel="noopener noreferrer">${E(u.replace(/^https?:\/\//,'').slice(0,48))} ↗</a>`).join(' · ')}</p>`:''}</section>`;
}
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-win-research],[data-win-seen]');if(!b)return;e.preventDefault();b.disabled=true;
 try{
  if(b.dataset.winResearch){await api('/api/win-research',{opportunity_id:b.dataset.winResearch});await boot();toast('Win Scout started. The brief lands on this page in about 15 minutes.');}
  else{await api('/api/win-seen',{opportunity_id:b.dataset.winSeen});await boot();}
 }catch(err){toast(err.message,true);b.disabled=false;}
});
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
