let pitchCurrent=null,pitchDirty=false,pitchChoices=null,pitchSource=null,pitchClock=null,pitchElapsed=0,pitchStarted=0;
const pitchLength=s=>Number.isFinite(s)?s<60?Math.round(s)+' sec':Math.floor(s/60)+' min'+(s%60?' '+Math.round(s%60)+' sec':''):'Choose a length';
const pitchState=s=>({draft:'Draft',rehearsal_ready:'Ready for rehearsal',archived:'Archived'}[s]||s);
const pitchOptions=(values,chosen,all='')=>(all?'<option value="">'+E(all)+'</option>':'')+values.map(v=>`<option value="${E(v)}" ${String(v)===String(chosen)?'selected':''}>${E(v)}</option>`).join('');
function pitchStop(){if(pitchClock)clearInterval(pitchClock);pitchClock=null;}
window.addEventListener('beforeunload',e=>{if(pitchDirty){e.preventDefault();e.returnValue='';}});

async function pitchLibrary(){
 pitchStop();pitchCurrent=null;pitchDirty=false;
 const q=new URLSearchParams(location.search);try{sessionStorage.setItem('astory-pitch-library',location.pathname+location.search);}catch{}pitchChoices=await api('/api/pitches?'+q);
 if(q.get('material'))pitchSource=await api('/api/material/'+encodeURIComponent(q.get('material')));else pitchSource=null;
 const items=pitchChoices.items;
 app.innerHTML=heading('Pitch Studio','Choose who you’re talking to and how much time you have.','<button class="primary" data-pitch-action="new">Write a new pitch</button>')+
 `<section id="pitch-new" class="section" ${pitchSource?'':'hidden'}><h2>Start a pitch</h2><p class="small">${pitchSource?'Adapt this source as a working draft. Its original stays untouched.':'Write a new script, or duplicate a saved pitch to adapt it.'}</p>
 <form id="pitch-new-form"><div class="pitch-fields"><label>Title<input name="title" required maxlength="160" value="${E(pitchSource?'Adaptation of '+pitchSource.relative_path.split(/[\\/]/).at(-1):'')}" placeholder="e.g. A Story - investor introduction"></label><label>Length (minutes)<input name="duration_minutes" type="number" min="0.17" max="120" step="any" value="1" required></label><label>Audience<input name="audience" list="pitch-audiences" value="General" required maxlength="100"></label><label>Scenario<input name="scenario" list="pitch-scenarios" value="Quick introduction" required maxlength="100"></label></div>
 <label class="pitch-label">Pitch text<textarea name="body" class="pitch-text" required maxlength="40000" rows="10" placeholder="Start with the problem, explain A Story, and end with the next step.">${E(pitchSource?.body?.slice(0,40000)||'')}</textarea></label>
 ${pitchSource?`<p class="small source-path">Source: ${E(pitchSource.source_path)}${(pitchSource.body?.length||0)>40000?' - first 40,000 characters only; full source remains in Materials.':''}${!pitchSource.body?' - text unavailable; use the original as a reference.':''}</p>`:''}
 <div class="actions"><button class="primary" type="submit">Create draft</button><button type="button" data-pitch-action="cancel-new">Cancel</button></div></form></section>`+
 `<section class="section"><form id="pitch-filters" class="filters"><label>Search pitches<input name="q" value="${E(q.get('q'))}" placeholder="Title or wording"></label><label>Length<select name="duration"><option value="">Any length</option>${pitchChoices.lengths.map(s=>`<option value="${s}" ${q.get('duration')===String(s)?'selected':''}>${E(pitchLength(s))}</option>`).join('')}</select></label><label>Audience<select name="audience">${pitchOptions(pitchChoices.audiences,q.get('audience'),'Any audience')}</select></label><label>Scenario<select name="scenario">${pitchOptions(pitchChoices.scenarios,q.get('scenario'),'Any scenario')}</select></label><label>Collection<select name="archived"><option value="">Active drafts</option><option value="yes" ${q.get('archived')==='yes'?'selected':''}>Include archived</option></select></label><button type="submit">Find pitches</button><a href="/pitches">Clear</a></form>
 <div class="section-title"><h2>Your pitch library</h2><a href="/materials">Find source materials</a></div><p class="small">${items.length} pitches to work from. Timing is an estimate at 130 words per minute. Session plans include a demonstration or discussion.</p>
 ${items.map(p=>`<div class="record pitch-library-row"><div><a class="program-name" href="/pitch/${E(p.pitch_id)}">${E(p.title)}</a><p class="small">${E(p.audience)} · ${E(p.scenario)}</p><p class="pitch-preview">${E(p.preview)}${p.word_count>40?'…':''}</p></div><div class="pitch-row-meta"><strong>${E(pitchLength(p.duration_seconds))}</strong><p class="small">${p.word_count} words<br>About ${E(pitchLength(p.estimated_seconds))} of text</p>${tag(pitchState(p.status))}${p.format==='outline'?'<p class="small">Session plan</p>':''}${p.placeholders.length?`<p class="small">${p.placeholders.length} open prompts</p>`:''}</div></div>`).join('')||'<p class="empty">No pitches match these choices. Clear the filters or create a new pitch.</p>'}</section>`+
 pitchDataLists();
 pitchLengthLinks(q);
}
function pitchDataLists(){return `<datalist id="pitch-audiences">${(pitchChoices?.audiences||[]).map(a=>`<option value="${E(a)}">`).join('')}</datalist><datalist id="pitch-scenarios">${(pitchChoices?.scenarios||[]).map(a=>`<option value="${E(a)}">`).join('')}</datalist>`;}
async function pitchEditor(id){
 pitchStop();pitchElapsed=0;[pitchChoices,pitchCurrent]=await Promise.all([api('/api/pitches'),api('/api/pitch/'+encodeURIComponent(id))]);pitchDirty=false;
 const p=pitchCurrent;
 app.innerHTML=heading(p.title,p.audience+' · '+p.scenario,'<a class="button" href="/pitches">Pitch library</a>')+
 `<form id="pitch-editor-form"><div class="pitch-savebar"><div><strong id="pitch-save-state" role="status" aria-live="polite">Saved · ${E(readableDate(p.created_at))}</strong><span class="small">Edits stay private. Saving keeps the previous version.</span></div><div class="actions"><button class="primary" type="submit">Save pitch</button><button type="button" data-pitch-action="duplicate">Make a variant</button><button type="button" data-pitch-action="rehearse">Practice aloud</button></div></div>
 <div id="pitch-edit-layout" class="pitch-edit-layout"><section class="section pitch-writing"><h2>Your script</h2><div class="pitch-fields"><label>Title<input name="title" required maxlength="160" value="${E(p.title)}"></label><label>Length<select name="duration_seconds" id="pitch-duration">${pitchChoices.lengths.map(s=>`<option value="${s}" ${s===p.duration_seconds?'selected':''}>${E(pitchLength(s))}</option>`).join('')}<option value="custom">Custom length</option></select></label><label id="pitch-custom-length" hidden>Custom length (seconds)<input name="custom_seconds" type="number" min="10" max="7200" value="${p.duration_seconds}"></label><label>Audience<input name="audience" list="pitch-audiences" required maxlength="100" value="${E(p.audience)}"></label><label>Scenario<input name="scenario" list="pitch-scenarios" required maxlength="100" value="${E(p.scenario)}"></label><label>Speaker<input name="speaker" maxlength="100" value="${E(p.speaker)}" placeholder="Bao, Daniel, or a team handoff"></label><label>Format<select name="format">${pitchOptions(['script','outline'],p.format)}</select></label><label>Stage<select name="status">${['draft','rehearsal_ready','archived'].map(v=>`<option value="${v}" ${v===p.status?'selected':''}>${E(pitchState(v))}</option>`).join('')}</select></label></div>
 <label class="pitch-label" for="pitch-body">Pitch text</label><textarea id="pitch-body" name="body" required maxlength="40000" class="pitch-text" rows="18">${E(p.body)}</textarea><p id="pitch-count" class="small" aria-live="polite"></p>
 <label class="pitch-label">Speaker notes<textarea name="notes" maxlength="10000" rows="5" placeholder="Delivery cues, demonstrations, or claims to check">${E(p.notes)}</textarea></label><label class="pitch-label">What changed? (optional)<input name="change_note" maxlength="300" placeholder="e.g. Clearer investor ask"></label>
 <div class="actions"><button class="primary" type="submit">Save pitch</button><button type="button" data-pitch-action="copy">Copy current text</button><a class="button" href="/api/pitch/${E(id)}/export">Download saved TXT</a></div></section>
 <div class="pitch-context"><section class="section"><h2>Before you pitch</h2><p>Adapt the opening and the ask for this audience. Read it aloud to check timing.</p><p class="small">Historical wording and numbers need checking against Company memory. Editing a pitch does not change company facts.</p><div class="actions"><a href="/memory">Company memory</a><a href="/materials">Pitch materials</a></div><p id="pitch-open-prompts" class="small"></p></section>
 <section class="section"><h2>Source material</h2>${p.source_details.map(s=>`<div class="source"><strong>${E(s.original_path.split(/[\\/]/).at(-1))}</strong><p class="source-path">${E(s.original_path)}</p><p>${E(readableDate(s.captured_at))} · historical reference</p>${s.material_id?`<a href="/material/${E(s.material_id)}">Read source</a>`:''}</div>`).join('')||'<p class="small">No source attached. This is your own working draft.</p>'}
 ${p.claim_details.length?`<details><summary>Linked company claims</summary>${p.claim_details.map(c=>`<p><strong>${E(c.label)}</strong><br>${E(c.body)}<br><span class="small">${c.id===c.canonical_version_id?'Canonical version':'Historical version'} · ${E(c.status||'Unreviewed')}</span></p>`).join('')}</details>`:''}</section>
 <section class="section"><h2>Version history</h2><p class="small">${p.history.length} saved version${p.history.length===1?'':'s'}. Restore creates a new version.</p>${p.history.map((v,i)=>`<div class="record"><strong>${E(readableDate(v.created_at))}</strong><p class="small">${E(v.change_note||'Saved edits')} · ${E(v.format)}</p><div class="actions"><a href="/api/pitch/${E(id)}/export?version=${E(v.id)}">Read TXT</a>${i?`<button type="button" data-pitch-action="restore" data-version="${E(v.id)}">Restore as new version</button>`:tag('Current')}</div></div>`).join('')}</section></div></div>
 <section id="pitch-rehearsal" class="section pitch-rehearsal" hidden><div class="section-title"><h2>Rehearsal</h2><button type="button" data-pitch-action="edit">Back to editing</button></div><p class="small">Your current text, including unsaved edits. The timer measures this practice only.</p><div class="pitch-timerbar"><strong id="pitch-timer" role="timer">00:00</strong><span id="pitch-timer-target" class="small"></span><button type="button" data-pitch-action="timer">Start timer</button><button type="button" data-pitch-action="reset-timer">Reset</button></div><div id="pitch-practice-text" class="pitch-practice-text"></div></section></form>`+pitchDataLists();
 pitchEditorLayout(p);pitchCounts();pitchOfferRecovery();document.title=p.title+' | A Story';
}
function pitchValues(form){
 const f=new FormData(form),p=Object.fromEntries(f);p.duration_seconds=f.has('duration_minutes')?Math.round(Number(f.get('duration_minutes'))*60):f.get('duration_seconds')==='custom'?Number(f.get('custom_seconds')):Number(f.get('duration_seconds'));
 p.sources=pitchCurrent?.sources|| (pitchSource?.source_version_id?[pitchSource.source_version_id]:[]);p.claim_versions=pitchCurrent?.claim_versions||[];p.expected_version_id=pitchCurrent?.id;
 return p;
}
function pitchCounts(){
 const form=document.querySelector('#pitch-editor-form');if(!form)return;const p=pitchValues(form),words=(p.body.match(/[\p{L}\p{N}_]+(?:['’-][\p{L}\p{N}_]+)*/gu)||[]).length,seconds=Math.round(words/130*60);
 document.querySelector('#pitch-count').textContent=words+' words · about '+pitchLength(seconds)+' at 130 words/minute · target '+pitchLength(p.duration_seconds)+(seconds>p.duration_seconds?' - shorten or allow more time.':p.format==='outline'?' - includes outline cues; allow time for demos and pauses.':' - rehearse to confirm.');
 const prompts=[...new Set(p.body.match(/\[[^\]\n]{1,250}\]/g)||[])];document.querySelector('#pitch-open-prompts').textContent=prompts.length?'Open prompts: '+prompts.join(' · '):'Read it aloud. Does it sound like something you would actually say?';
 document.querySelector('#pitch-custom-length').hidden=form.elements.duration_seconds.value!=='custom';
}
function pitchDrawTimer(){const seconds=pitchElapsed+(pitchClock?Math.floor((Date.now()-pitchStarted)/1000):0),target=pitchValues(document.querySelector('#pitch-editor-form')).duration_seconds;document.querySelector('#pitch-timer').textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');document.querySelector('#pitch-timer-target').textContent='Target '+pitchLength(target)+(seconds>target?' - over target':'');}
document.addEventListener('input',e=>{if(e.target.closest('#pitch-editor-form,#pitch-new-form')){pitchDirty=true;pitchRemember();const state=document.querySelector('#pitch-save-state');if(state)state.textContent='Unsaved edits';pitchCounts();}});
document.addEventListener('change',e=>{if(e.target.closest('#pitch-editor-form')){pitchDirty=true;pitchRemember();document.querySelector('#pitch-save-state').textContent='Unsaved edits';pitchCounts();}});
document.addEventListener('submit',async e=>{
 if(!['pitch-editor-form','pitch-new-form','pitch-filters'].includes(e.target.id))return;e.preventDefault();e.stopImmediatePropagation();
 const buttons=[...e.target.querySelectorAll('button[type="submit"]')];buttons.forEach(b=>b.disabled=true);
 try{
  if(e.target.id==='pitch-filters'){const q=new URLSearchParams(new FormData(e.target));location.href='/pitches?'+q;return;}
  const p=pitchValues(e.target);const r=await api(e.target.id==='pitch-new-form'?'/api/pitches':'/api/pitch/'+encodeURIComponent(pitchCurrent.pitch_id),p);pitchClearRecovery();pitchDirty=false;
  if(e.target.id==='pitch-new-form')location.href='/pitch/'+r.pitch_id;else{await pitchEditor(r.pitch_id);toast('Saved as a new version. Your earlier wording is preserved.');}
 }catch(err){toast(err.message,true);}finally{buttons.forEach(b=>b.disabled=false);}
});
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-pitch-action]');if(!b)return;e.preventDefault();e.stopImmediatePropagation();const action=b.dataset.pitchAction;
 try{
  if(action==='recover'){pitchRecover();}
  else if(action==='discard-recovery'){pitchClearRecovery();document.querySelector('#pitch-recovery').remove();}
  else if(action==='new'){document.querySelector('#pitch-new').hidden=false;document.querySelector('#pitch-new-form input').focus();}
  else if(action==='cancel-new'){if(!pitchDirty||confirm('Discard the unsaved new pitch?')){pitchDirty=false;document.querySelector('#pitch-new').hidden=true;}}
  else if(action==='copy'){try{await navigator.clipboard.writeText(document.querySelector('#pitch-body').value);toast('Current pitch text copied.');}catch{const field=document.querySelector('#pitch-body');field.focus();field.select();toast('Text selected. Press Ctrl + C to copy.');}}
  else if(action==='duplicate'){b.disabled=true;const p=pitchValues(document.querySelector('#pitch-editor-form'));p.title=(p.title+' - variant').slice(0,160);p.status='draft';p.change_note='Adapted from '+pitchCurrent.id;const r=await api('/api/pitches',p);pitchDirty=false;location.href='/pitch/'+r.pitch_id;}
  else if(action==='restore'){if(pitchDirty&&!confirm('Restore this saved version? Unsaved edits will be replaced.'))return;b.disabled=true;const r=await api('/api/pitch/'+pitchCurrent.pitch_id+'/restore',{version_id:b.dataset.version,expected_version_id:pitchCurrent.id});pitchDirty=false;await pitchEditor(r.pitch_id);toast('Restored as a new version. All previous versions are retained.');}
  else if(action==='rehearse'){document.querySelector('#pitch-edit-layout').hidden=true;document.querySelector('#pitch-rehearsal').hidden=false;document.querySelector('#pitch-practice-text').textContent=document.querySelector('#pitch-body').value;pitchDrawTimer();document.querySelector('#pitch-rehearsal').scrollIntoView({block:'start'});}
  else if(action==='edit'){pitchStop();pitchElapsed=0;document.querySelector('#pitch-edit-layout').hidden=false;document.querySelector('#pitch-rehearsal').hidden=true;document.querySelector('[data-pitch-action="timer"]').textContent='Start timer';}
  else if(action==='timer'){if(pitchClock){pitchElapsed+=Math.floor((Date.now()-pitchStarted)/1000);pitchStop();b.textContent='Resume timer';}else{pitchStarted=Date.now();pitchClock=setInterval(pitchDrawTimer,500);b.textContent='Pause timer';}pitchDrawTimer();}
  else if(action==='reset-timer'){pitchStop();pitchElapsed=0;document.querySelector('[data-pitch-action="timer"]').textContent='Start timer';pitchDrawTimer();}
 }catch(err){toast(err.message,true);}finally{b.disabled=false;}
});

// Keep writing ahead of metadata, and recover unsaved wording after a refresh.
function pitchEditorLayout(p){
 const f=document.querySelector('#pitch-editor-form'),writing=f.querySelector('.pitch-writing'),fields=writing.querySelector('.pitch-fields');
 writing.querySelector('h2').remove();
 const title=f.elements.title;title.className='pitch-form-title';title.id='pitch-title';title.setAttribute('aria-label','Title');title.closest('label').className='sr-only';title.closest('label').htmlFor='pitch-title';title.closest('label').before(title);writing.prepend(title);
 const core=document.createElement('div');core.className='pitch-core-fields';title.after(core);
 for(const name of ['duration_seconds','custom_seconds','audience'])core.append(f.elements[name].closest('label'));
 const meta=document.createElement('details');meta.className='pitch-disclosure';meta.innerHTML='<summary>Delivery notes & settings</summary>';writing.append(meta);meta.append(fields);
 meta.append(f.elements.notes.closest('label'));meta.append(f.elements.change_note.closest('label'));
 const text=f.elements.body;text.rows=13;writing.querySelector('label[for="pitch-body"]').textContent=p.format==='outline'?'Session text & demo plan':'Spoken draft';
 const brief=f.querySelector('.pitch-context .section');brief.innerHTML='<h2>For this audience</h2><p class="pitch-brief-copy">'+E(p.notes||'Use Delivery notes to record the decision this audience should make and the proof they need.')+'</p><p class="small">Working draft based on your direction and sources. Verify current product claims before presenting.</p><p id="pitch-open-prompts" class="small"></p>';
 const context=f.querySelector('.pitch-context');
 for(const section of [...context.querySelectorAll('.section')].slice(1)){const h=section.querySelector('h2'),details=document.createElement('details');details.className='pitch-disclosure';details.innerHTML='<summary>'+E(h.textContent)+'</summary>';h.remove();while(section.firstChild)details.append(section.firstChild);section.append(details);}
 const back=app.querySelector('.page-heading a');try{back.href=sessionStorage.getItem('astory-pitch-library')||'/pitches';}catch{}back.textContent='Back to pitches';
}
function pitchLengthLinks(q){
 const filter=document.querySelector('#pitch-filters'),nav=document.createElement('nav');nav.className='pitch-lengths';nav.setAttribute('aria-label','Pitch length');
 const link=s=>{const p=new URLSearchParams(q);s?p.set('duration',s):p.delete('duration');p.delete('material');return '/pitches'+(p.size?'?'+p:'');};
 nav.innerHTML=['',30,60,180,300,420,600,900,1200].map(s=>'<a href="'+E(link(String(s)))+'" '+((q.get('duration')||'')===String(s)?'aria-current="true"':'')+'>'+E(s?pitchLength(s):'All lengths')+'</a>').join('');filter.after(nav);
}
function pitchRemember(){if(!pitchCurrent)return;const f=document.querySelector('#pitch-editor-form');if(!f)return;try{sessionStorage.setItem('astory-pitch-recovery:'+pitchCurrent.pitch_id,JSON.stringify({version:pitchCurrent.id,fields:pitchValues(f)}));}catch{}}
function pitchClearRecovery(){if(pitchCurrent)try{sessionStorage.removeItem('astory-pitch-recovery:'+pitchCurrent.pitch_id);}catch{}}
function pitchOfferRecovery(){
 let draft;try{draft=JSON.parse(sessionStorage.getItem('astory-pitch-recovery:'+pitchCurrent.pitch_id)||'null');}catch{return;}if(!draft)return;
 const section=document.createElement('section');section.id='pitch-recovery';section.className='pitch-recovery';section.innerHTML='<strong>Unsaved wording is available in this tab.</strong><p class="small">'+(draft.version===pitchCurrent.id?'Restore it to the editor or keep the saved version.':'This pitch has a newer saved version. Restore your wording to compare before saving.')+'</p><div class="actions"><button data-pitch-action="recover">Restore unsaved wording</button><button data-pitch-action="discard-recovery">Keep saved version</button></div>';document.querySelector('#pitch-editor-form').before(section);
}
function pitchRecover(){
 let draft;try{draft=JSON.parse(sessionStorage.getItem('astory-pitch-recovery:'+pitchCurrent.pitch_id)||'null');}catch{return;}if(!draft)return;const f=document.querySelector('#pitch-editor-form');
 for(const [key,value]of Object.entries(draft.fields))if(f.elements[key]&&typeof value==='string')f.elements[key].value=value;
 const duration=String(draft.fields.duration_seconds);
 if([...f.elements.duration_seconds.options].some(o=>o.value===duration))f.elements.duration_seconds.value=duration;else{f.elements.duration_seconds.value='custom';f.elements.custom_seconds.value=duration;}
 pitchDirty=true;document.querySelector('#pitch-save-state').textContent='Recovered unsaved wording';document.querySelector('#pitch-recovery').remove();pitchCounts();pitchRemember();
}
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'&&document.querySelector('#pitch-editor-form')){e.preventDefault();const f=document.querySelector('#pitch-editor-form');if(!f.querySelector('button[type="submit"]').disabled)f.requestSubmit();}});
document.addEventListener('click',e=>{if(pitchDirty&&e.target.closest('a'))pitchRemember();});
document.addEventListener('change',e=>{if(e.target.closest('#pitch-filters')&&e.target.tagName==='SELECT')e.target.form.requestSubmit();});
