// ---------- Reservation drive: the $1 reservation push to leads and beta families before November 2 (AGENT-SYSTEM.md) ----------
// Loaded before app.js; uses its helpers (E, api, heading, toast, boot, plural, fmtDay, draftBlock) at call time. Bao sends every note himself.
const DRIVE_CSV_HELP='A header row, then one person per line: name, email, context, kind. Kind is Lead or Beta family (empty means Lead). Context is how you know them, in a sentence; the drafter picks it up.';
function driveLoaderForm(){
 return `<form class="drive-import-form"><label>Your CSV file<input type="file" name="file" accept=".csv,text/csv"></label><label>Or paste the rows<textarea name="csv" rows="5" maxlength="60000" placeholder="name,email,context,kind&#10;Linh Pham,linh@example.com,Signed up after the Columbus demo night,Lead&#10;The Tran family,tran@example.com,Beta since September; grandma talked about Hue,Beta family"></textarea></label><p class="small">${E(DRIVE_CSV_HELP)} Someone already in People with the same email is enrolled, not copied; a repeated email is skipped.</p><div class="actions"><button class="primary" type="submit">Load these people</button></div></form>`;
}
function driveLoaderCard(){
 return `<details class="more add-person" id="drive-loader"><summary>Load leads and beta families for the reservation drive</summary><p class="small">Each person is tagged <code>reservation-2026</code> and the drafter writes their note, one per cycle. Watch the drive at <a href="/drive">Reservation drive</a>.</p>${driveLoaderForm()}</details>`;
}
function driveMemberCard(m){
 const last=m.touches[0],mail=m.email?`<a class="button" href="mailto:${E(m.email)}${m.draft&&m.draft.title?'?subject='+encodeURIComponent(m.draft.title):''}">Open email ↗</a>`:'';
 const outcome=`<button type="button" data-drive-action="reserved" data-id="${E(m.contact_id)}">They reserved</button><button type="button" data-drive-action="referred" data-id="${E(m.contact_id)}">They referred someone</button>`;
 let body='';
 if(m.shown==='NEW')body=`<p class="qa-needs">${m.drafting?'<strong>Drafting.</strong> The agent is writing this note now.':`<strong>Not yet written.</strong> The agent writes one note per cycle. <button class="link-button" type="button" data-growth-draft="contact" data-id="${E(m.contact_id)}">Draft it now</button>`}</p>`;
 else if(m.shown==='READY')body=draftBlock(m.draft)+`<div class="actions"><button class="primary" type="button" data-drive-action="sent" data-id="${E(m.contact_id)}">I sent it</button>${mail}<button class="link-button" type="button" data-growth-draft="contact" data-id="${E(m.contact_id)}">Write a new draft</button></div>`;
 else if(m.shown==='SENT')body=(m.draft?draftBlock(m.draft)+'<p class="small">A reminder is drafted. Send it only if they have not answered.</p>':'')+`<div class="actions"><button class="primary" type="button" data-drive-action="replied" data-id="${E(m.contact_id)}">They replied</button>${outcome}${m.draft?`<button type="button" data-drive-action="sent" data-id="${E(m.contact_id)}">I sent the reminder</button>`:''}</div>`;
 else if(m.shown==='REPLIED')body=`<div class="actions">${outcome}</div>`;
 else body=`<div class="actions"><button type="button" data-drive-action="referred" data-id="${E(m.contact_id)}">They referred someone</button></div>`;
 return `<article class="section person-card drive-${E(m.shown.toLowerCase())}" id="drive-${E(m.contact_id)}"><div class="section-title"><div><h3>${E(m.name)}</h3><p class="small">${E(m.kind_words)}${m.email?' · '+E(m.email):''}${m.referrals?' · '+E(plural(m.referrals,'referral')):''}</p></div><span class="credit-status${m.shown==='READY'?' due':''}">${E(m.state_words)}${m.reserved_on?' '+E(fmtDay(m.reserved_on)):m.sent_on&&m.shown==='SENT'?' '+E(fmtDay(m.sent_on)):''}</span></div>`+
  (m.context?`<p class="small">${E(m.context)}</p>`:'')+(last?`<p class="small">Last: ${E(fmtDay(last.occurred_on))}, ${E(last.summary)}</p>`:'')+body+`</article>`;
}
async function reservationDrive(){
 const b=await api('/api/drive'),c=b.counts,left=b.days_left;
 const when=left>0?`<strong>${left}</strong> ${left===1?'day':'days'} to November 2`:left===0?'<strong>Closes today</strong>':'<strong>Closed</strong> November 2';
 const groups=[['READY','Ready to send','Copy the note, send it from your own email, then press "I sent it".'],['SENT','Sent, waiting','Record what happens: a reply, a reservation, a referral.'],['REPLIED','They replied','Answer them from your email; record a reservation or a referral here.'],['NEW','Still being written','The Follow-up drafter writes one note per cycle, then Fact Guard and Bao’s Voice check it.'],['RESERVED','Reserved','Each one is a $1 reservation, counted as a purchase for the email channel.']];
 app.innerHTML=heading('Reservation drive','Your leads and beta families, one personal note each, before the $1 reservation closes on November 2. You send every note yourself.')+
  `<p class="state-line"><span>${when}</span><span><strong>${c.total}</strong> people (${plural(c.leads,'lead')}, ${plural(c.beta,'beta family','beta families')})</span><span><strong>${c.not_written}</strong> not yet written</span><span class="${c.ready?'urgent':''}"><strong>${c.ready}</strong> ready to send</span><span><strong>${c.sent}</strong> sent</span><span><strong>${c.replied}</strong> replied</span><span><strong>${c.reserved}</strong> reserved</span><span><strong>${c.referrals}</strong> referrals</span></p>`+
  `<details class="more add-person"${c.total?'':' open'}><summary>Load leads and beta families</summary>${driveLoaderForm()}</details>`+
  (c.total?groups.map(([key,title,note])=>{const list=b.members.filter(m=>m.shown===key);return list.length?`<section aria-labelledby="drive-${key}"><div class="block-title"><h2 id="drive-${key}">${E(title)} (${list.length})</h2></div><p class="block-note">${E(note)}</p>${list.map(driveMemberCard).join('')}</section>`:'';}).join(''):'<div class="all-clear"><h2>No one loaded yet</h2><p class="small">Load your CSV above. Nothing is invented: only the people in your file are written to.</p></div>')+
  (b.entries.length?`<section class="section"><div class="section-title"><h2>What channel math sees</h2><a href="/growth#channels">Channel math</a></div><ul class="deal-log">${b.entries.map(e=>`<li class="small">${E(new Date(e.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'America/New_York'}))} · ${E(e.channel==='referrals'?'Referrals':'Email')} · ${e.purchases?'1 purchase ($1)':'1 signup'} · ${E(e.note||'')}</li>`).join('')}</ul></section>`:'')+
  `<p class="small">Today reminds you how many notes are still unsent on ${b.nudge_days.map(d=>E(fmtDay(d))).join(', ')}.</p>`;
}
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.classList.contains('drive-import-form'))return;e.preventDefault();
 const btn=f.querySelector('button[type=submit]'),file=f.querySelector('input[type=file]').files[0];btn.disabled=true;
 try{
  let csv=f.querySelector('textarea').value;
  if(file){if(file.size>60000)throw new Error('That file is larger than 60 KB. Split it into two.');csv=await file.text();}
  const r=await api('/api/drive-import',{csv});
  const bits=[r.created?plural(r.created,'new person','new people'):'',r.enrolled?plural(r.enrolled,'known contact')+' enrolled':'',r.skipped?plural(r.skipped,'duplicate')+' skipped':'',r.rejected.length?plural(r.rejected.length,'row')+' rejected ('+r.rejected.slice(0,3).map(x=>'row '+x.row+': '+x.reason).join('; ')+')':''].filter(Boolean);
  toast(bits.length?bits.join(', ')+'.':'Nothing to load.',Boolean(r.rejected.length&&!r.created&&!r.enrolled));
  if(location.pathname!=='/drive'&&(r.created||r.enrolled)){location.href='/drive';return;}
  await boot();
 }catch(err){toast(err.message,true);}finally{btn.disabled=false;}
});
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-drive-action]');if(!b)return;e.preventDefault();
 const action=b.dataset.action||b.dataset.driveAction,id=b.dataset.id,body={id,action};
 const ask={sent:'Log that you sent this note from your own email?',replied:'Log that they replied?',reserved:'Record that they reserved A Story for $1? This adds one purchase to the email channel this week.'}[action];
 if(action==='referred'){const who=prompt('Who did they refer? Leave empty if you do not know yet.');if(who===null)return;body.who=who;}
 else if(!confirm(ask))return;
 b.disabled=true;
 try{await api('/api/drive-action',body);await boot();toast({sent:'Logged. Record the reply or the reservation when it comes.',replied:'Logged. Answer them from your email.',reserved:'Reservation recorded. Channel math has it.',referred:'Referral recorded under the referrals channel. Add the new family in People when you have their details.'}[action]);}
 catch(err){toast(err.message,true);b.disabled=false;}
});
