// Plans: ask the Planner a question, get a one-page brief in Bao's identity as a PDF. The weekly plan writes itself on Monday.
function planReport(r){
 const p=r.report;if(!p)return '';
 const head=`<div class="section-title"><div><h2>${E(r.title||'Plan')}</h2><p class="small">You asked: ${E(r.question)} · ${E(readableDate(r.finished_at))}</p></div><div class="actions">${r.pdf_url?`<a class="button primary" href="${E(r.pdf_url)}">Open the PDF</a>`:''}${r.html_url?`<a class="button" href="${E(r.html_url)}" target="_blank" rel="noopener">Web version</a>`:''}</div></div>`;
 if(!p.bottom_line&&p.answer)return `<section class="section plan-report">${head}${p.answer.slice(0,2).map(x=>`<p>${E(x)}</p>`).join('')}<p class="small">An older long-form report. New reports are one-page briefs.</p></section>`;
 return `<section class="section plan-report">${head}`+
 (p.bottom_line?`<div class="plan-bottom"><p>${E(p.bottom_line)}</p></div>`:'')+
 (p.moves.length?`<h3 class="list-head">This week</h3><ol class="plan-moves">${p.moves.map(m=>`<li><strong>${E(m.what)}</strong><span class="small"> ${E(m.owner)}${m.by?' · '+E(m.by):''}${m.why?' · '+E(m.why):''}</span></li>`).join('')}</ol>`:'')+
 (p.decisions.length?`<h3 class="list-head">Decide</h3><div class="table-scroll"><table class="pipeline plan-table"><thead><tr><th>Decision</th><th>Recommended</th><th>Unblocks</th></tr></thead><tbody>${p.decisions.map(d=>`<tr><td>${E(d.decision)}</td><td class="plan-when">${E(d.recommend)}</td><td><small>${E(d.unblocks)}</small></td></tr>`).join('')}</tbody></table></div>`:'')+
 (p.numbers.length?`<div class="summary desk-tiles">${p.numbers.map(n=>`<div><strong>${E(n.value)}</strong><span>${E(n.label)}</span>${n.source?`<small>${E(n.source)}</small>`:''}</div>`).join('')}</div>`:'')+
 (p.by_agent&&p.by_agent.length?`<details class="more"><summary>By agent (${p.by_agent.length})</summary><div class="table-scroll"><table class="pipeline plan-table"><thead><tr><th>Agent</th><th>Result</th><th>Needs you</th></tr></thead><tbody>${p.by_agent.map(a=>`<tr><td><strong>${E(a.agent)}</strong></td><td>${E(a.result)}</td><td><small>${E(a.needs)}</small></td></tr>`).join('')}</tbody></table></div></details>`:'')+
 (p.risks.length||p.later.length?`<details class="more"><summary>Risks and later</summary>${p.risks.length?`<ul>${p.risks.map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:''}${p.later.length?`<ul>${p.later.map(x=>`<li>${E(x.what)} <small>${E(x.owner)}${x.by?' · '+E(x.by):''}</small></li>`).join('')}</ul>`:''}</details>`:'')+`</section>`;
}
async function plans(){
 const r=await api('/api/plans'),items=r.items,latest=r.latest;
 app.innerHTML=heading('Plans','Ask a question, get a one-page brief as a PDF: the answer, three moves, the decisions only you can make.')+
 `<form class="section plan-form"><label>What do you want to know?<textarea name="question" maxlength="600" placeholder="${E(r.default_question)}"></textarea></label><div class="actions"><button class="primary" type="submit"${r.writing?' disabled':''}>${r.writing?'Writing…':'Write the brief'}</button><span class="small">About 2 minutes. The weekly brief writes itself on Monday mornings and is linked in the daily email.</span></div></form>`+
 (latest?planReport(latest):'<div class="all-clear"><h2>No brief yet</h2><p class="small">Ask the question above, or wait for Monday.</p></div>')+
 (items.length?`<section class="section"><h2>Past briefs</h2><ul class="tracker">${items.map(x=>`<li><span><strong>${E(x.title||x.question)}</strong><small class="tracker-sub">${E(readableDate(x.created_at))} · ${E(x.state==='READY'?'Ready':x.state==='QUEUED'?'Writing':'Failed'+(x.error?': '+x.error.slice(0,80):''))}${x.auto?' · weekly':''}</small></span>${x.pdf_url?`<a class="button" href="${E(x.pdf_url)}">PDF</a>`:x.state==='READY'&&x.html_url?`<a class="button" href="${E(x.html_url)}" target="_blank" rel="noopener">Open</a>`:''}</li>`).join('')}</ul></section>`:'');
}
document.addEventListener('submit',async e=>{
 const f=e.target;if(!f.classList.contains('plan-form'))return;e.preventDefault();
 const btn=f.querySelector('button[type=submit]');btn.disabled=true;
 try{await api('/api/plan',{question:new FormData(f).get('question')||''});await boot();toast('The Planner is writing. Reload in about 2 minutes; the PDF appears here.');}catch(err){toast(err.message,true);btn.disabled=false;}
});
