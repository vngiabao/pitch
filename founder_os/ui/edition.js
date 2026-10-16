// Edition deck preview: fit slides to their frame, link each QA note to its flag, and animate with GSAP (motion only when the viewer allows it).
(function(){
  function fit(){document.querySelectorAll('.pv-slide').forEach(function(box){box.style.setProperty('--s',String(box.clientWidth/1920));});}
  fit();window.addEventListener('resize',fit);
  var g=window.gsap;
  document.querySelectorAll('.pv-issues li').forEach(function(li){
    var flag=document.querySelector('[data-flag="'+li.dataset.for+'"]');if(!flag)return;
    li.addEventListener('mouseenter',function(){flag.classList.add('on');if(g)g.fromTo(flag,{scale:1.08},{scale:1,duration:.45,ease:'back.out(3)',overwrite:true});});
    li.addEventListener('mouseleave',function(){flag.classList.remove('on');});
  });
  if(!g)return;
  if(window.ScrollTrigger)g.registerPlugin(window.ScrollTrigger);
  g.matchMedia().add('(prefers-reduced-motion: no-preference)',function(){
    g.from('.pv-head > *',{y:14,autoAlpha:0,duration:.6,stagger:.07,ease:'power3.out'});
    // Cards are never pre-hidden: if animation can't run, the slides still show.
    if(window.ScrollTrigger)window.ScrollTrigger.batch('.pv-card',{start:'top 96%',once:true,onEnter:function(cards){g.from(cards,{y:36,autoAlpha:0,duration:.7,stagger:.08,ease:'power3.out'});}});
    g.to('.pv-flag.block',{opacity:.5,duration:.9,repeat:-1,yoyo:true,ease:'sine.inOut'});
  });
})();
