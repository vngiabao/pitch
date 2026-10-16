// ---------- Product desk: the beta family journal, retention numbers and read-only metrics intake (AGENT-SYSTEM.md) ----------
// Loaded before app.js; uses its helpers (E, api, heading, toast, boot, plural) at call time.
const pdDay=v=>v?new Date(String(v).slice(0,10)+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'';
const pdRange=r=>!r||!r.start?'no dates yet':r.start===r.end?pdDay(r.start):pdDay(r.start)+' - '+pdDay(r.end);
const pdToday=()=>new Date().toLocaleDateString('en-CA',{timeZone:'America/New_York'});
const pdValue=p=>p.unit==='count'?String(Math.round(p.value)):p.unit==='percent'?p.value+'%':new Intl.NumberFormat('en-US',{style:'currency',currency:p.unit.length===3?p.unit.toUpperCase():'USD',maximumFractionDigits:2}).format(p.value);
const pdNeeds={second_call_rate:'families with a first call',relatives_contributing:'families with a first call',calls_after_contribution:'a family where a relative contributed'};
function measuredList(r){
 return `<dl class="fact-list">${r.metrics.map(m=>`<div><dt>${E(m.label)}</dt><dd>${m.measurable?`<strong>${E(m.numerator)} of ${E(m.denominator)}</strong> ${E(m.denominator_label)} (${E(m.percent)}%)${m.calls!==undefined?`, ${plural(m.calls,'call')} in all`:''}<br><small>${E(pdRange(m.range))} · ${E(m.sources.join(' and '))} entries</small>`:`<span class="muted">Not measurable yet. Needs ${E(pdNeeds[m.key])}.</span>`}</dd></div>`).join('')}</dl>`;
}
function familyCard(f,kinds,states){
 const facts=[f.storyteller?'Storyteller: '+f.storyteller:'',f.adult_child?'Adult child: '+f.adult_child:'',f.enrolled_on?'Enrolled '+pdDay(f.enrolled_on):'Enrolled date not set',plural(f.events.length,'event')].filter(Boolean).join(' · ');
 const events=f.events.length?`<ul class="small family-events">${f.events.map(e=>`<li>${E(pdDay(e.at))} · <strong>${E(e.kind_words)}</strong>${e.detail?' · '+E(e.detail):''}${e.source==='import'?' · imported':''} <button type="button" class="link-button" data-event-delete="${E(e.id)}">Remove</button></li>`).join('')}</ul>`:'<p class="small muted">No events yet. Log the first call when it happens.</p>';
 return `<article class="record" id="family-${E(f.id)}"><div class="section-title"><h3>${E(f.label)}</h3><label class="small">Status <select data-family-status="${E(f.id)}" aria-label="Status of ${E(f.label)}">${states.map(([v,l])=>`<option value="${E(v)}"${v===f.status?' selected':''}>${E(l)}</option>`).join('')}</select></label></div>`+
  `<p class="small">${E(facts)}</p>${f.notes?`<p class="small">${E(f.notes)}</p>`:''}${events}`+
  `<details class="more"><summary>Log an event</summary><form class="event-form" data-id="${E(f.id)}"><div class="form-grid"><label>What happened<select name="kind">${kinds.map(([v,l])=>`<option value="${E(v)}">${E(l)}</option>`).join('')}</select></label><label>Day<input type="date" name="at" required value="${pdToday()}" max="${pdToday()}"></label></div><label>Detail (optional)<input name="detail" maxlength="1000" placeholder="e.g. Grandma talked for 40 minutes about the move from Hue"></label><div class="actions"><button class="primary" type="submit">Log it</button></div></form></details></article>`;
}
function addFamilyForm(open,states){
 return `<details class="more"${open?' open':''}><summary>Add a family</summary><form class="family-form"><div class="form-grid"><label>Family name or label<input name="label" required maxlength="120" placeholder="e.g. The Tran family"></label><label>Storyteller<input name="storyteller" maxlength="120" placeholder="Who is interviewed"></label><label>Adult child<input name="adult_child" maxlength="120" placeholder="Who signed them up"></label><label>Enrolled on<input type="date" name="enrolled_on" max="${pdToday()}"></label><label>Status<select name="status">${states.map(([v,l])=>`<option value="${E(v)}">${E(l)}</option>`).join('')}</select></label></div><label>Notes<textarea name="notes" maxlength="2000"></textarea></label><div class="actions"><button class="primary" type="submit">Add family</button></div></form></details>`;
}
function intakeSection(i){
 const files=i.files.length?i.files.map(f=>`<div class="record"><strong>${E(f.name)}</strong> <span class="small">${E(Math.max(1,Math.round(f.size/1024)))} KB · ${E(pdDay(f.modified))}</span>${f.imported?`<p class="small">Imported ${E(pdDay(f.imported.imported_at))} as ${E(i.providers[f.imported.provider]||f.imported.provider)}.</p>`:`<form class="import-form" data-file="${E(f.name)}"><div class="form-grid"><label>Export from<select name="provider">${Object.entries(i.providers).map(([v,l])=>`<option value="${E(v)}">${E(l)}</option>`).join('')}</select></label><label>Note (optional)<input name="note" maxlength="500"></label></div><div class="actions"><button type="submit">Import this file</button></div></form>`}</div>`).join(''):`<p class="small muted">No exports waiting. Save a CSV from App Store Connect, Stripe or RevenueCat into the folder above, then reload.</p>`;
 const sources=i.sources.length?`<div class="table-scroll"><table><thead><tr><th>Export</th><th>File</th><th>Covers</th><th>Numbers</th><th>Imported</th></tr></thead><tbody>${i.sources.map(s=>`<tr><td>${E(i.providers[s.provider]||s.provider)}</td><td>${E(s.file_name)}</td><td>${E(pdRange({start:s.period_start,end:s.period_end}))}</td><td>${E(s.point_count)}</td><td>${E(pdDay(s.imported_at))}</td></tr>`).join('')}</tbody></table></div>`:'';
 const latest=i.latest.length?`<h3 class="list-head">Latest value of every imported metric</h3><div class="table-scroll"><table><thead><tr><th>Source</th><th>Metric</th><th>Day</th><th>Value</th><th>From</th></tr></thead><tbody>${i.latest.map(p=>`<tr><td>${E(i.providers[p.provider]||p.provider)}</td><td>${E(p.metric.replaceAll('_',' '))}</td><td>${E(pdDay(p.period))}</td><td>${E(pdValue(p))}</td><td class="small">${E(p.file_name)}</td></tr>`).join('')}</tbody></table></div>`:'';
 const keys=i.api.filter(a=>a.credential_present).map(a=>a.name);
 return `<section class="section" id="intake"><div class="section-title"><h2>Metrics intake</h2><span class="small">Read-only</span></div><p class="small">Save a CSV export from App Store Connect, Stripe or RevenueCat into <span class="source-path">${E(i.inbox)}</span> and import it here. Every number keeps its file, the file’s fingerprint and its day. Nothing is sent anywhere.</p>${files}${sources}${latest}`+
  `<p class="small">API pulls are not switched on. When they are, each key lives only in Windows Credential Manager under <span class="source-path">AStoryFounderOS:Metrics:&lt;provider&gt;</span>; ${keys.length?'a key is stored for '+E(keys.join(' and '))+'.':'no key is stored yet.'}</p></section>`;
}
async function betaFamilies(){
 const b=await api('/api/product'),c=b.counts,r=b.retention;
 app.innerHTML=heading('Beta families','What the beta families actually do, counted from this journal. These numbers reach Fact Guard as measured, with their denominators.')+
  `<p class="state-line"><span><strong>${c.families}</strong> families</span><span><strong>${c.first_calls}</strong> had a first call</span><span><strong>${c.second_calls}</strong> had a second call</span><span><strong>${c.contributing}</strong> with a relative contributing</span>${c.issues?`<span class="urgent"><strong>${c.issues}</strong> issues logged</span>`:''}</p>`+
  `<section class="section" aria-labelledby="measured-title"><div class="section-title"><h2 id="measured-title">Measured so far</h2><span class="small">${r.as_of?'As of '+E(pdDay(r.as_of)):'Nothing measured yet'}</span></div>${measuredList(r)}<p class="small">Fact Guard treats these as measured facts, labelled with the as-of date, ahead of owner-reported numbers. A rate with no denominator stays empty rather than showing zero.</p></section>`+
  `<section class="section" aria-labelledby="families-title"><div class="section-title"><h2 id="families-title">The journal</h2><span class="small">Enter each family yourself; nothing here is invented</span></div>${addFamilyForm(!b.families.length,b.family_states)}${b.families.map(f=>familyCard(f,b.event_kinds,b.family_states)).join('')||'<p class="small muted">No families yet. Add the first one above.</p>'}</section>`+
  intakeSection(b.intake);
}
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.classList.contains('family-form')&&!f.classList.contains('event-form')&&!f.classList.contains('import-form'))return;e.preventDefault();
 const body=Object.fromEntries(new FormData(f)),btn=f.querySelector('button[type=submit]');btn.disabled=true;
 try{
  if(f.classList.contains('family-form')){await api('/api/family',body);toast('Family added. Log its first call when it happens.');}
  else if(f.classList.contains('event-form')){await api('/api/family-event',{family_id:f.dataset.id,...body});toast('Logged. The measured numbers above are updated.');}
  else{const r=await api('/api/metrics-import',{file:f.dataset.file,...body});toast(`Imported ${plural(r.point_count,'number')} from ${r.file_name}.`);}
  await boot();
 }catch(err){toast(err.message,true);}finally{btn.disabled=false;}
});
document.addEventListener('change',async e=>{
 const s=e.target.closest('[data-family-status]');if(!s)return;s.disabled=true;
 try{await api('/api/family-update',{id:s.dataset.familyStatus,status:s.value});await boot();toast('Status saved.');}catch(err){toast(err.message,true);s.disabled=false;}
});
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-event-delete]');if(!b)return;e.preventDefault();
 if(!confirm('Remove this event from the journal? The measured numbers change with it.'))return;b.disabled=true;
 try{await api('/api/family-event-delete',{id:b.dataset.eventDelete});await boot();toast('Event removed.');}catch(err){toast(err.message,true);b.disabled=false;}
});
