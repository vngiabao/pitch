// ---------- Assumption Coach: every number the deck depends on, what it rests on today, and this week's three cheapest tests (AGENT-SYSTEM.md) ----------
// Loaded before app.js; uses its helpers (E, api, heading, toast, boot, plural, tag) at call time.
const acDay=v=>v?new Date(String(v).slice(0,10)+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'';
const acStatusTag=s=>`<span class="tag ${s==='measured'?'good':s==='modeled'?'':'review'}">${E({assumed:'Assumed',modeled:'Modeled',measured:'Measured'}[s]||s)}</span>`;
const acLines=xs=>xs&&xs.length?`<ul class="small">${xs.map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:'<p class="small muted">Nothing recorded.</p>';
function acMeasured(a){
 const m=a.measured;if(!m)return '';
 const fact=m.fact?`<p class="small"><strong>Measured:</strong> ${E(m.fact.text)}</p>`:'';
 const ev=(m.evidence||[]).length?`<p class="small"><strong>Measured nearby:</strong> ${m.evidence.map(e=>E(e.text)).join(' ')}</p>`:'';
 return fact+ev;
}
function acCard(a,titles){
 const slides=a.slides.map(s=>titles[s]?`${E(titles[s])} (${E(s)})`:E(s)).join(' · ');
 const changed=a.status_changed_at?`<p class="small muted">Status changed ${E(acDay(a.status_changed_at))}${a.status==='measured'?' when the measured number arrived':' when its measured entries were removed'}.</p>`:'';
 const statusField=a.status==='measured'?'<p class="small muted">Measured by the data; the status follows the entries.</p>':`<label>Status<select name="status"><option value="assumed"${a.status==='assumed'?' selected':''}>Assumed</option><option value="modeled"${a.status==='modeled'?' selected':''}>Modeled</option></select></label>`;
 return `<article class="record" id="assumption-${E(a.key)}"><div class="section-title"><h3>${E(a.statement)}</h3>${acStatusTag(a.status)}</div>`+
  `<p class="small"><strong>${E(a.number)}</strong> · On: ${slides||'no slide'}</p>${acMeasured(a)}${changed}`+
  `<div class="detail-grid"><div><h4>For</h4>${acLines(a.evidence_for)}</div><div><h4>Against</h4>${acLines(a.evidence_against)}</div></div>`+
  `<p><strong>Cheapest test:</strong> ${E(a.cheapest_test)}</p>${a.owner_note?`<p class="small qa-note"><strong>Your note:</strong> ${E(a.owner_note)}</p>`:''}`+
  `<details class="more"><summary>Edit</summary><form class="assumption-form" data-key="${E(a.key)}"><div class="form-grid"><label>Evidence for (one per line)<textarea name="evidence_for" maxlength="3000">${E(a.evidence_for.join('\n'))}</textarea></label><label>Evidence against (one per line)<textarea name="evidence_against" maxlength="3000">${E(a.evidence_against.join('\n'))}</textarea></label></div>`+
  `<label>Cheapest test<input name="cheapest_test" maxlength="600" value="${E(a.cheapest_test)}"></label><label>Your note<textarea name="owner_note" maxlength="1000">${E(a.owner_note)}</textarea></label>${statusField}<div class="actions"><button class="primary" type="submit">Save</button></div></form></details></article>`;
}
function acChallenge(c,b){
 const btn=`<button class="primary" data-action="assumption-challenge"${b.researching?' disabled':''}>${b.researching?'Coach is working…':'Challenge now'}</button>`;
 if(!c)return `<section class="section" aria-labelledby="challenge-title"><div class="section-title"><h2 id="challenge-title">This week’s three weakest</h2>${btn}</div><p class="small muted">No challenge yet. ${E(b.next_challenge)}${b.researching?' One is running now; it lands here in a few minutes.':''}</p></section>`;
 return `<section class="section" aria-labelledby="challenge-title"><div class="section-title"><h2 id="challenge-title">This week’s three weakest</h2>${btn}</div>`+
  `<p class="small">Pitch Coach, ${E(acDay(c.created_at))}, reading ${E(c.edition_title||'the core deck')}${c.measured.length?` and ${plural(c.measured.length,'measured number')}`:' with nothing measured yet'}. ${E(b.next_challenge)}</p>`+
  `<ol class="plan-list">${c.weakest.map(w=>`<li class="record"><div class="section-title"><h3>${E(w.statement)}</h3>${acStatusTag(w.status)}</div><p><strong>Why it is weak.</strong> ${E(w.why_weak)}</p><p><strong>Cheapest test this week.</strong> ${E(w.cheapest_test)}</p><p class="small"><strong>A judge would ask:</strong> “${E(w.judge_question)}”</p><p class="small"><a href="#assumption-${E(w.key)}">The full row</a></p></li>`).join('')}</ol>`+
  `${c.note?`<p class="small">${E(c.note)}</p>`:''}${c.rejected.length?`<details class="more small"><summary>${plural(c.rejected.length,'item')} Fact Guard set aside</summary><ul>${c.rejected.map(r=>`<li>${E(r.key||'(no key)')}: ${E(r.reason)}</li>`).join('')}</ul></details>`:''}</section>`;
}
// Today: one short block for a new challenge or a status flip, so the line is never cut by the Do next limit.
function assumptionLine(alerts){
 const mine=(alerts||[]).filter(x=>x.url==='/assumptions');if(!mine.length)return '';
 return `<section class="section" aria-labelledby="assumption-line-title"><div class="section-title"><h2 id="assumption-line-title">Assumptions</h2><a href="/assumptions">Open</a></div><ul class="small">${mine.map(x=>`<li><strong>${E(x.title)}</strong> ${E(x.detail)}</li>`).join('')}</ul></section>`;
}
async function assumptionsPage(){
 const b=await api('/api/assumptions'),c=b.counts,t=b.slide_titles;
 const groups=[['measured','Measured','From channel math and the beta family journal, with the dates they cover. These may be said as they are.'],['modeled','Modeled','Built from pricing and published inputs. Say “modeled”, never “we see”.'],['assumed','Assumed','Example inputs and beliefs. Say “an assumption we are testing”; the cheapest test says how.']];
 app.innerHTML=heading('Assumptions','Every number the deck depends on, what each rests on today, and the cheapest test for it.')+
  `<p class="state-line"><span><strong>${c.measured}</strong> measured</span><span><strong>${c.modeled}</strong> modeled</span><span class="${c.assumed?'urgent':''}"><strong>${c.assumed}</strong> assumed</span></p>`+
  acChallenge(b.challenge,b)+
  groups.map(([s,label,note])=>{const rows=b.assumptions.filter(a=>a.status===s);return `<section class="section" aria-labelledby="group-${s}"><div class="section-title"><h2 id="group-${s}">${E(label)}</h2><span class="small">${plural(rows.length,'assumption')}</span></div><p class="small">${E(note)}</p>${rows.map(a=>acCard(a,t)).join('')||'<p class="small muted">None yet.</p>'}</section>`;}).join('')+
  `<section class="section"><h2>How this works</h2><p class="small">The rows come from the core deck’s own notes. A measured number from channel math or the family journal flips a row to measured on its own, with its as-of date; if those entries are removed the row goes back to what the deck said. Your edits are kept as yours. Pitch Tailor and Pitch Coach read this table on every run so a script says “modeled” or “measured” correctly, and the Coach asks about the weakest rows first. Every Monday at 7:30 AM Eastern the Coach names the three weakest and the one cheapest test for each; it may not use a number that is not on this page.</p></section>`;
 api('/api/assumptions-seen',{}).catch(()=>{});
}
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.classList.contains('assumption-form'))return;e.preventDefault();
 const body=Object.fromEntries(new FormData(f)),btn=f.querySelector('button[type=submit]');btn.disabled=true;
 try{await api('/api/assumption',{key:f.dataset.key,...body});toast('Saved. The agents read this on their next run.');await boot();}catch(err){toast(err.message,true);}finally{btn.disabled=false;}
});
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-action="assumption-challenge"]');if(!b)return;e.preventDefault();b.disabled=true;
 try{await api('/api/assumption-challenge',{});toast('Asked the Coach. The three weakest assumptions land here in a few minutes.');await boot();}catch(err){toast(err.message,true);b.disabled=false;}
});
