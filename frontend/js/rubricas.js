/* Pestaña Rúbricas */
function vRub(){
 var l=LABS[cur],s=sumW(l),ok=s==100;
 return'<div class="card row">'+labSel()+'<span class="tag">Rúbrica v'+l.v+'</span></div><div class="card"><div class="tw"><table><tr><th>Criterio</th><th>Peso %</th><th>Indicadores (separados por coma)</th><th></th></tr>'+
 l.rub.map(function(c,i){return'<tr><td><input value="'+esc(c.n)+'" onchange="LABS[cur].rub['+i+'].n=this.value;LABS[cur].dirty=true"></td><td><input class="n" type="number" min="0" max="100" value="'+c.w+'" onchange="LABS[cur].rub['+i+'].w=+this.value;bump();render()"></td><td><input value="'+esc(c.kw.join(', '))+'" onchange="LABS[cur].rub['+i+'].kw=this.value.split(\',\').map(function(x){return x.trim().toLowerCase()}).filter(Boolean);LABS[cur].dirty=true"></td><td><button class="b s" onclick="LABS[cur].rub.splice('+i+',1);bump();render()">✕</button></td></tr>'}).join('')+'</table></div>'+
 '<div class="row" style="margin-top:10px"><button class="b s" onclick="LABS[cur].rub.push({n:\'Nuevo criterio\',w:0,kw:[\'clave\']});LABS[cur].dirty=true;render()">+ Criterio</button><b class="'+(ok?'ok':'er')+'">Suma de ponderaciones: '+s+'%</b><button class="b" '+(ok?'':'disabled')+' onclick="saveRubric()">Guardar rúbrica</button>'+(l.dirty?'<span class="wa">Cambios sin guardar</span>':'')+'</div>'+
 (ok?'':'<p class="er" style="margin-bottom:0">Inconsistencia: las ponderaciones deben sumar 100 %. La evaluación está bloqueada hasta corregirla.</p>')+'</div>'}
function bump(){var l=LABS[cur];l.v=(parseFloat(l.v)+0.1).toFixed(1);l.res=null;l.ok=false;l.adj=null;l.dirty=true}

