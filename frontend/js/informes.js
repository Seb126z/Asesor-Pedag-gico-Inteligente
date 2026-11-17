/* Pestañas Informe y Mapa mental (módulo de Sebastián) */
function vInf(){
 var done=LABS.filter(function(l){return l.res&&l.ok});
 if(!done.length)return'<div class="card">El informe consolida los laboratorios evaluados y <b>aprobados por el docente</b>. Evalúa y aprueba al menos uno en la pestaña Evaluación.</div>';
 var avg=done.reduce(function(a,l){return a+final(l)},0)/done.length,gaps=[];
 done.forEach(function(l){l.res.crit.forEach(function(c){if(c.score<3.5)gaps.push(l.name.split(' · ')[0]+' — '+c.criterio+(c.brecha?' ('+c.brecha.toLowerCase()+')':''))})});
 var h='<div class="card row" style="justify-content:space-between"><div><div class="mu">Promedio ponderado simple</div><div class="big" style="color:'+col(avg)+'">'+avg.toFixed(2)+'</div></div><div class="mu">'+done.length+' de '+LABS.length+' laboratorios aprobados</div></div>'+
 '<div class="card"><h3>Evolución por laboratorio</h3>'+LABS.map(function(l){var g=l.res&&l.ok?final(l):null;return'<div class="row" style="flex-wrap:nowrap;margin-bottom:6px"><span style="width:190px;flex:none"><small>'+esc(l.name)+'</small></span><div class="bar" style="flex:1"><i style="width:'+(g==null?0:g/5*100)+'%;background:'+col(g)+'"></i></div><b style="width:90px;text-align:right">'+(g==null?'<small class="mu">pendiente</small>':g.toFixed(1)+' · '+lvl(g))+'</b></div>'}).join('')+'</div>'+
 '<div class="card"><h3>Brechas y plan de fortalecimiento</h3>'+(gaps.length?'<ol style="margin:0;padding-left:20px">'+gaps.map(function(g){return'<li>'+esc(g)+'</li>'}).join('')+'</ol>':'<p class="ok" style="margin:0">No se detectaron brechas por debajo de 3,5.</p>')+'</div>';
 return h}
function mastery(t){var v=[];LABS.forEach(function(l){if(l.topics.indexOf(t)>-1&&l.res&&l.ok)v.push(final(l))});return v.length?v.reduce(function(a,b){return a+b},0)/v.length:null}
function vMap(){
 var cx=350,cy=235,n='<line x1="0" y1="0" x2="0" y2="0"/>',e='',N='';
 var step=2*Math.PI/CATS.length;
 CATS.forEach(function(c,i){
  var a=i*step-Math.PI/2,x=cx+Math.cos(a)*115,y=cy+Math.sin(a)*115;
  e+='<line x1="'+cx+'" y1="'+cy+'" x2="'+x+'" y2="'+y+'" stroke="var(--bd)" stroke-width="2"/>';
  N+='<g class="nd" onclick="sel=\'c'+i+'\';render()"><rect x="'+(x-48)+'" y="'+(y-15)+'" width="96" height="30" rx="15" fill="var(--sf)" stroke="var(--ac)" stroke-width="1.5"/><text x="'+x+'" y="'+(y+4)+'" text-anchor="middle" font-weight="600">'+c[0]+'</text></g>';
  c[1].forEach(function(t,j){
   var off=(j-(c[1].length-1)/2)*0.5,b=a+off,tx=cx+Math.cos(b)*215,ty=cy+Math.sin(b)*195,m=mastery(t);
   e+='<line x1="'+x+'" y1="'+y+'" x2="'+tx+'" y2="'+ty+'" stroke="var(--bd)"/>';
   N+='<g class="nd" onclick="sel=\''+t+'\';render()"><circle cx="'+tx+'" cy="'+ty+'" r="'+(sel==t?30:26)+'" fill="'+col(m)+'" fill-opacity=".25" stroke="'+col(m)+'" stroke-width="2.5"/><text x="'+tx+'" y="'+(ty+4)+'" text-anchor="middle" style="font-size:10px">'+TOPICS[t].split(' ')[0]+'</text></g>'})});
 N+='<g><circle cx="'+cx+'" cy="'+cy+'" r="34" fill="var(--ac)"/><text x="'+cx+'" y="'+(cy+5)+'" text-anchor="middle" style="fill:var(--bg);font-weight:700;font-size:15px">IA</text></g>';
 var d='<p class="mu" style="margin:0">Selecciona una temática para ver sus detalles.</p>';
 if(sel&&TOPICS[sel]){var m=mastery(sel),ls=LABS.filter(function(l){return l.topics.indexOf(sel)>-1});
  d='<h3>'+TOPICS[sel]+'</h3><p>Dominio: <b style="color:'+col(m)+'">'+(m==null?'sin evaluar':m.toFixed(1)+' · '+lvl(m))+'</b></p><p class="mu">Aplicado en: '+ls.map(function(l){return esc(l.name)}).join('; ')+'</p>'+
  ls.map(function(l){if(!(l.res&&l.ok))return'<p><small>'+esc(l.name.split(' · ')[0])+': pendiente de aprobación.</small></p>';return'<p><small><b>'+esc(l.name.split(' · ')[0])+'</b> — '+l.res.crit.map(function(c){return c.score>=3.5?'<span class="ok">✓ '+esc(c.criterio)+'</span>':'<span class="wa">▲ profundizar: '+esc(c.criterio)+'</span>'}).join(' · ')+'</small></p>'}).join('')}
 else if(sel&&sel[0]=='c'){var c=CATS[+sel.slice(1)];d='<h3>'+c[0]+'</h3><p class="mu">Incluye: '+c[1].map(function(t){return TOPICS[t]}).join(', ')+'</p>'}
 return'<div class="card"><div class="row" style="margin-bottom:6px"><span class="tag">● verde ≥ 4,0</span><span class="tag">● ámbar 3,0–3,9</span><span class="tag">● rojo &lt; 3,0</span><span class="tag">● gris sin evaluar</span></div><div class="tw"><svg viewBox="0 0 700 470" style="width:100%;min-width:560px">'+e+N+'</svg></div></div><div class="card">'+d+'</div>'}

