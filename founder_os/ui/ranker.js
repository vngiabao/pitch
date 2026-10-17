// "Apply to these first": the programs worth the most per founder hour, with every component of the estimate shown.
(function(){
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const usd=v=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(v);
 function parts(r){
  const m=r.money,l=r.likelihood,h=r.hours,u=r.urgency;
  return `<ul class="apply-first-parts small"><li>Money: ${esc(usd(m.counted))} counted (${esc(m.basis)})</li><li>Likelihood: ${esc(Math.round(l.value*100))}% (fit ${esc(l.fit_known?l.fit:'about '+l.fit)}, ${esc(l.eligibility.toLowerCase())}${l.eligibility_factor<1?', halved':''})</li><li>Hours: ${esc(h.value)} (${esc(h.source)})</li><li>Urgency: x${esc(u.factor)}${u.days!==null&&u.days!==undefined?' ('+esc(u.days)+' days left)':''}</li><li>Expected value: ${esc(usd(r.expected_value))}</li></ul>`;
 }
 function row(r,i,compact){
  const p=r.preparation||{};
  return `<li class="apply-first-row"><span class="apply-first-rank">${i+1}</span><div class="apply-first-main"><a class="program-name" href="/opportunity/${esc(r.opportunity_id)}">${esc(r.name)}</a>`+
   `<p class="small">${esc(r.reason)}${p.summary?' '+esc(p.summary):''}</p>${compact?'':parts(r)}`+
   `${!compact&&p.application_id&&p.questions?`<p class="small"><a href="/application/${esc(p.application_id)}">Prepared answers</a>${p.edition?` · <a href="/pitch-lab/${esc(p.edition.id)}">Pitch edition</a>`:''}</p>`:!compact&&p.edition?`<p class="small"><a href="/pitch-lab/${esc(p.edition.id)}">Pitch edition</a></p>`:''}</div>`+
   `<div class="apply-first-figure"><strong>${esc(usd(r.per_hour))}</strong><small>per hour, estimate</small></div></li>`;
 }
 window.applyFirst=function(data,opts){
  opts=opts||{};const rows=Array.isArray(data)?data:(data&&data.rows)||[];const unpriced=(data&&data.unpriced)||[];
  if(!rows.length)return '';
  const method='<details class="apply-first-method small"><summary>How this number is made</summary><p>Cash prize maximum, or credit face value counted at 25 percent, times a win likelihood from the fit score (fit above 40 scaled to a 60 percent ceiling, halved while eligibility is unknown), divided by the estimated founder hours (3 when the hunter has no estimate), times an urgency factor for programs closing within 14 days (up to 2x on the closing day). It is an estimate that orders the work. It does not forecast an award.'+(unpriced.length?' Not ranked because no amount is published: '+esc(unpriced.map(x=>x.name).join(', '))+'.':'')+'</p></details>';
  return `<section class="section apply-first" id="apply-first" aria-labelledby="apply-first-title"><div class="section-title"><h2 id="apply-first-title">Apply to these first</h2><span class="small">Expected money per founder hour. An estimate, not a forecast.${opts.compact?' <a href="/money#apply-first">Every component</a>':''}</span></div><ol class="apply-first-list">${rows.map((r,i)=>row(r,i,opts.compact)).join('')}</ol>${opts.compact?'':method}</section>`;
 };
})();
