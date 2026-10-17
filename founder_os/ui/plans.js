// Plans: ask the Planner a question, get a report in Bao's identity as a PDF. The weekly plan writes itself on Monday.
function planReport(r){
 const p=r.report;if(!p)return '';
 return `<section class="section plan-report"><div class="section-title"><div><h2>${E(r.title||'Plan')}</h2><p class="small">${E(r.question)} · ${E(readableDate(r.finished_at))}</p></div><div class="actions">${r.pdf_url?`<a class="button primary" href="${E(r.pdf_url)}">Open the PDF</a>`:''}${r.html_url?`<a class="button" href="${E(r.html_url)}" target="_blank" rel="noopener">Web version</a>`:''}</div></div>`+
 p.answer.map(x=>`<p>${E(x)}</p>`).join('')+
 (p.numbers.length?`<div class="summary desk-tiles">${p.numbers.map(n=>`<div><strong>${E(n.value)}</strong><span>${E(n.label)}</span>${n.source?`<small>${E(n.source)}</small>`:''}</div>`).join('')}</div>`:'')+
 (p.plan.length?`<h3 class="list-head">The plan</h3><div class="table-scroll"><table class="pipeline plan-table"><thead><tr><th>When</th><th>What and why</th><th>Who</th></tr></thead><tbody>${p.plan.map(x=>`<tr><td class="plan-when">${E(x.when)}</td><td>${E(x.what)}${x.why?`<br><small>${E(x.why)}</small>`:''}${x.link?`<br><a class="small" href="${E(x.link)}">${E(x.link.replace(/^https?:\/\/[^/]+/,''))}</a>`:''}</td><td>${E(x.owner)}</td></tr>`).join('')}</tbody></table></div>`:'')+
 (p.questions_for_bao.length?`<div class="notice plan-questions"><strong>Questions only you can answer</strong><ol>${p.questions_for_bao.map(q=>`<li>${E(q)}</li>`).join('')}</ol></div>`:'')+
 (p.risks.length?`<details class="more"><summary>Risks (${p.risks.length})</summary><ul>${p.risks.map(x=>`<li>${E(x)}</li>`).join('')}</ul></details>`:'')+`</section>`;
}
async function plans(){
 const r=await api('/api/plans'),items=r.items,latest=r.latest;
 app.innerHTML=heading('Plans','Ask the Planner a question and get a report in your own colors, as a PDF. It reads every desk, lays out the next moves, and lists what only you can answer.')+
 `<form class="section plan-form"><label>What do you want to know?<textarea name="question" maxlength="600" placeholder="${E(r.default_question)}"></textarea></label><div class="actions"><button class="primary" type="submit"${r.writing?' disabled':''}>${r.writing?'Writing…':'Write the report'}</button><span class="small">About 5 minutes on your ChatGPT plan. The weekly plan writes itself on Monday mornings and is linked in the daily brief.</span></div></form>`+
 (latest?planReport(latest):'<div class="all-clear"><h2>No report yet</h2><p class="small">Ask the question above, or wait for Monday’s plan.</p></div>')+
 (items.length?`<section class="section"><h2>Past reports</h2><ul class="tracker">${items.map(x=>`<li><span><strong>${E(x.title||x.question)}</strong><small class="tracker-sub">${E(readableDate(x.created_at))} · ${E(x.state==='READY'?'Ready':x.state==='QUEUED'?'Writing':'Failed'+(x.error?': '+x.error.slice(0,80):''))}${x.auto?' · weekly':''}</small></span>${x.pdf_url?`<a class="button" href="${E(x.pdf_url)}">PDF</a>`:x.state==='READY'&&x.html_url?`<a class="button" href="${E(x.html_url)}" target="_blank" rel="noopener">Open</a>`:''}</li>`).join('')}</ul></section>`:'');
}
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.classList.contains('plan-form'))return;e.preventDefault();
 const btn=f.querySelector('button[type=submit]');btn.disabled=true;
 try{await api('/api/plan',{question:new FormData(f).get('question')||''});await boot();toast('The Planner is writing. Reload in about 5 minutes; the PDF appears here.');}catch(err){toast(err.message,true);btn.disabled=false;}
});
