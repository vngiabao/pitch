// ---------- Founder profile: the vault of facts only Bao knows; the Form Filler copies them into application answers (AGENT-SYSTEM.md) ----------
// Loaded before app.js; uses its helpers (E, api, heading, toast, boot, plural) at call time.
// Sensitive values never arrive with the page. They are fetched one at a time when Bao clicks Reveal.
const fpDay=v=>v?new Date(v).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'America/New_York'}):'';
const fpType=k=>/_url$|_link$|website$/.test(k)?'url':/_dob$|_date$/.test(k)?'date':'text';
function profileRow(f){
 const id='fp-'+f.key,state=f.set?(f.sensitive?`<span class="fp-masked" aria-label="Saved, hidden">${E(f.masked)}</span> <button type="button" class="link-button" data-profile-reveal="${E(f.key)}">Reveal</button>`:'<span class="small">Saved</span>'):'<span class="small muted">Not filled yet</span>';
 const input=f.sensitive?`<input id="${id}" name="value" type="text" autocomplete="off" spellcheck="false" placeholder="${f.set?'Hidden. Reveal to see it, or type a new value':'Type it once'}" maxlength="2000">`
  :`<input id="${id}" name="value" type="${fpType(f.key)}" value="${E(f.value||'')}" placeholder="${fpType(f.key)==='url'?'https://':''}" maxlength="2000"${fpType(f.key)==='date'?' max="2100-12-31"':''}>`;
 return `<form class="record fp-row profile-form" data-key="${E(f.key)}" data-sensitive="${f.sensitive?'1':''}"><div class="section-title"><h3><label for="${id}">${E(f.label)}</label></h3><span class="small">${state}${f.updated_at?' · '+E(fpDay(f.updated_at)):''}</span></div>`+
  `<p class="small muted fp-used">Used for: ${E(f.used_for)}${f.sensitive?' Masked here; never written to logs, reports or AI drafts.':''}</p>`+
  `<div class="actions">${input}<button class="primary" type="submit">Save</button>${f.set?`<button type="button" data-profile-clear="${E(f.key)}">Clear</button>`:''}${f.custom?`<button type="button" data-profile-delete="${E(f.key)}">Remove</button>`:''}</div></form>`;
}
function profileGroup(name,fields){
 const blurb={Company:'Legal identity lines. The EIN and street addresses stay masked.',Contact:'Who gets your number is your call; this only saves typing it.',Founders:'Only for forms that ask. Dates of birth are stored, never listed.',Links:'Public links the forms keep asking for. Leave one empty and that question stays with you.','Team and money':'Plain words work: "$0, bootstrapped" or "2 founders, no employees".',Other:'Anything a form asks that is not above. The filler matches a question whose label contains every word of yours.'}[name]||'';
 return `<section class="section" aria-labelledby="fp-${E(name.replace(/\W+/g,'-').toLowerCase())}"><div class="section-title"><h2 id="fp-${E(name.replace(/\W+/g,'-').toLowerCase())}">${E(name)}</h2><span class="small">${E(fields.filter(f=>f.set).length)} of ${E(fields.length)} filled</span></div><p class="small">${E(blurb)}</p>${fields.map(profileRow).join('')}${name==='Other'?addProfileField():''}</section>`;
}
function addProfileField(){
 return `<details class="more"><summary>Add another fact</summary><form class="profile-add-form"><div class="form-grid"><label>What the form calls it<input name="label" required maxlength="120" placeholder="e.g. Deepgram project ID"></label><label>Value<input name="value" required maxlength="2000"></label></div><label class="small"><input type="checkbox" name="sensitive" value="1"> Private: mask it on this page and keep it out of AI drafts</label><p class="small muted">Never bank account, routing or card numbers. Enter those on the official form yourself.</p><div class="actions"><button class="primary" type="submit">Save fact</button></div></form></details>`;
}
async function founderProfile(){
 const b=await api('/api/founder-profile'),byGroup=g=>b.fields.filter(f=>f.group===g);
 document.querySelector('#breadcrumbs').innerHTML='<a href="/">A Story</a> / Founder profile';document.title='Founder profile | A Story';
 app.innerHTML=heading('Founder profile','Facts only you know, written once. The Form Filler copies them into application answers, so "Needs you" shrinks to what truly needs you.')+
  `<p class="state-line"><span><strong>${E(b.filled)}</strong> of ${E(b.total)} filled</span><span>Every save re-runs the filler over the applications whose forms were read</span><span>Nothing is ever submitted for you</span></p>`+
  b.groups.map(g=>profileGroup(g,byGroup(g))).join('');
}
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.classList.contains('profile-form')&&!f.classList.contains('profile-add-form'))return;e.preventDefault();
 const body=Object.fromEntries(new FormData(f)),btn=f.querySelector('button[type=submit]');btn.disabled=true;
 try{
  let r;
  if(f.classList.contains('profile-form')){if(!String(body.value||'').trim()){toast('Type a value first, or use Clear to empty this field.',true);return;}r=await api('/api/founder-profile',{key:f.dataset.key,value:body.value});}
  else r=await api('/api/founder-profile',{label:body.label,value:body.value,sensitive:body.sensitive==='1'});
  await boot();toast(r.filled?'Saved. '+plural(r.filled,'application answer')+' filled from your profile.':'Saved.');
 }catch(err){toast(err.message,true);}finally{btn.disabled=false;}
});
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b||!(b.dataset.profileReveal||b.dataset.profileClear||b.dataset.profileDelete))return;
 b.disabled=true;
 try{
  if(b.dataset.profileReveal){const r=await api('/api/founder-profile-reveal',{key:b.dataset.profileReveal});const input=document.getElementById('fp-'+b.dataset.profileReveal);input.value=r.value;input.focus();b.replaceWith(Object.assign(document.createElement('span'),{className:'small',textContent:'Shown below until you leave this page'}));return;}
  if(b.dataset.profileClear){if(!confirm('Clear this saved value? Questions it answered keep their current answers until you change them.'))return;await api('/api/founder-profile',{key:b.dataset.profileClear,value:''});await boot();toast('Cleared.');return;}
  if(b.dataset.profileDelete){if(!confirm('Remove this fact from your profile?'))return;await api('/api/founder-profile-delete',{key:b.dataset.profileDelete});await boot();toast('Removed.');}
 }catch(err){toast(err.message,true);}finally{b.disabled=false;}
});
